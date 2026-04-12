"""Score derivation constrained by rubric_v0 and source_metric_registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.files import load_yaml, utc_now_iso
from src.common.schema import validate_instance

MODULE_NAME = "score_engine"
COMPUTED_BY = "score_engine_v1"


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_product",
        "version_dependency": COMPUTED_BY,
    }


def score_product(
    product: dict[str, Any],
    product_profile: dict[str, Any],
    evidence: list[dict[str, Any]],
    observation: dict[str, Any],
    source_item: dict[str, Any],
    *,
    config_dir: Path,
    schema_dir: Path,
    benchmark_observations: list[dict[str, Any]] | None = None,
    computed_at: str | None = None,
    computed_by: str = COMPUTED_BY,
) -> dict[str, Any]:
    rubric = load_yaml(config_dir / "rubric_v0.yaml")
    source_metric_registry = load_yaml(config_dir / "source_metric_registry.yaml")
    timestamp = computed_at or utc_now_iso()
    score_run = {
        "score_run_id": f"score_run_{product['product_id']}_{rubric['version']}",
        "target_type": "product",
        "target_id": product["product_id"],
        "rubric_version": rubric["version"],
        "computed_at": timestamp,
        "computed_by": computed_by,
        "score_scope": "phase1_main",
        "is_override": False,
        "override_review_issue_id": None,
        "created_at": timestamp,
    }

    evidence_refs = [_evidence_ref(item) for item in evidence]
    components = [
        _build_evidence_component(evidence_refs, evidence),
        _need_clarity_component(evidence_refs, evidence, product_profile),
        _attention_component(
            evidence_refs,
            observation,
            source_item,
            benchmark_observations or [],
            source_metric_registry,
        ),
        _commercial_component(evidence_refs, evidence, product),
        _persistence_component([_observation_ref(observation)]),
    ]

    for component in components:
        validate_instance(component, schema_dir / "score_component.schema.json")

    return {"score_run": score_run, "score_components": components}


def _build_evidence_component(evidence_refs: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    build_evidence = [item for item in evidence if item["evidence_type"] in {"build_tool_claim", "prompt_demo", "build_speed_claim"}]
    high_confidence = any(item["evidence_strength"] == "high" for item in build_evidence)
    if len(build_evidence) >= 2 or high_confidence:
        band = "high"
        rationale = "Traceable build evidence is present in multiple or high-strength snippets."
    elif build_evidence:
        band = "medium"
        rationale = "Build evidence exists, but it is not strong enough for a high-confidence band."
    else:
        band = "low"
        rationale = "Only broad product claims exist; stable build evidence is missing."
    return {
        "score_type": "build_evidence_score",
        "raw_value": None,
        "normalized_value": None,
        "band": band,
        "rationale": rationale,
        "evidence_refs_json": evidence_refs[: max(1, min(len(evidence_refs), 3))],
    }


def _need_clarity_component(
    evidence_refs: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    product_profile: dict[str, Any],
) -> dict[str, Any]:
    unclear = any(item["evidence_type"] == "unclear_description_signal" for item in evidence)
    has_job = bool(product_profile.get("one_sentence_job"))
    has_persona = product_profile.get("primary_persona_code") not in {None, "unknown"}
    has_delivery = product_profile.get("delivery_form_code") not in {None, "unknown"}
    known_fields = sum([has_job, has_persona, has_delivery])

    if unclear or known_fields <= 1:
        band = "low"
        rationale = "Only broad or ambiguous product description is available, so taxonomy should not be forced."
    elif known_fields == 2:
        band = "medium"
        rationale = "An initial judgment is possible, but notable ambiguity remains in profile evidence."
    else:
        band = "high"
        rationale = "Job, persona, and delivery form are all supported by traceable evidence."
    return {
        "score_type": "need_clarity_score",
        "raw_value": None,
        "normalized_value": None,
        "band": band,
        "rationale": rationale,
        "evidence_refs_json": evidence_refs[: max(1, min(len(evidence_refs), 3))],
    }


def _attention_component(
    evidence_refs: list[dict[str, Any]],
    observation: dict[str, Any],
    source_item: dict[str, Any],
    benchmark_observations: list[dict[str, Any]],
    source_metric_registry: dict[str, Any],
) -> dict[str, Any]:
    definition = next((item for item in source_metric_registry["definitions"] if item["source_id"] == source_item["source_id"]), None)
    if definition is None:
        return _null_attention_component(evidence_refs, None, "metric_definition_unavailable")

    metric_name = definition["primary_metric"]
    metrics_snapshot = observation.get("metrics_snapshot") or source_item.get("current_metrics_json") or {}
    raw_value = metrics_snapshot.get(metric_name)
    if raw_value is None:
        return _null_attention_component(evidence_refs, None, "source_metrics_unavailable")

    relation_type = observation["relation_type"]
    comparable_values = [
        benchmark["metrics_snapshot"].get(metric_name)
        for benchmark in benchmark_observations
        if benchmark.get("source_id") == source_item["source_id"]
        and benchmark.get("relation_type") == relation_type
        and isinstance(benchmark.get("metrics_snapshot"), dict)
        and benchmark["metrics_snapshot"].get(metric_name) is not None
    ]
    min_sample_size = source_metric_registry["attention_v1_policy"]["frozen_parameters"]["min_sample_size"]
    if len(comparable_values) < min_sample_size:
        return _null_attention_component(evidence_refs, raw_value, "benchmark_sample_insufficient")

    percentile = _mid_rank_percentile(raw_value, comparable_values)
    thresholds = source_metric_registry["attention_v1_policy"]["frozen_parameters"]["band_thresholds"]
    if percentile >= thresholds["high_gte"]:
        band = "high"
    elif percentile >= thresholds["medium_gte"]:
        band = "medium"
    else:
        band = "low"

    return {
        "score_type": "attention_score",
        "raw_value": raw_value,
        "normalized_value": round(percentile, 4),
        "band": band,
        "rationale": f"Attention metric {metric_name} was benchmarked within the same source and relation_type cohort.",
        "evidence_refs_json": evidence_refs[:1] if evidence_refs else [_observation_ref(observation)],
    }


def _commercial_component(
    evidence_refs: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    product: dict[str, Any],
) -> dict[str, Any]:
    pricing = any(item["evidence_type"] == "pricing_page" for item in evidence)
    paid = any(item["evidence_type"] == "paid_plan_claim" for item in evidence)
    if not product.get("canonical_homepage_url"):
        band = None
        rationale = "homepage_unavailable"
    elif pricing and paid:
        band = "high"
        rationale = "Pricing page and paid-plan evidence are both traceable."
    elif pricing or paid:
        band = "medium"
        rationale = "Commercialization hints exist, but evidence is incomplete."
    else:
        band = None
        rationale = "pricing_evidence_unavailable"
    return {
        "score_type": "commercial_score",
        "raw_value": None,
        "normalized_value": None,
        "band": band,
        "rationale": rationale,
        "evidence_refs_json": evidence_refs[: max(1, min(len(evidence_refs), 2))],
    }


def _persistence_component(evidence_refs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "score_type": "persistence_score",
        "raw_value": None,
        "normalized_value": None,
        "band": None,
        "rationale": "not_enabled_in_phase1",
        "evidence_refs_json": evidence_refs,
    }


def _null_attention_component(evidence_refs: list[dict[str, Any]], raw_value: Any, reason: str) -> dict[str, Any]:
    return {
        "score_type": "attention_score",
        "raw_value": raw_value,
        "normalized_value": None,
        "band": None,
        "rationale": reason,
        "evidence_refs_json": evidence_refs[:1] if evidence_refs else [{"observation_id": "observation_unavailable"}],
    }


def _mid_rank_percentile(raw_value: float, comparable_values: list[float]) -> float:
    lower = sum(1 for value in comparable_values if value < raw_value)
    equal = sum(1 for value in comparable_values if value == raw_value)
    return (lower + (equal * 0.5)) / len(comparable_values)


def _evidence_ref(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": evidence["source_item_id"],
        "evidence_type": evidence["evidence_type"],
        "source_url": evidence["source_url"],
    }


def _observation_ref(observation: dict[str, Any]) -> dict[str, Any]:
    return {"observation_id": observation["observation_id"]}
