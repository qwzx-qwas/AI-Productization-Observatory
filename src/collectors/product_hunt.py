"""Fixture-driven Product Hunt collector for the minimal replay baseline."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import load_json, utc_now_iso


def collect_fixture_window(fixture_path: Path) -> dict[str, Any]:
    payload = load_json(fixture_path)
    if payload.get("source_code") != "product_hunt":
        raise ContractValidationError(f"Collector fixture must declare source_code=product_hunt: {fixture_path}")

    items = payload.get("items", [])
    if not items:
        raise ProcessingError("parse_failure", f"Collector fixture contains no items: {fixture_path}")

    crawl_run_id = hashlib.sha256(
        f"{payload['source_id']}:{payload['window_start']}:{payload['window_end']}".encode("utf-8")
    ).hexdigest()[:16]

    return {
        "crawl_run": {
            "crawl_run_id": crawl_run_id,
            "source_id": payload["source_id"],
            "source_code": payload["source_code"],
            "run_unit": "per_source + per_window",
            "window_start": payload["window_start"],
            "window_end": payload["window_end"],
            "request_params": payload["request_params"],
            "watermark_before": payload["watermark_before"],
            "collected_at": utc_now_iso(),
            "item_count": len(items),
        },
        "items": items,
    }
