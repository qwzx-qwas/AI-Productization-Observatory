"""GitHub collectors for replayable fixture runs and live REST-backed windows."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from socket import timeout as SocketTimeout
from time import sleep
from typing import Any, Callable

from src.candidate_prescreen.config import query_slice_config, require_live_discovery_allowed, source_config
from src.common.config import require_environment_variable
from src.common.errors import ProcessingError
from src.common.files import load_json, utc_now_iso

_REQUIRED_REQUEST_PARAM_FIELDS = (
    "window_start",
    "window_end",
    "fetch_mode",
    "page_or_cursor_start",
    "page_or_cursor_end",
    "selection_rule_version",
    "query_slice_id",
    "time_field",
)
_GITHUB_PER_PAGE = 100
_GITHUB_TIME_FIELD = "pushed_at"
_GITHUB_USER_AGENT = "ai-productization-observatory"


def _require_non_empty_mapping(payload: dict[str, Any], field_name: str, fixture_path: Path) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict) or not value:
        raise ProcessingError("parse_failure", f"GitHub collector fixture must include {field_name}: {fixture_path}")
    return value


def _parse_window_date(value: str) -> date:
    normalized = value[:10] if "T" in value else value
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ProcessingError("parse_failure", f"GitHub live collector requires ISO date window bounds, got: {value}") from exc


def _window_iso_start(value: str) -> str:
    return f"{value[:10]}T00:00:00Z"


def _pushed_at_within_window(
    pushed_at: Any,
    *,
    window_start: str,
    window_end: str,
) -> bool:
    if not isinstance(pushed_at, str):
        return True
    try:
        pushed_date = _parse_window_date(pushed_at)
    except ProcessingError:
        return True
    return _parse_window_date(window_start) <= pushed_date <= _parse_window_date(window_end)


def _default_watermark_before(window_start: str) -> dict[str, Any]:
    return {
        "time_field": _GITHUB_TIME_FIELD,
        _GITHUB_TIME_FIELD: _window_iso_start(window_start),
        "external_id": "gh_seed_0000",
    }


def _midpoint(start_date: date, end_date: date) -> date:
    delta_days = (end_date - start_date).days
    return start_date + timedelta(days=max(1, delta_days // 2))


def _configured_failure_page() -> int | None:
    raw_value = os.environ.get("APO_GITHUB_LIVE_FAIL_ON_PAGE")
    if not raw_value:
        return None
    try:
        page = int(raw_value)
    except ValueError as exc:
        raise ProcessingError("parse_failure", "APO_GITHUB_LIVE_FAIL_ON_PAGE must be a positive integer") from exc
    if page < 1:
        raise ProcessingError("parse_failure", "APO_GITHUB_LIVE_FAIL_ON_PAGE must be a positive integer")
    return page


def _maybe_inject_configured_failure(current_page: int) -> None:
    configured_page = _configured_failure_page()
    if configured_page != current_page:
        return
    raise ProcessingError("network_error", f"configured GitHub live failure injection on page {current_page}")


def _json_request(
    url: str,
    *,
    headers: dict[str, str],
    timeout_seconds: int,
    request_interval_seconds: int,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, Any]:
    if request_interval_seconds > 0:
        sleep_fn(request_interval_seconds)

    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=ssl.create_default_context()) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_type = "api_429" if exc.code == 429 else "dependency_unavailable"
        raise ProcessingError(error_type, f"HTTP error from upstream {url}: {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProcessingError("network_error", f"Network error while requesting {url}: {exc.reason}") from exc
    except SocketTimeout as exc:
        raise ProcessingError("timeout", f"Timeout while requesting {url}") from exc

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProcessingError("parse_failure", f"Upstream returned invalid JSON from {url}") from exc
    if not isinstance(decoded, dict):
        raise ProcessingError("parse_failure", f"Upstream JSON must be an object for {url}")
    return decoded


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": _GITHUB_USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _read_github_readme(
    full_name: str,
    token: str,
    timeout_seconds: int,
    request_interval_seconds: int,
) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    try:
        payload = _json_request(
            url,
            headers=_github_headers(token),
            timeout_seconds=timeout_seconds,
            request_interval_seconds=request_interval_seconds,
        )
    except ProcessingError:
        return ""

    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return ""
    try:
        return base64.b64decode(content.encode("utf-8")).decode("utf-8", errors="ignore").strip()
    except ValueError:
        return ""


def _validate_resume_state(
    resume_state: dict[str, Any] | None,
    *,
    window_start: str,
    window_end: str,
    expected_query_slice_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if resume_state is None:
        return [{"window_start": window_start, "window_end": window_end, "page": 1}], _default_watermark_before(window_start)

    if not isinstance(resume_state, dict):
        raise ProcessingError("resume_state_invalid", "GitHub live resume_state must be a mapping")
    if resume_state.get("query_slice_id") != expected_query_slice_id:
        raise ProcessingError("resume_state_invalid", "GitHub live resume_state query_slice_id mismatch")
    if resume_state.get("source_window_start") != window_start or resume_state.get("source_window_end") != window_end:
        raise ProcessingError("resume_state_invalid", "GitHub live resume_state window mismatch")

    pending_windows = resume_state.get("pending_windows")
    if not isinstance(pending_windows, list) or not pending_windows:
        raise ProcessingError("resume_state_invalid", "GitHub live resume_state must include pending_windows")

    normalized_windows: list[dict[str, Any]] = []
    for entry in pending_windows:
        if not isinstance(entry, dict):
            raise ProcessingError("resume_state_invalid", "GitHub live pending_windows entries must be mappings")
        entry_window_start = entry.get("window_start")
        entry_window_end = entry.get("window_end")
        entry_page = entry.get("page")
        if not isinstance(entry_window_start, str) or not isinstance(entry_window_end, str):
            raise ProcessingError("resume_state_invalid", "GitHub live pending window bounds must be strings")
        if not isinstance(entry_page, int) or entry_page < 1:
            raise ProcessingError("resume_state_invalid", "GitHub live pending window page must be a positive integer")
        normalized_windows.append(
            {
                "window_start": entry_window_start,
                "window_end": entry_window_end,
                "page": entry_page,
            }
        )

    logical_watermark = resume_state.get("logical_watermark")
    if not isinstance(logical_watermark, dict):
        raise ProcessingError("resume_state_invalid", "GitHub live resume_state must include logical_watermark")
    if logical_watermark.get("time_field") != _GITHUB_TIME_FIELD:
        raise ProcessingError("resume_state_invalid", "GitHub live logical_watermark must preserve time_field = pushed_at")
    if not isinstance(logical_watermark.get("external_id"), str):
        raise ProcessingError("resume_state_invalid", "GitHub live logical_watermark must include external_id")
    if not isinstance(logical_watermark.get(_GITHUB_TIME_FIELD), str):
        raise ProcessingError("resume_state_invalid", "GitHub live logical_watermark must include pushed_at")

    return normalized_windows, dict(logical_watermark)


def _render_query_text(query_text_template: str, *, window_start: str, window_end: str) -> str:
    return query_text_template.replace("WINDOW_START", window_start).replace("WINDOW_END", window_end)


def _request_params(
    *,
    window_start: str,
    window_end: str,
    selection_rule_version: str,
    query_slice_id: str,
    page_or_cursor_start: int,
    page_or_cursor_end: int,
    query_text: str,
    split_windows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    request_params: dict[str, Any] = {
        "window_start": window_start,
        "window_end": window_end,
        "fetch_mode": "search_repositories",
        "page_or_cursor_start": page_or_cursor_start,
        "page_or_cursor_end": page_or_cursor_end,
        "selection_rule_version": selection_rule_version,
        "query_slice_id": query_slice_id,
        "time_field": _GITHUB_TIME_FIELD,
        "query_text": query_text,
    }
    if split_windows:
        request_params["split_windows"] = split_windows
    return request_params


def _build_resume_state(
    *,
    window_start: str,
    window_end: str,
    query_slice_id: str,
    pending_windows: list[dict[str, Any]],
    logical_watermark: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_window_start": window_start,
        "source_window_end": window_end,
        "query_slice_id": query_slice_id,
        "pending_windows": [dict(entry) for entry in pending_windows],
        "logical_watermark": dict(logical_watermark),
    }


def _next_page(total_count: Any, current_page: int, item_count: int) -> int | None:
    if item_count < _GITHUB_PER_PAGE:
        return None
    if isinstance(total_count, int):
        capped_total = min(total_count, 1000)
        if current_page * _GITHUB_PER_PAGE >= capped_total:
            return None
    return current_page + 1


def _should_split(total_count: Any, incomplete_results: Any, start_date: date, end_date: date) -> bool:
    if incomplete_results is True and start_date < end_date:
        return True
    if isinstance(total_count, int) and total_count >= 1000 and start_date < end_date:
        return True
    return False


def _logical_watermark_after(
    watermark: dict[str, Any],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    current = dict(watermark)
    for item in items:
        pushed_at = item.get(_GITHUB_TIME_FIELD)
        external_id = item.get("external_id")
        if not isinstance(pushed_at, str) or not isinstance(external_id, str):
            continue
        if (pushed_at, external_id) >= (
            str(current.get(_GITHUB_TIME_FIELD) or ""),
            str(current.get("external_id") or ""),
        ):
            current[_GITHUB_TIME_FIELD] = pushed_at
            current["external_id"] = external_id
    return current


def collect_live_window(
    *,
    workflow_config: dict[str, Any],
    window_start: str,
    window_end: str,
    query_slice_id: str | None,
    timeout_seconds: int = 30,
    request_interval_seconds: int = 0,
    resume_state: dict[str, Any] | None = None,
    token: str | None = None,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    require_live_discovery_allowed(workflow_config, "github")
    source = source_config(workflow_config, "github")
    slice_config = query_slice_config(workflow_config, "github", query_slice_id)
    source_id = str(source.get("source_id") or "src_github")
    selection_rule_version = str(source.get("selection_rule_version") or "")
    effective_query_slice_id = str(slice_config.get("query_slice_id") or "")
    query_text_template = str(slice_config.get("query_text_template") or "")
    if not selection_rule_version or not effective_query_slice_id or not query_text_template:
        raise ProcessingError("parse_failure", "GitHub live collector requires source selection metadata and query_text_template")

    active_token = token or require_environment_variable("GITHUB_TOKEN")
    pending_windows, watermark_before = _validate_resume_state(
        resume_state,
        window_start=window_start,
        window_end=window_end,
        expected_query_slice_id=effective_query_slice_id,
    )

    collected_at = utc_now_iso()
    shared_state = state if state is not None else {}
    split_windows_seen: list[dict[str, str]] = []
    request_params = _request_params(
        window_start=window_start,
        window_end=window_end,
        selection_rule_version=selection_rule_version,
        query_slice_id=effective_query_slice_id,
        page_or_cursor_start=int(pending_windows[0]["page"]),
        page_or_cursor_end=max(1, int(pending_windows[0]["page"]) - 1),
        query_text=_render_query_text(query_text_template, window_start=window_start, window_end=window_end),
    )
    crawl_run = {
        "crawl_run_id": hashlib.sha256(
            (
                f"{source_id}:{window_start}:{window_end}:{selection_rule_version}:{effective_query_slice_id}:{collected_at}"
            ).encode("utf-8")
        ).hexdigest()[:16],
        "source_id": source_id,
        "source_code": "github",
        "run_unit": "per_source + per_window",
        "window_start": _window_iso_start(window_start),
        "window_end": _window_iso_start(window_end),
        "request_params": request_params,
        "watermark_before": dict(watermark_before),
        "collected_at": collected_at,
        "item_count": 0,
    }
    shared_state.clear()
    shared_state.update(
        {
            "crawl_run": crawl_run,
            "collected_items": [],
            "logical_watermark": dict(watermark_before),
            "resume_state": _build_resume_state(
                window_start=window_start,
                window_end=window_end,
                query_slice_id=effective_query_slice_id,
                pending_windows=pending_windows,
                logical_watermark=watermark_before,
            ),
        }
    )

    headers = _github_headers(active_token)
    while pending_windows:
        current = pending_windows[0]
        leaf_window_start = str(current["window_start"])
        leaf_window_end = str(current["window_end"])
        current_page = int(current["page"])
        leaf_query_text = _render_query_text(query_text_template, window_start=leaf_window_start, window_end=leaf_window_end)
        params = urllib.parse.urlencode({"q": leaf_query_text, "per_page": _GITHUB_PER_PAGE, "page": current_page})
        url = f"https://api.github.com/search/repositories?{params}"
        _maybe_inject_configured_failure(current_page)
        payload = _json_request(
            url,
            headers=headers,
            timeout_seconds=timeout_seconds,
            request_interval_seconds=request_interval_seconds,
        )

        total_count = payload.get("total_count")
        incomplete_results = payload.get("incomplete_results")
        items = payload.get("items")
        if not isinstance(items, list):
            raise ProcessingError("schema_drift", "GitHub search response is missing items[]")

        current_start_date = _parse_window_date(leaf_window_start)
        current_end_date = _parse_window_date(leaf_window_end)
        if _should_split(total_count, incomplete_results, current_start_date, current_end_date):
            split_point = _midpoint(current_start_date, current_end_date)
            left_window = {
                "window_start": current_start_date.isoformat(),
                "window_end": split_point.isoformat(),
                "page": 1,
            }
            right_window = {
                "window_start": (split_point + timedelta(days=1)).isoformat(),
                "window_end": current_end_date.isoformat(),
                "page": 1,
            }
            pending_windows = [left_window, right_window, *pending_windows[1:]]
            split_windows_seen.extend(
                [
                    {"window_start": left_window["window_start"], "window_end": left_window["window_end"]},
                    {"window_start": right_window["window_start"], "window_end": right_window["window_end"]},
                ]
            )
            crawl_run["request_params"] = _request_params(
                window_start=window_start,
                window_end=window_end,
                selection_rule_version=selection_rule_version,
                query_slice_id=effective_query_slice_id,
                page_or_cursor_start=int(pending_windows[0]["page"]),
                page_or_cursor_end=int(crawl_run["request_params"]["page_or_cursor_end"]),
                query_text=request_params["query_text"],
                split_windows=split_windows_seen,
            )
            shared_state["resume_state"] = _build_resume_state(
                window_start=window_start,
                window_end=window_end,
                query_slice_id=effective_query_slice_id,
                pending_windows=pending_windows,
                logical_watermark=shared_state["logical_watermark"],
            )
            continue
        if incomplete_results is True or (isinstance(total_count, int) and total_count >= 1000):
            raise ProcessingError(
                "dependency_unavailable",
                "GitHub search slice could not be exhausted within the current pushed window boundary",
            )

        page_items: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized_item = dict(item)
            if item.get("id") is not None:
                normalized_item["external_id"] = str(item["id"])
            full_name = item.get("full_name")
            normalized_item["readme_text"] = (
                _read_github_readme(
                    full_name,
                    active_token,
                    timeout_seconds,
                    request_interval_seconds,
                )
                if isinstance(full_name, str) and full_name
                else ""
            )
            # GitHub search can return repository payloads whose current pushed_at
            # has drifted past the requested leaf window. Enforce the frozen
            # pushed-window contract before raw persistence and watermark updates.
            if not _pushed_at_within_window(
                normalized_item.get(_GITHUB_TIME_FIELD),
                window_start=leaf_window_start,
                window_end=leaf_window_end,
            ):
                continue
            page_items.append(normalized_item)

        shared_state["collected_items"].extend(page_items)
        shared_state["logical_watermark"] = _logical_watermark_after(shared_state["logical_watermark"], page_items)

        next_page = _next_page(total_count, current_page, len(items))
        crawl_run["item_count"] = len(shared_state["collected_items"])
        crawl_run["request_params"] = _request_params(
            window_start=window_start,
            window_end=window_end,
            selection_rule_version=selection_rule_version,
            query_slice_id=effective_query_slice_id,
            page_or_cursor_start=int(request_params["page_or_cursor_start"]),
            page_or_cursor_end=current_page,
            query_text=request_params["query_text"],
            split_windows=split_windows_seen or None,
        )
        if next_page is None:
            pending_windows = pending_windows[1:]
        else:
            current["page"] = next_page
            pending_windows[0] = current

        shared_state["resume_state"] = _build_resume_state(
            window_start=window_start,
            window_end=window_end,
            query_slice_id=effective_query_slice_id,
            pending_windows=pending_windows,
            logical_watermark=shared_state["logical_watermark"],
        )

    return {
        "crawl_run": dict(crawl_run),
        "items": list(shared_state["collected_items"]),
    }


def collect_fixture_window(
    fixture_path: Path,
    *,
    expected_source_code: str = "github",
    expected_window_start: str | None = None,
    expected_window_end: str | None = None,
    expected_query_slice_id: str | None = None,
    expected_selection_rule_version: str | None = None,
) -> dict[str, Any]:
    try:
        payload = load_json(fixture_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProcessingError("parse_failure", f"Collector fixture is not readable JSON: {fixture_path}") from exc

    if payload.get("source_code") != expected_source_code:
        raise ProcessingError(
            "parse_failure",
            f"Collector fixture must declare source_code={expected_source_code}: {fixture_path}",
        )

    if expected_window_start and payload.get("window_start") != expected_window_start:
        raise ProcessingError(
            "parse_failure",
            f"Collector fixture window_start mismatch: expected {expected_window_start}, got {payload.get('window_start')}",
        )

    if expected_window_end and payload.get("window_end") != expected_window_end:
        raise ProcessingError(
            "parse_failure",
            f"Collector fixture window_end mismatch: expected {expected_window_end}, got {payload.get('window_end')}",
        )

    request_params = _require_non_empty_mapping(payload, "request_params", fixture_path)
    watermark_before = _require_non_empty_mapping(payload, "watermark_before", fixture_path)
    source_id = payload.get("source_id")
    window_start = payload.get("window_start")
    window_end = payload.get("window_end")
    if not source_id or not window_start or not window_end:
        raise ProcessingError("parse_failure", f"Collector fixture is missing source identity or window bounds: {fixture_path}")

    missing_request_params = [field for field in _REQUIRED_REQUEST_PARAM_FIELDS if field not in request_params]
    if missing_request_params:
        joined = ", ".join(missing_request_params)
        raise ProcessingError("parse_failure", f"GitHub collector fixture request_params missing required fields: {joined}")

    if request_params.get("time_field") != "pushed_at":
        raise ProcessingError("parse_failure", "GitHub collector fixture must preserve time_field = pushed_at")
    if watermark_before.get("time_field") != "pushed_at":
        raise ProcessingError("parse_failure", "GitHub collector fixture watermark_before must preserve time_field = pushed_at")

    if expected_query_slice_id and request_params.get("query_slice_id") != expected_query_slice_id:
        raise ProcessingError(
            "parse_failure",
            f"Collector fixture query_slice_id mismatch: expected {expected_query_slice_id}, got {request_params.get('query_slice_id')}",
        )
    if expected_selection_rule_version and request_params.get("selection_rule_version") != expected_selection_rule_version:
        raise ProcessingError(
            "parse_failure",
            "Collector fixture selection_rule_version mismatch: "
            f"expected {expected_selection_rule_version}, got {request_params.get('selection_rule_version')}",
        )

    items = payload.get("items", [])
    if not items:
        raise ProcessingError("parse_failure", f"Collector fixture contains no items: {fixture_path}")

    crawl_run_id = hashlib.sha256(
        f"{source_id}:{window_start}:{window_end}:{request_params['selection_rule_version']}:{request_params['query_slice_id']}".encode(
            "utf-8"
        )
    ).hexdigest()[:16]
    collected_at = utc_now_iso()

    return {
        "crawl_run": {
            "crawl_run_id": crawl_run_id,
            "source_id": source_id,
            "source_code": payload["source_code"],
            "run_unit": "per_source + per_window",
            "window_start": window_start,
            "window_end": window_end,
            "request_params": request_params,
            "watermark_before": watermark_before,
            "collected_at": collected_at,
            "item_count": len(items),
        },
        "items": items,
    }
