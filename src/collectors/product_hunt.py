"""Fixture-driven Product Hunt collector for the minimal replay baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.common.errors import ProcessingError
from src.common.files import load_json, utc_now_iso


def collect_fixture_window(
    fixture_path: Path,
    *,
    expected_source_code: str = "product_hunt",
    expected_window_start: str | None = None,
    expected_window_end: str | None = None,
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

    request_params = payload.get("request_params")
    watermark_before = payload.get("watermark_before")
    source_id = payload.get("source_id")
    window_start = payload.get("window_start")
    window_end = payload.get("window_end")
    if not isinstance(request_params, dict) or not isinstance(watermark_before, dict):
        raise ProcessingError("parse_failure", f"Collector fixture must include request_params and watermark_before: {fixture_path}")
    if not source_id or not window_start or not window_end:
        raise ProcessingError("parse_failure", f"Collector fixture is missing source identity or window bounds: {fixture_path}")

    items = payload.get("items", [])
    if not items:
        raise ProcessingError("parse_failure", f"Collector fixture contains no items: {fixture_path}")

    crawl_run_id = hashlib.sha256(
        f"{source_id}:{window_start}:{window_end}".encode("utf-8")
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
