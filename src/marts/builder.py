"""Fixture-backed mart builder for the Phase1-F consumption contract."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from typing import Any

from src.common.constants import DEFAULT_MART_VERSION
from src.common.files import dump_json, load_json, load_yaml, utc_now_iso
from src.review.review_packet_builder import build_unresolved_registry_entry, select_effective_taxonomy_assignment

CONTROLLED_VOCAB_DOC = "05_controlled_vocabularies_v0.md"


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
    config_dir = source_registry_path.parent
    source_registry = load_yaml(source_registry_path)
    source_metric_registry = load_yaml(config_dir / "source_metric_registry.yaml")
    taxonomy_config = load_yaml(config_dir / "taxonomy_v0.yaml")
    persona_config = load_yaml(config_dir / "persona_v0.yaml")
    delivery_form_config = load_yaml(config_dir / "delivery_form_v0.yaml")
    vocab_doc_path = config_dir.parent / CONTROLLED_VOCAB_DOC
    source_snapshot = {entry["source_id"]: entry for entry in source_registry["sources"]}
    source_metric_snapshot = {entry["source_id"]: entry for entry in source_metric_registry["definitions"]}
    taxonomy_snapshot = _build_taxonomy_lookup(taxonomy_config)
    controlled_vocab = _load_controlled_vocab_entries(vocab_doc_path)
    generated_at = utc_now_iso()

    top_jtbd: dict[str, set[str]] = defaultdict(set)
    attention_distribution: dict[tuple[str, str], set[str]] = defaultdict(set)
    unresolved_registry: list[dict[str, Any]] = []
    fact_product_observation: list[dict[str, Any]] = []
    dim_product: dict[str, dict[str, Any]] = {}
    dim_source: dict[str, dict[str, Any]] = {}
    dim_taxonomy: dict[str, dict[str, Any]] = {}
    dim_time: dict[str, dict[str, Any]] = {}
    persona_codes_used: set[str] = set()
    delivery_form_codes_used: set[str] = set()
    drill_down_trace: list[dict[str, Any]] = []

    for record in fixture["records"]:
        source = source_snapshot.get(record["source_id"])
        effective_taxonomy = _effective_taxonomy(record)
        unresolved_entry = _unresolved_registry_entry(record, effective_taxonomy)
        if unresolved_entry is not None:
            unresolved_registry.append(unresolved_entry)
        dim_source[record["source_id"]] = _build_dim_source_row(source, record["source_id"])
        dim_product[record["product_id"]] = _build_dim_product_row(
            record,
            effective_taxonomy=effective_taxonomy,
            fixture_version=fixture["fixture_version"],
        )
        persona_codes_used.add(dim_product[record["product_id"]]["current_primary_persona_code"])
        delivery_form_codes_used.add(dim_product[record["product_id"]]["current_delivery_form_code"])
        _register_dim_time_row(dim_time, record.get("observed_at"), fixture["window_end"])
        if effective_taxonomy is not None:
            _register_dim_taxonomy_row(dim_taxonomy, taxonomy_snapshot, effective_taxonomy.get("category_code"))
        if not _is_main_stat_source(source):
            drill_down_trace.append(
                _build_drill_down_trace(
                    record,
                    effective_taxonomy=effective_taxonomy,
                    main_report_included=False,
                    unresolved_entry=unresolved_entry,
                )
            )
            continue
        if not _is_effective_resolved_primary(record):
            drill_down_trace.append(
                _build_drill_down_trace(
                    record,
                    effective_taxonomy=effective_taxonomy,
                    main_report_included=False,
                    unresolved_entry=unresolved_entry,
                )
            )
            continue
        product_id = record["product_id"]
        if effective_taxonomy is None:
            continue
        category_code = effective_taxonomy["category_code"]
        top_jtbd[category_code].add(product_id)
        attention_band = record.get("effective_scores", {}).get("attention_band")
        if attention_band:
            attention_distribution[(category_code, attention_band)].add(product_id)
        fact_product_observation.append(
            _build_fact_row(
                record,
                effective_taxonomy=effective_taxonomy,
                generated_at=generated_at,
                metric_registry_version=source_metric_registry["version"],
                source_metric_definition=source_metric_snapshot.get(record["source_id"]),
                attention_formula_version=_default_attention_formula_version(source_metric_registry),
            )
        )
        drill_down_trace.append(
            _build_drill_down_trace(
                record,
                effective_taxonomy=effective_taxonomy,
                main_report_included=True,
                unresolved_entry=unresolved_entry,
            )
        )

    mart = {
        "mart_version": DEFAULT_MART_VERSION,
        "generated_at": generated_at,
        "window_start": fixture["window_start"],
        "window_end": fixture["window_end"],
        "fact_product_observation": sorted(fact_product_observation, key=lambda row: (row["observed_at"], row["product_id"])),
        "dim_product": [dim_product[product_id] for product_id in sorted(dim_product)],
        "dim_source": [dim_source[source_id] for source_id in sorted(dim_source)],
        "dim_taxonomy": [dim_taxonomy[code] for code in sorted(dim_taxonomy)],
        "dim_persona": _build_controlled_vocab_dimension(
            used_codes=persona_codes_used,
            allowed_codes=persona_config["codes"],
            entries=controlled_vocab["persona"],
        ),
        "dim_delivery_form": _build_controlled_vocab_dimension(
            used_codes=delivery_form_codes_used,
            allowed_codes=delivery_form_config["codes"],
            entries=controlled_vocab["delivery_form"],
        ),
        "dim_time": [dim_time[date_day] for date_day in sorted(dim_time)],
        "top_jtbd_products_30d": [
            {"category_code": category, "product_count": len(product_ids)}
            for category, product_ids in sorted(top_jtbd.items())
        ],
        "attention_distribution_30d": [
            {"category_code": category, "attention_band": band, "product_count": len(product_ids)}
            for (category, band), product_ids in sorted(attention_distribution.items())
        ],
        "unresolved_registry_view": unresolved_registry,
        "dashboard_read_contract": _build_dashboard_read_contract(),
        "drill_down_trace": sorted(drill_down_trace, key=lambda row: (row["path_type"], row["product_id"])),
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


def _build_fact_row(
    record: dict[str, Any],
    *,
    effective_taxonomy: dict[str, Any],
    generated_at: str,
    metric_registry_version: str,
    source_metric_definition: dict[str, Any] | None,
    attention_formula_version: str,
) -> dict[str, Any]:
    scores = record.get("effective_scores") or {}
    relation_type = record.get("relation_type") or _relation_type_for_source(record.get("source_id"))
    return {
        "product_id": record["product_id"],
        "source_id": record["source_id"],
        "source_item_id": record["source_item_id"],
        "observation_id": record["observation_id"],
        "observed_at": record["observed_at"],
        "relation_type": relation_type,
        "attention_raw_value": scores.get("attention_raw_value"),
        "attention_normalized_value": scores.get("attention_normalized_value"),
        "attention_band": scores.get("attention_band"),
        "attention_metric_definition_version": (
            scores.get("attention_metric_definition_version")
            or (source_metric_definition or {}).get("metric_definition_version")
        ),
        "build_evidence_band": scores.get("build_evidence_band"),
        "commercial_band": scores.get("commercial_band"),
        "taxonomy_primary_code": effective_taxonomy["category_code"],
        "metric_version": metric_registry_version,
        "attention_formula_version": scores.get("attention_formula_version") or attention_formula_version,
        "mart_built_at": generated_at,
    }


def _build_dim_product_row(
    record: dict[str, Any],
    *,
    effective_taxonomy: dict[str, Any] | None,
    fixture_version: str,
) -> dict[str, Any]:
    product = record.get("product") if isinstance(record.get("product"), dict) else {}
    profile = record.get("effective_profile") if isinstance(record.get("effective_profile"), dict) else {}
    effective_category = effective_taxonomy.get("category_code") if effective_taxonomy else None
    return {
        "product_id": record["product_id"],
        "normalized_name": product.get("normalized_name"),
        "primary_domain": product.get("primary_domain"),
        "canonical_homepage_url": product.get("canonical_homepage_url"),
        "canonical_repo_url": product.get("canonical_repo_url"),
        "current_profile_version": profile.get("profile_version"),
        "current_primary_persona_code": profile.get("primary_persona_code") or "unknown",
        "current_delivery_form_code": profile.get("delivery_form_code") or "unknown",
        "current_taxonomy_version": effective_taxonomy.get("taxonomy_version") if effective_taxonomy else None,
        "is_unresolved": effective_category == "unresolved",
        "effective_result_version": record.get("effective_result_version") or fixture_version,
    }


def _build_dim_source_row(source: dict[str, Any] | None, source_id: str) -> dict[str, Any]:
    source = source or {}
    return {
        "source_id": source_id,
        "source_code": source.get("source_code"),
        "source_name": source.get("source_name"),
        "source_type": source.get("source_type"),
        "primary_role": source.get("primary_role"),
        "enabled": source.get("enabled"),
    }


def _build_dashboard_read_contract() -> dict[str, Any]:
    return {
        "main_report_dataset": "fact_product_observation",
        "main_report_semantics": "effective resolved taxonomy",
        "main_stat_source_predicate": "enabled = true and primary_role = supply_primary",
        "runtime_detail_join_allowed": False,
        "cards": [
            {
                "card_id": "top_jtbd_products_30d",
                "reads_from": "top_jtbd_products_30d",
                "window_days": 30,
                "drill_down_enabled": True,
            },
            {
                "card_id": "attention_distribution_30d",
                "reads_from": "attention_distribution_30d",
                "window_days": 30,
                "drill_down_enabled": True,
            },
            {
                "card_id": "unresolved_backlog",
                "reads_from": "unresolved_registry_view",
                "window_days": None,
                "drill_down_enabled": True,
            },
        ],
        "supporting_views": [
            "dim_product",
            "dim_source",
            "dim_taxonomy",
            "dim_persona",
            "dim_delivery_form",
            "dim_time",
            "unresolved_registry_view",
        ],
        "drill_down_objects": [
            "product",
            "observation",
            "evidence",
            "taxonomy_assignment",
            "score_component",
            "review_issue",
        ],
    }


def _build_drill_down_trace(
    record: dict[str, Any],
    *,
    effective_taxonomy: dict[str, Any] | None,
    main_report_included: bool,
    unresolved_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    refs = record.get("drill_down_refs") if isinstance(record.get("drill_down_refs"), dict) else {}
    path_type = "source_to_main_mart" if main_report_included else "effective_unresolved_registry"
    if not main_report_included and unresolved_entry is None:
        path_type = "excluded_from_main_mart"
    return {
        "product_id": record["product_id"],
        "source_id": record["source_id"],
        "source_item_id": refs.get("source_item_id") or record.get("source_item_id"),
        "observation_id": refs.get("observation_id") or record.get("observation_id"),
        "evidence_ids": list(refs.get("evidence_ids") or []),
        "review_issue_ids": list(refs.get("review_issue_ids") or []),
        "effective_taxonomy_code": effective_taxonomy.get("category_code") if effective_taxonomy else None,
        "main_report_included": main_report_included,
        "unresolved_registry_required": unresolved_entry is not None,
        "path_type": path_type,
    }


def _register_dim_time_row(dim_time: dict[str, dict[str, Any]], observed_at: object, window_end: object) -> None:
    if not isinstance(observed_at, str) or not isinstance(window_end, str):
        return
    observed_at_dt = _parse_iso8601(observed_at)
    window_end_dt = _parse_iso8601(window_end)
    date_day = observed_at_dt.date().isoformat()
    iso_year, iso_week, _ = observed_at_dt.isocalendar()
    dim_time[date_day] = {
        "date_day": date_day,
        "year": observed_at_dt.year,
        "month": observed_at_dt.month,
        "week": f"{iso_year}-W{iso_week:02d}",
        "rolling_30d_flag": observed_at_dt >= window_end_dt - timedelta(days=30),
        "rolling_90d_flag": observed_at_dt >= window_end_dt - timedelta(days=90),
    }


def _build_taxonomy_lookup(taxonomy_config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for node in taxonomy_config.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        code = node.get("code")
        if not isinstance(code, str):
            continue
        lookup[code] = {
            "taxonomy_version": taxonomy_config.get("version"),
            "category_code": code,
            "label": node.get("label"),
            "level": node.get("level"),
            "parent_code": node.get("parent_code"),
            "is_deprecated": False,
        }
        for child in node.get("stable_l2_examples") or []:
            if not isinstance(child, dict) or not isinstance(child.get("code"), str):
                continue
            lookup[child["code"]] = {
                "taxonomy_version": taxonomy_config.get("version"),
                "category_code": child["code"],
                "label": child.get("label"),
                "level": 2,
                "parent_code": code,
                "is_deprecated": False,
            }
    return lookup


def _register_dim_taxonomy_row(
    dim_taxonomy: dict[str, dict[str, Any]],
    taxonomy_snapshot: dict[str, dict[str, Any]],
    category_code: object,
) -> None:
    if not isinstance(category_code, str) or category_code == "unresolved":
        return
    taxonomy_row = taxonomy_snapshot.get(category_code)
    if taxonomy_row is None:
        return
    dim_taxonomy[category_code] = taxonomy_row


def _build_controlled_vocab_dimension(
    *,
    used_codes: set[str],
    allowed_codes: list[str],
    entries: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    dimension: list[dict[str, Any]] = []
    allowed = set(allowed_codes)
    for code in sorted(used_codes):
        if code not in allowed:
            raise ValueError(f"Unexpected controlled vocabulary code in mart fixture: {code}")
        entry = entries.get(code)
        if entry is None:
            raise ValueError(f"Missing controlled vocabulary doc entry for mart fixture code: {code}")
        dimension.append(
            {
                "code": code,
                "label": entry["label"],
                "definition": entry["definition"],
                "is_unknown": code == "unknown",
            }
        )
    return dimension


def _load_controlled_vocab_entries(markdown_path: Path) -> dict[str, dict[str, dict[str, str]]]:
    text = markdown_path.read_text(encoding="utf-8")
    return {
        "persona": _extract_codebook(text, start_heading="## 2. Persona Codes", end_heading="## 3. Delivery Form Codes"),
        "delivery_form": _extract_codebook(text, start_heading="## 3. Delivery Form Codes", end_heading="## 4. Relation Type"),
    }


def _extract_codebook(text: str, *, start_heading: str, end_heading: str) -> dict[str, dict[str, str]]:
    try:
        section = text.split(start_heading, maxsplit=1)[1].split(end_heading, maxsplit=1)[0]
    except IndexError as exc:
        raise ValueError(f"Unable to locate controlled vocabulary section: {start_heading}") from exc

    entries: dict[str, dict[str, str]] = {}
    current_code: str | None = None
    for raw_line in section.splitlines():
        line = raw_line.strip()
        code_match = re.match(r"- `code`: `([^`]+)`", line)
        if code_match:
            current_code = code_match.group(1)
            entries[current_code] = {}
            continue
        if current_code is None:
            continue
        label_match = re.match(r"- `label`: `([^`]+)`", line)
        if label_match:
            entries[current_code]["label"] = label_match.group(1)
            continue
        definition_match = re.match(r"- `definition`: (.+)", line)
        if definition_match:
            entries[current_code]["definition"] = definition_match.group(1).strip().strip("`")
    return entries


def _default_attention_formula_version(source_metric_registry: dict[str, Any]) -> str:
    for key in source_metric_registry:
        if key.endswith("_policy"):
            return key.removesuffix("_policy")
    return "attention_v1"


def _parse_iso8601(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _relation_type_for_source(source_id: object) -> str | None:
    if source_id == "src_product_hunt":
        return "launch"
    if source_id == "src_github":
        return "repo"
    return None
