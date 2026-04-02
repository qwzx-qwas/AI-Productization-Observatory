"""Source discovery adapters for candidate prescreening."""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from socket import timeout as SocketTimeout
from typing import Any

from src.candidate_prescreen.config import query_slice_config, source_config
from src.candidate_prescreen.relay import clean_raw_evidence_excerpt
from src.common.config import require_environment_variable
from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import load_json


def _parse_window(window: str) -> tuple[date, date]:
    try:
        start_text, end_text = window.split("..", 1)
        return date.fromisoformat(start_text), date.fromisoformat(end_text)
    except ValueError as exc:
        raise ContractValidationError(f"window must look like YYYY-MM-DD..YYYY-MM-DD, got: {window}") from exc


def _window_text(start: date, end: date) -> str:
    return f"{start.isoformat()}..{end.isoformat()}"


def _midpoint(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=max(1, delta // 2))


def _json_request(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    body = None
    request_headers = dict(headers or {})
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
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


def _read_github_readme(full_name: str, token: str, timeout_seconds: int) -> str:
    url = f"https://api.github.com/repos/{full_name}/readme"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-productization-observatory",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        payload = _json_request(url, headers=headers, timeout_seconds=timeout_seconds)
    except ProcessingError:
        return ""
    content = payload.get("content")
    encoding = payload.get("encoding")
    if not isinstance(content, str) or encoding != "base64":
        return ""
    try:
        decoded = base64.b64decode(content.encode("utf-8")).decode("utf-8", errors="ignore")
    except ValueError:
        return ""
    return decoded.strip()


def _normalize_fixture_item(
    payload: dict[str, Any],
    *,
    source_code: str,
    window: str,
    expected_query_slice_id: str | None,
) -> list[dict[str, Any]]:
    if payload.get("source") != source_code:
        raise ContractValidationError(f"Fixture source mismatch: expected {source_code}, got {payload.get('source')}")
    if payload.get("window") != window:
        raise ContractValidationError(f"Fixture window mismatch: expected {window}, got {payload.get('window')}")
    if expected_query_slice_id is not None and payload.get("query_slice_id") != expected_query_slice_id:
        raise ContractValidationError(
            f"Fixture query_slice_id mismatch: expected {expected_query_slice_id}, got {payload.get('query_slice_id')}"
        )
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ContractValidationError("Candidate discovery fixture must contain a non-empty items list")
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ContractValidationError("Candidate discovery fixture items must be mappings")
        fixture_item = dict(item)
        fixture_item["raw_evidence_excerpt"] = clean_raw_evidence_excerpt(fixture_item.get("raw_evidence_excerpt"))
        normalized.append(fixture_item)
    return normalized


def discover_candidates(
    workflow_config: dict[str, Any],
    *,
    source_code: str,
    window: str,
    query_slice_id: str | None,
    limit: int,
    fixture_path: Path | None,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    slice_config = query_slice_config(workflow_config, source_code, query_slice_id)
    if fixture_path is not None:
        fixture_payload = load_json(fixture_path)
        if not isinstance(fixture_payload, dict):
            raise ContractValidationError(f"Fixture {fixture_path} must be a JSON object")
        return _normalize_fixture_item(
            fixture_payload,
            source_code=source_code,
            window=window,
            expected_query_slice_id=slice_config.get("query_slice_id"),
        )[:limit]
    if source_code == "github":
        return _discover_github_live(workflow_config, window=window, slice_config=slice_config, limit=limit, timeout_seconds=timeout_seconds)
    if source_code == "product_hunt":
        return _discover_product_hunt_live(
            workflow_config,
            window=window,
            slice_config=slice_config,
            limit=limit,
            timeout_seconds=timeout_seconds,
        )
    raise ContractValidationError(f"Unsupported source_code for candidate prescreen discovery: {source_code}")


def _discover_github_live(
    workflow_config: dict[str, Any],
    *,
    window: str,
    slice_config: dict[str, Any],
    limit: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    token = require_environment_variable("GITHUB_TOKEN")
    start_date, end_date = _parse_window(window)
    return _discover_github_window(
        workflow_config,
        slice_config=slice_config,
        token=token,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        timeout_seconds=timeout_seconds,
    )


def _discover_github_window(
    workflow_config: dict[str, Any],
    *,
    slice_config: dict[str, Any],
    token: str,
    start_date: date,
    end_date: date,
    limit: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    query_text = str(slice_config.get("query_text_template", "")).replace("WINDOW_START", start_date.isoformat()).replace(
        "WINDOW_END",
        end_date.isoformat(),
    )
    params = urllib.parse.urlencode({"q": query_text, "per_page": min(100, limit), "page": 1})
    url = f"https://api.github.com/search/repositories?{params}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "ai-productization-observatory",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = _json_request(url, headers=headers, timeout_seconds=timeout_seconds)
    total_count = payload.get("total_count")
    incomplete_results = payload.get("incomplete_results")
    if (total_count == 1000 or incomplete_results is True) and start_date < end_date:
        split_point = _midpoint(start_date, end_date)
        left = _discover_github_window(
            workflow_config,
            slice_config=slice_config,
            token=token,
            start_date=start_date,
            end_date=split_point,
            limit=limit,
            timeout_seconds=timeout_seconds,
        )
        remaining = max(0, limit - len(left))
        right_start = split_point + timedelta(days=1)
        right = _discover_github_window(
            workflow_config,
            slice_config=slice_config,
            token=token,
            start_date=right_start,
            end_date=end_date,
            limit=remaining,
            timeout_seconds=timeout_seconds,
        )
        return (left + right)[:limit]
    items = payload.get("items")
    if not isinstance(items, list):
        raise ProcessingError("schema_drift", "GitHub search response is missing items[]")
    normalized: list[dict[str, Any]] = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        full_name = item.get("full_name")
        readme_excerpt = _read_github_readme(full_name, token, timeout_seconds) if isinstance(full_name, str) and full_name else ""
        summary = item.get("description") or ""
        readable_excerpt = clean_raw_evidence_excerpt("\n\n".join(part for part in [summary, readme_excerpt] if part))
        normalized.append(
            {
                "external_id": str(item.get("id")),
                "canonical_url": item.get("html_url"),
                "title": item.get("name") or full_name or "",
                "summary": summary,
                "author_name": ((item.get("owner") or {}).get("login") if isinstance(item.get("owner"), dict) else None),
                "linked_homepage_url": item.get("homepage"),
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": item.get("pushed_at"),
                "raw_evidence_excerpt": readable_excerpt,
                "topics": item.get("topics") if isinstance(item.get("topics"), list) else [],
                "language": item.get("language"),
                "current_metrics_json": {
                    "star_count": item.get("stargazers_count"),
                    "fork_count": item.get("forks_count"),
                    "watcher_count": item.get("watchers_count"),
                },
            }
        )
    return normalized


def _discover_product_hunt_live(
    workflow_config: dict[str, Any],
    *,
    window: str,
    slice_config: dict[str, Any],
    limit: int,
    timeout_seconds: int,
) -> list[dict[str, Any]]:
    token = require_environment_variable("PRODUCT_HUNT_TOKEN")
    start_date, end_date = _parse_window(window)
    query = """
    query CandidatePosts($first: Int!, $after: String, $postedAfter: DateTime!, $postedBefore: DateTime!) {
      posts(first: $first, after: $after, postedAfter: $postedAfter, postedBefore: $postedBefore) {
        edges {
          cursor
          node {
            id
            name
            tagline
            description
            url
            website
            createdAt
            featuredAt
            votesCount
            commentsCount
            topics {
              edges {
                node {
                  name
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ai-productization-observatory",
    }
    payload = _json_request(
        "https://api.producthunt.com/v2/api/graphql",
        method="POST",
        headers=headers,
        payload={
            "query": query,
            "variables": {
                "first": min(50, limit),
                "after": None,
                "postedAfter": f"{start_date.isoformat()}T00:00:00Z",
                "postedBefore": f"{end_date.isoformat()}T23:59:59Z",
            },
        },
        timeout_seconds=timeout_seconds,
    )
    data = payload.get("data")
    posts = ((data or {}).get("posts") if isinstance(data, dict) else None)
    edges = ((posts or {}).get("edges") if isinstance(posts, dict) else None)
    if not isinstance(edges, list):
        raise ProcessingError("schema_drift", "Product Hunt GraphQL response is missing data.posts.edges[]")
    normalized: list[dict[str, Any]] = []
    for edge in edges[:limit]:
        if not isinstance(edge, dict):
            continue
        node = edge.get("node")
        if not isinstance(node, dict):
            continue
        topics = []
        topic_edges = (((node.get("topics") or {}).get("edges")) if isinstance(node.get("topics"), dict) else None)
        if isinstance(topic_edges, list):
            for topic_edge in topic_edges:
                topic_node = ((topic_edge or {}).get("node")) if isinstance(topic_edge, dict) else None
                if isinstance(topic_node, dict) and isinstance(topic_node.get("name"), str):
                    topics.append(topic_node["name"].lower())
        summary = node.get("tagline") or node.get("description") or ""
        description = node.get("description") or ""
        normalized.append(
            {
                "external_id": str(node.get("id")),
                "canonical_url": node.get("url"),
                "title": node.get("name") or "",
                "summary": summary,
                "author_name": node.get("name"),
                "linked_homepage_url": node.get("website"),
                "linked_repo_url": None,
                "published_at": node.get("featuredAt") or node.get("createdAt"),
                "pushed_at": None,
                "raw_evidence_excerpt": "\n\n".join(part for part in [summary, description] if part),
                "topics": topics,
                "language": None,
                "current_metrics_json": {
                    "vote_count": node.get("votesCount"),
                    "comment_count": node.get("commentsCount"),
                },
            }
        )
    return normalized


def discovery_metadata(
    workflow_config: dict[str, Any],
    *,
    source_code: str,
    window: str,
    query_slice_id: str | None,
    discovery_mode: str,
) -> dict[str, Any]:
    source = source_config(workflow_config, source_code)
    slice_config = query_slice_config(workflow_config, source_code, query_slice_id)
    start_text, end_text = window.split("..", 1)
    return {
        "source_id": source.get("source_id"),
        "time_field": source.get("time_field"),
        "query_family": slice_config.get("query_family"),
        "query_slice_id": slice_config.get("query_slice_id"),
        "selection_rule_version": source.get("selection_rule_version"),
        "discovery_mode": discovery_mode,
        "selection_basis": {
            "window_start": start_text,
            "window_end": end_text,
            "query_family": slice_config.get("query_family"),
            "query_slice_id": slice_config.get("query_slice_id"),
            "selection_rule_version": source.get("selection_rule_version"),
        },
    }
