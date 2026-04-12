"""Observation construction for append-only Phase1-D facts."""

from __future__ import annotations

from hashlib import sha1
from typing import Any

from src.common.files import utc_now_iso

MODULE_NAME = "observation_builder"
RELATION_MAPPING_VERSION = "relation_mapping_v1"


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_product_source_item_pair",
        "version_dependency": RELATION_MAPPING_VERSION,
    }


def build_observation(
    product: dict[str, Any],
    source_item: dict[str, Any],
    *,
    relation_mapping_version: str = RELATION_MAPPING_VERSION,
    created_at: str | None = None,
) -> dict[str, Any]:
    observed_at = source_item.get("published_at") or source_item.get("latest_observed_at") or utc_now_iso()
    relation_type = _relation_type_for_source(source_item.get("source_id"))
    observation_id = sha1(
        f"{product['product_id']}|{source_item['raw_id']}|{observed_at}|{relation_type}|{relation_mapping_version}".encode(
            "utf-8"
        )
    ).hexdigest()[:12]
    return {
        "observation_id": f"obs_{observation_id}",
        "product_id": product["product_id"],
        "source_item_id": source_item.get("source_item_id") or source_item["external_id"],
        "observed_at": observed_at,
        "relation_type": relation_type,
        "metrics_snapshot": source_item.get("current_metrics_json"),
        "raw_id": source_item.get("raw_id"),
        "created_at": created_at or utc_now_iso(),
    }


def _relation_type_for_source(source_id: str | None) -> str:
    if source_id == "src_product_hunt":
        return "launch"
    if source_id == "src_github":
        return "repo"
    return "directory_listing"
