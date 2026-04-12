"""Product Hunt normalizer that preserves raw traceability and null-safe mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.errors import ContractValidationError, ProcessingError
from src.common.schema import validate_instance
from src.runtime.raw_store.file_store import FileRawStore

_PRODUCT_HUNT_NORMALIZATION_VERSION = "product_hunt_v1"


def _excerpt(value: str | None, limit: int = 240) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split())
    return compact[:limit]


def normalize_raw_record(
    raw_record: dict[str, Any],
    raw_store: FileRawStore,
    schema_path: Path,
    normalization_version: str = _PRODUCT_HUNT_NORMALIZATION_VERSION,
) -> dict[str, Any]:
    payload = raw_store.load_payload(raw_record["raw_payload_ref"])
    published_at = payload.get("published_at")

    source_item = {
        "raw_id": raw_record["raw_id"],
        "source_id": raw_record["source_id"],
        "external_id": raw_record["external_id"],
        "canonical_url": payload.get("product_url"),
        "linked_homepage_url": payload.get("website_url"),
        "linked_repo_url": payload.get("github_url"),
        "title": payload.get("name"),
        "author_name": payload.get("maker_name"),
        "author_handle": payload.get("maker_handle"),
        "published_at": published_at,
        "raw_text_excerpt": _excerpt(payload.get("description") or payload.get("tagline")),
        "current_summary": _excerpt(payload.get("tagline"), limit=160),
        "current_metrics_json": payload.get("metrics"),
        "topics": payload.get("topics"),
        "language": payload.get("language"),
        "item_status": payload.get("status"),
        "first_observed_at": published_at or raw_record.get("fetched_at") or raw_record["collected_at"],
        "latest_observed_at": raw_record.get("fetched_at") or raw_record["collected_at"],
        "normalization_version": normalization_version,
    }

    try:
        validate_instance(source_item, schema_path)
    except ContractValidationError as exc:
        raise ProcessingError("json_schema_validation_failed", str(exc)) from exc
    return source_item
