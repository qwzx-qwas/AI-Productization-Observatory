"""GitHub collector fixture loader for replayable Phase1-B request boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

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


def _require_non_empty_mapping(payload: dict[str, Any], field_name: str, fixture_path: Path) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict) or not value:
        raise ProcessingError("parse_failure", f"GitHub collector fixture must include {field_name}: {fixture_path}")
    return value


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
