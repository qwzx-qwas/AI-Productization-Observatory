"""Deterministic entity resolution helpers for the Phase1-D baseline."""

from __future__ import annotations

from hashlib import sha1
from typing import Any
from urllib.parse import urlparse

from src.common.files import utc_now_iso

MODULE_NAME = "entity_resolver"
ENTITY_RESOLUTION_VERSION = "entity_resolution_v1"


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_source_item_batch",
        "version_dependency": ENTITY_RESOLUTION_VERSION,
    }


def resolve_source_item(
    source_item: dict[str, Any],
    *,
    existing_products: list[dict[str, Any]] | None = None,
    entity_resolution_version: str = ENTITY_RESOLUTION_VERSION,
    resolved_at: str | None = None,
) -> dict[str, Any]:
    timestamp = resolved_at or utc_now_iso()
    keys = _product_keys_from_source_item(source_item)
    matches = [
        product
        for product in (existing_products or [])
        if _product_keys(product).intersection(keys)
    ]

    if len(matches) > 1:
        return {
            "product": None,
            "entity_match_candidate": _build_candidate(
                source_item=source_item,
                matched_products=matches,
                entity_resolution_version=entity_resolution_version,
                resolved_at=timestamp,
                suggested_action="review",
                confidence=0.55,
            ),
        }

    if len(matches) == 1:
        return {
            "product": _merged_product(matches[0], source_item, entity_resolution_version, timestamp),
            "entity_match_candidate": None,
        }

    return {
        "product": _new_product(source_item, entity_resolution_version, timestamp),
        "entity_match_candidate": None,
    }


def _merged_product(
    product: dict[str, Any],
    source_item: dict[str, Any],
    entity_resolution_version: str,
    timestamp: str,
) -> dict[str, Any]:
    merged = dict(product)
    merged["normalized_name"] = merged.get("normalized_name") or _normalized_name(source_item)
    merged["primary_domain"] = merged.get("primary_domain") or _primary_domain(source_item)
    merged["canonical_homepage_url"] = merged.get("canonical_homepage_url") or source_item.get("linked_homepage_url")
    merged["canonical_repo_url"] = merged.get("canonical_repo_url") or source_item.get("linked_repo_url")
    merged["creator_name"] = merged.get("creator_name") or source_item.get("author_name")
    merged["latest_seen_at"] = source_item.get("latest_observed_at") or merged.get("latest_seen_at") or timestamp
    merged["entity_resolution_version"] = entity_resolution_version
    merged["entity_status"] = "active"
    merged["updated_at"] = timestamp
    merged.setdefault("first_seen_at", source_item.get("first_observed_at") or timestamp)
    merged.setdefault("created_at", timestamp)
    return merged


def _new_product(source_item: dict[str, Any], entity_resolution_version: str, timestamp: str) -> dict[str, Any]:
    product_id_basis = "|".join(sorted(_product_keys_from_source_item(source_item))) or source_item["external_id"]
    return {
        "product_id": f"prod_{sha1(product_id_basis.encode('utf-8')).hexdigest()[:12]}",
        "normalized_name": _normalized_name(source_item),
        "primary_domain": _primary_domain(source_item),
        "canonical_homepage_url": source_item.get("linked_homepage_url"),
        "canonical_repo_url": source_item.get("linked_repo_url"),
        "creator_name": source_item.get("author_name"),
        "first_seen_at": source_item.get("first_observed_at") or timestamp,
        "latest_seen_at": source_item.get("latest_observed_at") or timestamp,
        "entity_resolution_version": entity_resolution_version,
        "entity_status": "active",
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _build_candidate(
    *,
    source_item: dict[str, Any],
    matched_products: list[dict[str, Any]],
    entity_resolution_version: str,
    resolved_at: str,
    suggested_action: str,
    confidence: float,
) -> dict[str, Any]:
    left_source_item_id = source_item.get("source_item_id") or source_item["external_id"]
    right_source_item_id = "|".join(sorted(product["product_id"] for product in matched_products))
    snapshot_hash = sha1(
        f"{left_source_item_id}|{right_source_item_id}|{entity_resolution_version}".encode("utf-8")
    ).hexdigest()
    return {
        "candidate_id": f"emc_{snapshot_hash[:12]}",
        "left_source_item_id": left_source_item_id,
        "right_source_item_id": right_source_item_id,
        "candidate_features_json": {
            "matched_product_ids": [product["product_id"] for product in matched_products],
            "source_item_keys": sorted(_product_keys_from_source_item(source_item)),
        },
        "candidate_snapshot_hash": snapshot_hash,
        "suggested_action": suggested_action,
        "confidence": confidence,
        "status": "open",
        "review_issue_id": None,
        "created_at": resolved_at,
        "updated_at": resolved_at,
        "resolved_at": None,
    }


def _product_keys_from_source_item(source_item: dict[str, Any]) -> set[str]:
    values = {
        _normalize_url(source_item.get("linked_homepage_url")),
        _normalize_url(source_item.get("linked_repo_url")),
        _normalize_url(source_item.get("canonical_url")),
        _primary_domain(source_item),
        _normalized_name(source_item),
    }
    return {value for value in values if value}


def _product_keys(product: dict[str, Any]) -> set[str]:
    values = {
        _normalize_url(product.get("canonical_homepage_url")),
        _normalize_url(product.get("canonical_repo_url")),
        product.get("primary_domain"),
        product.get("normalized_name"),
    }
    return {value for value in values if value}


def _normalized_name(source_item: dict[str, Any]) -> str:
    title = source_item.get("title") or source_item.get("external_id") or "unknown"
    return " ".join(title.lower().replace("-", " ").replace("_", " ").split())


def _primary_domain(source_item: dict[str, Any]) -> str | None:
    for key in ("linked_homepage_url", "canonical_url", "linked_repo_url"):
        normalized = _normalize_url(source_item.get(key))
        if normalized:
            return normalized
    return None


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    value = f"{host}{path}".strip("/")
    return value or None
