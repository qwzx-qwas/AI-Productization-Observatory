"""Fixture-backed mart builder that consumes effective resolved results only."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from src.common.constants import DEFAULT_MART_VERSION
from src.common.files import dump_json, load_json, load_yaml, utc_now_iso
from src.review.review_packet_builder import build_unresolved_registry_entry, select_effective_taxonomy_assignment


def _is_main_stat_source(source: dict[str, Any] | None) -> bool:
    return bool(source and source.get("enabled") and source.get("primary_role") == "supply_primary")


def _is_effective_resolved_primary(record: dict[str, Any]) -> bool:
    taxonomy = _effective_taxonomy(record) or {}
    return (
        taxonomy.get("label_role") == "primary"
        and taxonomy.get("result_status") == "active"
        and taxonomy.get("category_code")
        and taxonomy.get("category_code") != "unresolved"
    )


def build_mart_from_fixture(fixture_path: Path, source_registry_path: Path, output_path: Path | None = None) -> dict[str, Any]:
    fixture = load_json(fixture_path)
    source_registry = load_yaml(source_registry_path)
    source_snapshot = {entry["source_id"]: entry for entry in source_registry["sources"]}

    top_jtbd: dict[str, set[str]] = defaultdict(set)
    attention_distribution: dict[tuple[str, str], set[str]] = defaultdict(set)
    unresolved_registry: list[dict[str, Any]] = []

    for record in fixture["records"]:
        source = source_snapshot.get(record["source_id"])
        effective_taxonomy = _effective_taxonomy(record)
        unresolved_entry = _unresolved_registry_entry(record, effective_taxonomy)
        if unresolved_entry is not None:
            unresolved_registry.append(unresolved_entry)
        if not _is_main_stat_source(source):
            continue
        if not _is_effective_resolved_primary(record):
            continue
        product_id = record["product_id"]
        if effective_taxonomy is None:
            continue
        category_code = effective_taxonomy["category_code"]
        top_jtbd[category_code].add(product_id)
        attention_band = record.get("effective_scores", {}).get("attention_band")
        if attention_band:
            attention_distribution[(category_code, attention_band)].add(product_id)

    mart = {
        "mart_version": DEFAULT_MART_VERSION,
        "generated_at": utc_now_iso(),
        "window_start": fixture["window_start"],
        "window_end": fixture["window_end"],
        "top_jtbd_products_30d": [
            {"category_code": category, "product_count": len(product_ids)}
            for category, product_ids in sorted(top_jtbd.items())
        ],
        "attention_distribution_30d": [
            {"category_code": category, "attention_band": band, "product_count": len(product_ids)}
            for (category, band), product_ids in sorted(attention_distribution.items())
        ],
        "unresolved_registry_view": unresolved_registry,
    }

    if output_path is not None:
        dump_json(output_path, mart)
    return mart


def _effective_taxonomy(record: dict[str, Any]) -> dict[str, Any] | None:
    assignments = record.get("taxonomy_assignments")
    if isinstance(assignments, list) and assignments:
        return select_effective_taxonomy_assignment(assignments, label_role="primary")
    taxonomy = record.get("effective_taxonomy")
    return taxonomy if isinstance(taxonomy, dict) else None


def _unresolved_registry_entry(
    record: dict[str, Any],
    effective_taxonomy: dict[str, Any] | None,
) -> dict[str, Any] | None:
    review_issues = record.get("review_issues")
    if isinstance(review_issues, list) and review_issues:
        return build_unresolved_registry_entry(review_issues, effective_taxonomy)
    entry = record.get("unresolved_registry_entry")
    return entry if isinstance(entry, dict) else None
