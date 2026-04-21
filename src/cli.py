"""Command-line entrypoints for the minimal runnable baseline."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from src.candidate_prescreen.config import load_candidate_prescreen_config
from src.candidate_prescreen.audit import default_phase1_g_audit_report_path, write_phase1_g_audit_ready_report
from src.candidate_prescreen.fill_controller import fill_gold_set_staging_until_complete
from src.candidate_prescreen.prompt_contract import candidate_prescreener_prompt_contract
from src.candidate_prescreen.relay import relay_preflight
from src.candidate_prescreen.relay import screen_candidate as relay_screen_candidate
from src.candidate_prescreen.staging import dedupe_staging_semantic_duplicates
from src.candidate_prescreen.workflow import (
    archive_duplicate_candidate_records as workflow_archive_duplicate_candidate_records,
    archive_future_window_candidate_records as workflow_archive_future_window_candidate_records,
    handoff_candidates_to_staging as workflow_handoff_candidates_to_staging,
    run_candidate_prescreen,
    validate_candidate_workspace as workflow_validate_candidate_workspace,
)
from src.common.config import AppConfig, resolve_required_settings, summarize_resolved_settings
from src.common.errors import BlockedReplayError, ConfigError, ContractValidationError, ObservatoryError
from src.common.files import dump_json, load_json, load_yaml
from src.common.logging_utils import configure_logging, get_logger
from src.common.schema import validate_schema_document
from src.devtools.quality import format_python, lint_python, typecheck_python
from src.marts.presentation import build_dashboard_view, build_product_drill_down, reconcile_dashboard_view
from src.runtime.migrations import migration_plan
from src.runtime.processing_errors import default_processing_error_store_path
from src.runtime.replay import build_default_mart, build_mart_window, replay_source_window
from src.review.runtime import (
    list_review_queue,
    resolve_taxonomy_review_from_record_path,
    trigger_entity_review_from_source_item,
    trigger_score_review_from_snapshot,
    trigger_taxonomy_review_from_source_item,
)
from src.review.store import default_review_issue_store_path


def _require_mapping(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{description} must be a mapping")
    return value


def _require_list(value: object, description: str) -> list[object]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{description} must be a list")
    return value


def _require_string(value: object, description: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{description} must be a non-empty string")
    return value


def _require_bool(value: object, description: str) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError(f"{description} must be a boolean")
    return value


def _require_non_empty_ref_list(value: object, description: str) -> list[dict[str, object]]:
    refs = _require_list(value, description)
    if not refs:
        raise ContractValidationError(f"{description} must contain at least one reference")
    normalized: list[dict[str, object]] = []
    for index, entry in enumerate(refs):
        ref = _require_mapping(entry, f"{description}[{index}]")
        if not any(isinstance(candidate, str) and candidate for candidate in ref.values()):
            raise ContractValidationError(f"{description}[{index}] must retain at least one non-empty trace field")
        normalized.append(ref)
    return normalized


def _load_config_mapping(config_dir: Path, file_name: str) -> dict[str, object]:
    return _require_mapping(load_yaml(config_dir / file_name), file_name)


def _load_schema_mapping(schema_dir: Path, file_name: str) -> dict[str, object]:
    return _require_mapping(load_json(schema_dir / file_name), file_name)


def _validate_source_registry_config(config_dir: Path) -> int:
    source_registry = _load_config_mapping(config_dir, "source_registry.yaml")
    sources = _require_list(source_registry.get("sources"), "source_registry.yaml:sources")
    source_ids = [_require_string(_require_mapping(entry, "source_registry.yaml:sources[]").get("source_id"), "source_id") for entry in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ContractValidationError("source_registry.yaml contains duplicate source_id values")
    if not all(isinstance(_require_mapping(entry, "source_registry.yaml:sources[]").get("enabled"), bool) for entry in sources):
        raise ContractValidationError("Every source_registry entry must define a boolean enabled field")
    return len(sources)


def _validate_taxonomy_config(config_dir: Path) -> None:
    taxonomy = _load_config_mapping(config_dir, "taxonomy_v0.yaml")
    if taxonomy.get("version") != "v0":
        raise ContractValidationError("taxonomy_v0.yaml must define version = v0")
    if taxonomy.get("implementation_ready") is not True:
        raise ContractValidationError("taxonomy_v0.yaml must declare implementation_ready = true")

    assignment_policy = _require_mapping(taxonomy.get("assignment_policy"), "taxonomy_v0.yaml:assignment_policy")
    if assignment_policy.get("unresolved_code") != "unresolved":
        raise ContractValidationError("taxonomy_v0.yaml must keep unresolved_code = unresolved")
    if assignment_policy.get("secondary_allowed_only_after_stable_primary") is not True:
        raise ContractValidationError("taxonomy_v0.yaml must require stable primary before secondary assignment")
    if assignment_policy.get("l2_can_be_empty_when_only_l1_stable") is not True:
        raise ContractValidationError("taxonomy_v0.yaml must explicitly allow empty L2 when only L1 is stable")
    if assignment_policy.get("stable_l2_examples_are_non_exhaustive") is not True:
        raise ContractValidationError("taxonomy_v0.yaml must declare stable_l2_examples as non-exhaustive")
    cap = assignment_policy.get("stable_l2_cap_per_l1")
    if not isinstance(cap, int) or cap <= 0:
        raise ContractValidationError("taxonomy_v0.yaml stable_l2_cap_per_l1 must be a positive integer")
    unresolved_exit_conditions = set(
        _require_list(assignment_policy.get("unresolved_exit_conditions"), "taxonomy_v0.yaml:assignment_policy:unresolved_exit_conditions")
    )
    if unresolved_exit_conditions != {
        "stable_unique_primary_l1",
        "adjacent_confusion_explainable",
        "traceable_evidence_and_merge_resolved",
    }:
        raise ContractValidationError("taxonomy_v0.yaml unresolved_exit_conditions drifted from the frozen taxonomy policy")
    long_term_l1_only_codes = {
        _require_string(code, "taxonomy_v0.yaml:assignment_policy:long_term_l1_only_codes[]")
        for code in _require_list(assignment_policy.get("long_term_l1_only_codes"), "taxonomy_v0.yaml:assignment_policy:long_term_l1_only_codes")
    }
    if long_term_l1_only_codes != {"JTBD_OTHER_VERTICAL"}:
        raise ContractValidationError("taxonomy_v0.yaml long_term_l1_only_codes drifted from the frozen Phase1 allowlist")

    required_adjacent_pairs = {
        tuple(sorted(("JTBD_CONTENT", "JTBD_KNOWLEDGE"))),
        tuple(sorted(("JTBD_KNOWLEDGE", "JTBD_PRODUCTIVITY_AUTOMATION"))),
        tuple(sorted(("JTBD_DEV_TOOLS", "JTBD_PRODUCTIVITY_AUTOMATION"))),
        tuple(sorted(("JTBD_MARKETING_GROWTH", "JTBD_CONTENT"))),
        tuple(sorted(("JTBD_SALES_SUPPORT", "JTBD_KNOWLEDGE"))),
    }
    adjacent_confusion_rules = _require_list(taxonomy.get("adjacent_confusion_rules"), "taxonomy_v0.yaml:adjacent_confusion_rules")
    seen_adjacent_pairs: set[tuple[str, str]] = set()
    for entry in adjacent_confusion_rules:
        rule = _require_mapping(entry, "taxonomy_v0.yaml:adjacent_confusion_rules[]")
        raw_pair = _require_list(rule.get("pair"), "taxonomy_v0.yaml:adjacent_confusion_rules[].pair")
        if len(raw_pair) != 2:
            raise ContractValidationError("taxonomy_v0.yaml adjacent confusion rules must define exactly two codes per pair")
        pair = [_require_string(code, "taxonomy_v0.yaml:adjacent_confusion_rules[].pair[]") for code in raw_pair]
        normalized_pair = tuple(sorted(pair))
        if normalized_pair in seen_adjacent_pairs:
            raise ContractValidationError(f"taxonomy_v0.yaml contains duplicate adjacent confusion pair: {normalized_pair}")
        seen_adjacent_pairs.add(normalized_pair)

        decide_when = _require_mapping(rule.get("decide_when"), "taxonomy_v0.yaml:adjacent_confusion_rules[].decide_when")
        if set(decide_when) != set(pair):
            raise ContractValidationError(f"taxonomy_v0.yaml adjacent confusion pair {normalized_pair} must define decide_when entries for both codes")
        for code in pair:
            decision = _require_mapping(decide_when.get(code), f"taxonomy_v0.yaml:{code}:decide_when")
            inclusion_signals = _require_list(decision.get("inclusion_signals"), f"taxonomy_v0.yaml:{code}:inclusion_signals")
            exclusion_signals = _require_list(decision.get("exclusion_signals"), f"taxonomy_v0.yaml:{code}:exclusion_signals")
            if not inclusion_signals or not exclusion_signals:
                raise ContractValidationError(f"taxonomy_v0.yaml adjacent confusion rule for {code} must define inclusion and exclusion signals")
            for signal in inclusion_signals:
                _require_string(signal, f"taxonomy_v0.yaml:{code}:inclusion_signals[]")
            for signal in exclusion_signals:
                _require_string(signal, f"taxonomy_v0.yaml:{code}:exclusion_signals[]")
            _require_string(decision.get("example_positive"), f"taxonomy_v0.yaml:{code}:example_positive")
        _require_string(rule.get("example_negative"), f"taxonomy_v0.yaml:{normalized_pair}:example_negative")
        _require_string(
            rule.get("route_to_review_or_unresolved_when"),
            f"taxonomy_v0.yaml:{normalized_pair}:route_to_review_or_unresolved_when",
        )
    if seen_adjacent_pairs != required_adjacent_pairs:
        raise ContractValidationError("taxonomy_v0.yaml adjacent confusion pair set does not match the frozen Phase1 taxonomy boundaries")

    nodes = _require_list(taxonomy.get("nodes"), "taxonomy_v0.yaml:nodes")
    required_codes = {
        "JTBD_CONTENT",
        "JTBD_KNOWLEDGE",
        "JTBD_PRODUCTIVITY_AUTOMATION",
        "JTBD_DEV_TOOLS",
        "JTBD_DATA_ANALYTICS",
        "JTBD_MARKETING_GROWTH",
        "JTBD_SALES_SUPPORT",
        "JTBD_DESIGN_PRESENTATION",
        "JTBD_PERSONAL_CREATIVE",
        "JTBD_OTHER_VERTICAL",
    }
    seen_codes: set[str] = set()
    seen_stable_l2_codes: set[str] = set()
    for entry in nodes:
        node = _require_mapping(entry, "taxonomy_v0.yaml:nodes[]")
        code = _require_string(node.get("code"), "taxonomy node code")
        if code in seen_codes:
            raise ContractValidationError(f"taxonomy_v0.yaml contains duplicate node code: {code}")
        seen_codes.add(code)
        for field_name in (
            "label",
            "zh_label",
            "definition",
            "inclusion_rule",
            "exclusion_rule",
            "example_positive",
            "example_negative",
            "adjacent_confusions",
            "stable_l2_examples",
        ):
            if field_name not in node:
                raise ContractValidationError(f"taxonomy_v0.yaml node {code} is missing {field_name}")
        stable_l2_examples = _require_list(node.get("stable_l2_examples"), f"taxonomy_v0.yaml:{code}:stable_l2_examples")
        if len(stable_l2_examples) > cap:
            raise ContractValidationError(f"taxonomy_v0.yaml node {code} exceeds stable L2 cap {cap}")
        for l2_entry in stable_l2_examples:
            l2 = _require_mapping(l2_entry, f"taxonomy_v0.yaml:{code}:stable_l2_examples[]")
            l2_code = _require_string(l2.get("code"), f"taxonomy_v0.yaml:{code}:stable_l2_examples[].code")
            _require_string(l2.get("label"), f"taxonomy_v0.yaml:{code}:stable_l2_examples[].label")
            _require_string(l2.get("zh_label"), f"taxonomy_v0.yaml:{code}:stable_l2_examples[].zh_label")
            if l2_code in seen_stable_l2_codes:
                raise ContractValidationError(f"taxonomy_v0.yaml contains duplicate stable L2 code: {l2_code}")
            seen_stable_l2_codes.add(l2_code)
    if seen_codes != required_codes:
        raise ContractValidationError("taxonomy_v0.yaml L1 code set does not match the frozen Phase1 taxonomy set")
    if not long_term_l1_only_codes.issubset(seen_codes):
        raise ContractValidationError("taxonomy_v0.yaml long_term_l1_only_codes must be a subset of the frozen L1 code set")


def _validate_vocab_configs(config_dir: Path) -> None:
    delivery_form = _load_config_mapping(config_dir, "delivery_form_v0.yaml")
    delivery_codes = set(_require_list(delivery_form.get("codes"), "delivery_form_v0.yaml:codes"))
    for required_code in {"web_app", "mobile_app", "desktop_app", "unknown"}:
        if required_code not in delivery_codes:
            raise ContractValidationError(f"delivery_form_v0.yaml is missing required code: {required_code}")

    persona = _load_config_mapping(config_dir, "persona_v0.yaml")
    persona_codes = set(_require_list(persona.get("codes"), "persona_v0.yaml:codes"))
    if "unknown" not in persona_codes:
        raise ContractValidationError("persona_v0.yaml must include unknown")
    if "personal_creator" in persona_codes:
        raise ContractValidationError("persona_v0.yaml must not add personal_creator in v0")


def _validate_rubric_config(config_dir: Path) -> None:
    rubric = _load_config_mapping(config_dir, "rubric_v0.yaml")
    if rubric.get("version") != "v0":
        raise ContractValidationError("rubric_v0.yaml must define version = v0")
    if rubric.get("implementation_ready") is not True:
        raise ContractValidationError("rubric_v0.yaml must declare implementation_ready = true")

    if _require_list(rubric.get("band_scale"), "rubric_v0.yaml:band_scale") != ["high", "medium", "low"]:
        raise ContractValidationError("rubric_v0.yaml band_scale must be [high, medium, low]")

    required_output_fields = _require_list(rubric.get("required_output_fields"), "rubric_v0.yaml:required_output_fields")
    if required_output_fields != [
        "score_type",
        "raw_value",
        "normalized_value",
        "band",
        "rationale",
        "evidence_refs_json",
    ]:
        raise ContractValidationError("rubric_v0.yaml required_output_fields drifted from the score_component contract")

    score_entries = _require_list(rubric.get("scores"), "rubric_v0.yaml:scores")
    scores: dict[str, dict[str, object]] = {}
    for entry in score_entries:
        score = _require_mapping(entry, "rubric_v0.yaml:scores[]")
        score_type = _require_string(score.get("score_type"), "rubric score_type")
        if score_type in scores:
            raise ContractValidationError(f"rubric_v0.yaml contains duplicate score_type: {score_type}")
        scores[score_type] = score

    if set(scores) != {
        "build_evidence_score",
        "need_clarity_score",
        "attention_score",
        "commercial_score",
        "persistence_score",
    }:
        raise ContractValidationError("rubric_v0.yaml score_type set does not match the frozen Phase1 rubric")

    for required_band_score in ("build_evidence_score", "need_clarity_score"):
        score = scores[required_band_score]
        if score.get("phase1_status") != "required" or score.get("null_policy") != "not_allowed":
            raise ContractValidationError(f"{required_band_score} must stay required with null_policy = not_allowed")
        if score.get("override_allowed") is not True:
            raise ContractValidationError(f"{required_band_score} must allow override")

    attention = scores["attention_score"]
    registry = _load_config_mapping(config_dir, "source_metric_registry.yaml")
    attention_policy = _require_mapping(registry.get("attention_v1_policy"), "source_metric_registry.yaml:attention_v1_policy")
    frozen_parameters = _require_mapping(attention_policy.get("frozen_parameters"), "source_metric_registry.yaml:frozen_parameters")
    band_thresholds = _require_mapping(frozen_parameters.get("band_thresholds"), "source_metric_registry.yaml:band_thresholds")
    benchmark_windows = _require_mapping(attention.get("benchmark_windows"), "rubric_v0.yaml:attention_score:benchmark_windows")
    rubric_thresholds = _require_mapping(attention.get("band_thresholds"), "rubric_v0.yaml:attention_score:band_thresholds")

    if benchmark_windows.get("primary_window_days") != frozen_parameters.get("primary_window_days"):
        raise ContractValidationError("attention primary_window_days drifted between rubric_v0.yaml and source_metric_registry.yaml")
    if benchmark_windows.get("fallback_window_days") != frozen_parameters.get("fallback_window_days"):
        raise ContractValidationError("attention fallback_window_days drifted between rubric_v0.yaml and source_metric_registry.yaml")
    if attention.get("min_sample_size") != frozen_parameters.get("min_sample_size"):
        raise ContractValidationError("attention min_sample_size drifted between rubric_v0.yaml and source_metric_registry.yaml")
    if rubric_thresholds != band_thresholds:
        raise ContractValidationError("attention band_thresholds drifted between rubric_v0.yaml and source_metric_registry.yaml")
    if set(_require_list(attention.get("null_reasons"), "rubric_v0.yaml:attention_score:null_reasons")) != {
        "source_metrics_unavailable",
        "metric_definition_unavailable",
        "metric_semantics_mismatch",
        "window_benchmark_unavailable",
        "benchmark_sample_insufficient",
    }:
        raise ContractValidationError("attention null_reasons must stay aligned with the frozen rule set")

    commercial = scores["commercial_score"]
    if commercial.get("phase1_status") != "optional":
        raise ContractValidationError("commercial_score must remain optional in phase1")

    persistence = scores["persistence_score"]
    if persistence.get("phase1_status") != "reserved" or persistence.get("override_allowed") is not False:
        raise ContractValidationError("persistence_score must remain reserved with override disabled")


def _validate_review_rules_config(config_dir: Path) -> None:
    review_rules = _load_config_mapping(config_dir, "review_rules_v0.yaml")
    if _require_list(review_rules.get("priority_system"), "review_rules_v0.yaml:priority_system") != ["P0", "P1", "P2", "P3"]:
        raise ContractValidationError("review_rules_v0.yaml priority_system must stay on P0/P1/P2/P3")
    if _require_list(review_rules.get("issue_types"), "review_rules_v0.yaml:issue_types") != [
        "entity_merge_uncertainty",
        "taxonomy_low_confidence",
        "taxonomy_conflict",
        "score_conflict",
        "suspicious_result",
    ]:
        raise ContractValidationError("review_rules_v0.yaml issue_types drifted from the frozen review policy")
    if _require_list(review_rules.get("resolution_actions"), "review_rules_v0.yaml:resolution_actions") != [
        "confirm_auto_result",
        "override_auto_result",
        "mark_unresolved",
        "reject_issue",
        "needs_more_evidence",
    ]:
        raise ContractValidationError("review_rules_v0.yaml resolution_actions drifted from the frozen review policy")
    if _require_list(review_rules.get("maker_checker_required_for"), "review_rules_v0.yaml:maker_checker_required_for") != [
        "P0 taxonomy override",
        "P0 score override",
        "P0 entity merge or split",
    ]:
        raise ContractValidationError("review_rules_v0.yaml maker_checker_required_for drifted from the frozen review policy")

    maker_checker_writeback = _require_mapping(
        review_rules.get("maker_checker_writeback"),
        "review_rules_v0.yaml:maker_checker_writeback",
    )
    if _require_list(
        maker_checker_writeback.get("required_fields"),
        "review_rules_v0.yaml:maker_checker_writeback:required_fields",
    ) != [
        "reviewer",
        "reviewed_at",
        "resolution_action",
        "resolution_notes",
        "approver",
        "approved_at",
        "review_issue_id",
    ]:
        raise ContractValidationError("review_rules_v0.yaml maker_checker_writeback.required_fields drifted from the frozen writeback contract")
    if (
        _require_bool(
            maker_checker_writeback.get("approved_writeback_required_for_high_impact_override"),
            "review_rules_v0.yaml:maker_checker_writeback:approved_writeback_required_for_high_impact_override",
        )
        is not True
    ):
        raise ContractValidationError("high-impact override writeback must require approval before becoming effective")
    if maker_checker_writeback.get("effective_result_writeback_mode") != "new_version_only":
        raise ContractValidationError("review_rules_v0.yaml maker_checker_writeback.effective_result_writeback_mode must stay new_version_only")

    unresolved_handling = _require_mapping(review_rules.get("unresolved_handling"), "review_rules_v0.yaml:unresolved_handling")
    if _require_list(
        unresolved_handling.get("unresolved_modes"),
        "review_rules_v0.yaml:unresolved_handling:unresolved_modes",
    ) != [
        "writeback_unresolved",
        "review_only_unresolved",
    ]:
        raise ContractValidationError("review_rules_v0.yaml unresolved_modes drifted from the frozen unresolved handling policy")

    sample_pool_rules = _require_mapping(review_rules.get("sample_pool_rules"), "review_rules_v0.yaml:sample_pool_rules")
    candidate_pool = _require_mapping(sample_pool_rules.get("candidate_pool"), "review_rules_v0.yaml:candidate_pool")
    if candidate_pool.get("per_batch_top_limit") != 10:
        raise ContractValidationError("candidate_pool.per_batch_top_limit must remain 10")
    if "unresolved" not in _require_list(candidate_pool.get("exclude_effective_category_codes"), "review_rules_v0.yaml:candidate_pool:exclude_effective_category_codes"):
        raise ContractValidationError("candidate_pool must exclude unresolved")
    if _require_list(candidate_pool.get("ordering"), "review_rules_v0.yaml:candidate_pool:ordering") != [
        "need_clarity_band_high_first",
        "build_evidence_band_high_second",
        "attention_score_secondary_only",
    ]:
        raise ContractValidationError("candidate_pool ordering drifted from the frozen sample-pool layering rule")

    training_pool = _require_mapping(sample_pool_rules.get("training_pool"), "review_rules_v0.yaml:training_pool")
    if training_pool.get("source") != "candidate_pool":
        raise ContractValidationError("training_pool must only source from candidate_pool")
    if (
        _require_bool(training_pool.get("require_review_closure"), "review_rules_v0.yaml:training_pool:require_review_closure") is not True
        or _require_bool(
            training_pool.get("require_sufficient_evidence"),
            "review_rules_v0.yaml:training_pool:require_sufficient_evidence",
        )
        is not True
        or _require_bool(
            training_pool.get("require_clear_adjudication"),
            "review_rules_v0.yaml:training_pool:require_clear_adjudication",
        )
        is not True
    ):
        raise ContractValidationError("training_pool must keep the frozen review/evidence/adjudication gates")

    gold_set = _require_mapping(sample_pool_rules.get("gold_set"), "review_rules_v0.yaml:gold_set")
    if gold_set.get("pool_name") != "gold_set_300":
        raise ContractValidationError("gold_set.pool_name must stay gold_set_300")
    if (
        _require_bool(gold_set.get("require_double_annotation"), "review_rules_v0.yaml:gold_set:require_double_annotation") is not True
        or _require_bool(gold_set.get("require_adjudication"), "review_rules_v0.yaml:gold_set:require_adjudication") is not True
    ):
        raise ContractValidationError("gold_set must keep double-annotation plus adjudication")

    annotation_contract = _require_mapping(review_rules.get("annotation_contract"), "review_rules_v0.yaml:annotation_contract")
    if annotation_contract.get("target_type") != "product":
        raise ContractValidationError("annotation_contract.target_type must stay product")
    if _require_list(
        annotation_contract.get("decision_form_required_fields"),
        "review_rules_v0.yaml:annotation_contract:decision_form_required_fields",
    ) != [
        "sample_id",
        "target_type",
        "target_id",
        "primary_category_code",
        "secondary_category_code",
        "primary_persona_code",
        "delivery_form_code",
        "build_evidence_band",
        "need_clarity_band",
        "rationale",
        "evidence_refs",
        "adjudication_status",
    ]:
        raise ContractValidationError("annotation decision-form required fields drifted from the frozen annotation guideline")
    if _require_list(
        annotation_contract.get("decision_form_optional_fields"),
        "review_rules_v0.yaml:annotation_contract:decision_form_optional_fields",
    ) != [
        "review_recommended",
        "review_reason",
        "taxonomy_change_suggestion",
    ]:
        raise ContractValidationError("annotation decision-form optional fields drifted from the frozen annotation guideline")
    if set(_require_list(annotation_contract.get("adjudication_statuses"), "review_rules_v0.yaml:annotation_contract:adjudication_statuses")) != {
        "single_annotated",
        "double_annotated",
        "adjudicated",
        "needs_review",
    }:
        raise ContractValidationError("annotation adjudication statuses drifted from the frozen annotation workflow")
    if _require_list(
        annotation_contract.get("default_double_annotation_channels"),
        "review_rules_v0.yaml:annotation_contract:default_double_annotation_channels",
    ) != ["local_project_user", "llm"]:
        raise ContractValidationError("annotation default_double_annotation_channels drifted from the frozen gold-set default")
    if annotation_contract.get("default_adjudicator_role") != "local_project_user":
        raise ContractValidationError("annotation default_adjudicator_role must stay local_project_user")
    if (
        _require_bool(
            annotation_contract.get("gold_set_finalization_requires_adjudicator_confirmation"),
            "review_rules_v0.yaml:annotation_contract:gold_set_finalization_requires_adjudicator_confirmation",
        )
        is not True
    ):
        raise ContractValidationError("gold_set finalization must require adjudicator confirmation")
    field_mappings = _require_mapping(annotation_contract.get("field_mappings"), "review_rules_v0.yaml:annotation_contract:field_mappings")
    if _require_mapping(field_mappings.get("build_evidence_band"), "build_evidence_band").get("score_type") != "build_evidence_score":
        raise ContractValidationError("build_evidence_band must map to build_evidence_score")
    if _require_mapping(field_mappings.get("need_clarity_band"), "need_clarity_band").get("score_type") != "need_clarity_score":
        raise ContractValidationError("need_clarity_band must map to need_clarity_score")
    if _require_list(
        annotation_contract.get("review_recommended_when"),
        "review_rules_v0.yaml:annotation_contract:review_recommended_when",
    ) != [
        "evidence_conflict",
        "primary_job_not_unique",
        "unstable_product_merge",
        "unresolved_assignment",
        "taxonomy_boundary_not_explainable",
    ]:
        raise ContractValidationError("annotation review_recommended_when drifted from the frozen annotation guideline")
    terminology_alignment = _require_mapping(
        annotation_contract.get("terminology_alignment"),
        "review_rules_v0.yaml:annotation_contract:terminology_alignment",
    )
    if terminology_alignment != {
        "needs_review": "annotation_workflow_signal_only",
        "needs_more_evidence": "review_resolution_without_stable_writeback",
        "mark_unresolved": "review_resolution_for_effective_unresolved",
        "override_auto_result": "review_resolution_for_new_effective_result",
    }:
        raise ContractValidationError("annotation terminology_alignment drifted from the frozen annotation/review boundary")
    taxonomy_change_suggestion = _require_mapping(
        annotation_contract.get("taxonomy_change_suggestion"),
        "review_rules_v0.yaml:annotation_contract:taxonomy_change_suggestion",
    )
    if (
        _require_bool(
            taxonomy_change_suggestion.get("record_only_until_adjudicator_confirmation"),
            "review_rules_v0.yaml:annotation_contract:taxonomy_change_suggestion:record_only_until_adjudicator_confirmation",
        )
        is not True
    ):
        raise ContractValidationError("taxonomy_change_suggestion must remain record-only until adjudicator confirmation")
    if (
        _require_bool(
            taxonomy_change_suggestion.get("auto_writeback_allowed"),
            "review_rules_v0.yaml:annotation_contract:taxonomy_change_suggestion:auto_writeback_allowed",
        )
        is not False
    ):
        raise ContractValidationError("taxonomy_change_suggestion must not become an automatic taxonomy writeback path")


def _validate_schema_alignment(config_dir: Path, schema_dir: Path) -> None:
    rubric = _load_config_mapping(config_dir, "rubric_v0.yaml")
    review_rules = _load_config_mapping(config_dir, "review_rules_v0.yaml")

    taxonomy_schema = _load_schema_mapping(schema_dir, "taxonomy_assignment.schema.json")
    taxonomy_required = _require_list(taxonomy_schema.get("required"), "taxonomy_assignment.schema.json:required")
    if taxonomy_required != [
        "target_type",
        "target_id",
        "taxonomy_version",
        "label_level",
        "label_role",
        "category_code",
        "rationale",
        "assigned_by",
        "model_or_rule_version",
        "assigned_at",
        "evidence_refs_json",
    ]:
        raise ContractValidationError("taxonomy_assignment.schema.json required fields drifted from the frozen taxonomy contract")
    taxonomy_properties = _require_mapping(taxonomy_schema.get("properties"), "taxonomy_assignment.schema.json:properties")
    if _require_list(_require_mapping(taxonomy_properties.get("target_type"), "taxonomy_assignment.schema.json:target_type").get("enum"), "taxonomy_assignment.schema.json:target_type:enum") != ["product"]:
        raise ContractValidationError("taxonomy_assignment.schema.json target_type must stay product-only in phase1")
    if _require_list(_require_mapping(taxonomy_properties.get("label_level"), "taxonomy_assignment.schema.json:label_level").get("enum"), "taxonomy_assignment.schema.json:label_level:enum") != [1, 2]:
        raise ContractValidationError("taxonomy_assignment.schema.json label_level must stay limited to L1/L2")
    if _require_list(_require_mapping(taxonomy_properties.get("label_role"), "taxonomy_assignment.schema.json:label_role").get("enum"), "taxonomy_assignment.schema.json:label_role:enum") != ["primary", "secondary"]:
        raise ContractValidationError("taxonomy_assignment.schema.json label_role drifted from the frozen taxonomy policy")
    if _require_list(_require_mapping(taxonomy_properties.get("result_status"), "taxonomy_assignment.schema.json:result_status").get("enum"), "taxonomy_assignment.schema.json:result_status:enum") != [
        "active",
        "superseded",
        "dismissed",
        None,
    ]:
        raise ContractValidationError("taxonomy_assignment.schema.json result_status drifted from the frozen lifecycle contract")
    if _require_mapping(taxonomy_properties.get("evidence_refs_json"), "taxonomy_assignment.schema.json:evidence_refs_json").get("minItems") != 1:
        raise ContractValidationError("taxonomy_assignment.schema.json evidence_refs_json must require at least one traceable reference")

    score_schema = _load_schema_mapping(schema_dir, "score_component.schema.json")
    score_required = _require_list(score_schema.get("required"), "score_component.schema.json:required")
    required_output_fields = _require_list(rubric.get("required_output_fields"), "rubric_v0.yaml:required_output_fields")
    if score_required != required_output_fields:
        raise ContractValidationError("score_component.schema.json required fields drifted from rubric_v0.yaml required_output_fields")
    score_properties = _require_mapping(score_schema.get("properties"), "score_component.schema.json:properties")
    score_type_enum = set(
        _require_list(_require_mapping(score_properties.get("score_type"), "score_component.schema.json:score_type").get("enum"), "score_component.schema.json:score_type:enum")
    )
    rubric_score_types = {
        _require_string(_require_mapping(entry, "rubric_v0.yaml:scores[]").get("score_type"), "rubric_v0.yaml:scores[].score_type")
        for entry in _require_list(rubric.get("scores"), "rubric_v0.yaml:scores")
    }
    if score_type_enum != rubric_score_types:
        raise ContractValidationError("score_component.schema.json score_type enum drifted from rubric_v0.yaml")
    if _require_list(_require_mapping(score_properties.get("band"), "score_component.schema.json:band").get("enum"), "score_component.schema.json:band:enum") != [
        "high",
        "medium",
        "low",
        None,
    ]:
        raise ContractValidationError("score_component.schema.json band enum must stay aligned with the frozen rubric band scale")
    if _require_mapping(score_properties.get("evidence_refs_json"), "score_component.schema.json:evidence_refs_json").get("minItems") != 1:
        raise ContractValidationError("score_component.schema.json evidence_refs_json must require at least one traceable reference")
    score_all_of = _require_list(score_schema.get("allOf"), "score_component.schema.json:allOf")
    required_non_null_band_scores = {"build_evidence_score", "need_clarity_score"}
    guarded_scores: set[str] = set()
    for entry in score_all_of:
        branch = _require_mapping(entry, "score_component.schema.json:allOf[]")
        conditional = _require_mapping(branch.get("if"), "score_component.schema.json:allOf[].if")
        conditional_properties = _require_mapping(conditional.get("properties"), "score_component.schema.json:allOf[].if.properties")
        score_type = _require_mapping(conditional_properties.get("score_type"), "score_component.schema.json:allOf[].if.properties.score_type").get("const")
        if score_type not in required_non_null_band_scores:
            continue
        then_branch = _require_mapping(branch.get("then"), "score_component.schema.json:allOf[].then")
        then_properties = _require_mapping(then_branch.get("properties"), "score_component.schema.json:allOf[].then.properties")
        if _require_list(_require_mapping(then_properties.get("band"), "score_component.schema.json:allOf[].then.properties.band").get("enum"), "score_component.schema.json:allOf[].then.properties.band:enum") != [
            "high",
            "medium",
            "low",
        ]:
            raise ContractValidationError(f"score_component.schema.json must keep non-null band enforcement for {score_type}")
        guarded_scores.add(score_type)
    if guarded_scores != required_non_null_band_scores:
        raise ContractValidationError("score_component.schema.json must keep non-null band enforcement for build_evidence_score and need_clarity_score")

    review_packet_schema = _load_schema_mapping(schema_dir, "review_packet.schema.json")
    review_packet_required = _require_list(review_packet_schema.get("required"), "review_packet.schema.json:required")
    if review_packet_required != [
        "target_summary",
        "issue_type",
        "current_auto_result",
        "related_evidence",
        "conflict_point",
        "recommended_action",
        "upstream_downstream_links",
    ]:
        raise ContractValidationError("review_packet.schema.json required fields drifted from the frozen review packet contract")
    review_packet_properties = _require_mapping(review_packet_schema.get("properties"), "review_packet.schema.json:properties")
    review_issue_types = _require_list(review_rules.get("issue_types"), "review_rules_v0.yaml:issue_types")
    if set(_require_list(_require_mapping(review_packet_properties.get("issue_type"), "review_packet.schema.json:issue_type").get("enum"), "review_packet.schema.json:issue_type:enum")) != set(review_issue_types):
        raise ContractValidationError("review_packet.schema.json issue_type enum drifted from review_rules_v0.yaml")
    if _require_mapping(review_packet_properties.get("related_evidence"), "review_packet.schema.json:related_evidence").get("minItems") != 1:
        raise ContractValidationError("review_packet.schema.json related_evidence must require at least one traceable evidence entry")
    if _require_mapping(review_packet_properties.get("upstream_downstream_links"), "review_packet.schema.json:upstream_downstream_links").get("minItems") != 1:
        raise ContractValidationError("review_packet.schema.json upstream_downstream_links must require at least one traceable linkage")


def _validate_candidate_prescreen_config(config_dir: Path, schema_dir: Path) -> None:
    workflow = load_candidate_prescreen_config(config_dir)
    if workflow.get("version") != "candidate_prescreen_v1":
        raise ContractValidationError("candidate_prescreen_workflow.yaml must define version = candidate_prescreen_v1")

    workspace = _require_mapping(workflow.get("workspace"), "candidate_prescreen_workflow.yaml:workspace")
    if workspace.get("directory") != "docs/candidate_prescreen_workspace":
        raise ContractValidationError("candidate_prescreen_workflow.yaml workspace.directory must stay docs/candidate_prescreen_workspace")
    if _require_bool(workspace.get("outside_formal_gold_set"), "candidate_prescreen_workflow.yaml:workspace:outside_formal_gold_set") is not True:
        raise ContractValidationError("candidate workspace must stay outside the formal gold_set directory")
    note_templates = _require_mapping(
        workspace.get("human_review_note_templates"),
        "candidate_prescreen_workflow.yaml:workspace:human_review_note_templates",
    )
    if note_templates != {
        "approved": "clear end-user product signal; evidence sufficient for staging",
        "hold": "boundary with internal tooling unclear",
        "rejected": "outside observatory scope",
    }:
        raise ContractValidationError("candidate human review note templates drifted from the frozen candidate prescreen workflow")
    allowed_statuses = _require_list(
        workspace.get("allowed_human_review_statuses"),
        "candidate_prescreen_workflow.yaml:workspace:allowed_human_review_statuses",
    )
    if allowed_statuses != [
        "pending_first_pass",
        "approved_for_staging",
        "rejected_after_human_review",
        "on_hold",
    ]:
        raise ContractValidationError("candidate human review statuses drifted from the frozen candidate prescreen workflow")
    if workspace.get("initial_human_review_status") != "pending_first_pass":
        raise ContractValidationError("candidate prescreen initial_human_review_status must stay pending_first_pass")
    if workspace.get("staging_write_requires_human_review_status") != "approved_for_staging":
        raise ContractValidationError("candidate prescreen staging handoff must require approved_for_staging")

    staging_defaults = _require_mapping(workflow.get("staging_defaults"), "candidate_prescreen_workflow.yaml:staging_defaults")
    if staging_defaults.get("directory") != "docs/gold_set_300_real_asset_staging":
        raise ContractValidationError("candidate prescreen staging directory must stay docs/gold_set_300_real_asset_staging")
    if staging_defaults.get("target_type") != "product":
        raise ContractValidationError("candidate prescreen staging target_type must stay product")
    if staging_defaults.get("training_pool_source") != "candidate_pool":
        raise ContractValidationError("candidate prescreen staging training_pool_source must stay candidate_pool")
    if _require_bool(staging_defaults.get("preserve_existing_stub_boundary"), "candidate_prescreen_workflow.yaml:staging_defaults:preserve_existing_stub_boundary") is not True:
        raise ContractValidationError("candidate prescreen staging handoff must preserve the existing stub boundary")

    llm_prescreen = _require_mapping(workflow.get("llm_prescreen"), "candidate_prescreen_workflow.yaml:llm_prescreen")
    if llm_prescreen.get("prompt_version") != "candidate_prescreener_v1":
        raise ContractValidationError("candidate prescreen prompt_version must stay candidate_prescreener_v1")
    if llm_prescreen.get("prompt_spec_ref") != "10_prompt_specs/candidate_prescreener_v1.md":
        raise ContractValidationError("candidate prescreen prompt_spec_ref must stay 10_prompt_specs/candidate_prescreener_v1.md")
    if llm_prescreen.get("routing_version") != "route_candidate_prescreener_v1":
        raise ContractValidationError("candidate prescreen routing_version must stay route_candidate_prescreener_v1")
    if llm_prescreen.get("relay_transport") != "http_json_relay":
        raise ContractValidationError("candidate prescreen relay_transport must stay http_json_relay")
    recommended_actions = _require_list(llm_prescreen.get("recommended_actions"), "candidate_prescreen_workflow.yaml:llm_prescreen:recommended_actions")
    if recommended_actions != ["reject", "hold", "candidate_pool", "whitelist_candidate"]:
        raise ContractValidationError("candidate prescreen recommended_actions drifted from the frozen workflow")
    unresolved_risk_levels = _require_list(
        llm_prescreen.get("unresolved_risk_levels"),
        "candidate_prescreen_workflow.yaml:llm_prescreen:unresolved_risk_levels",
    )
    if unresolved_risk_levels != ["low", "medium", "high"]:
        raise ContractValidationError("candidate prescreen unresolved_risk_levels must stay [low, medium, high]")

    execution_boundary = _require_mapping(workflow.get("execution_boundary"), "candidate_prescreen_workflow.yaml:execution_boundary")
    expected_execution_boundary = {
        "current_phase_default_live_source": "github",
        "product_hunt_current_phase_mode": "fixture_replay_contract_only",
        "product_hunt_live_discovery_status": "deferred",
        "product_hunt_future_live_path": "official_product_hunt_graphql_api_with_token_auth",
    }
    for field_name, expected_value in expected_execution_boundary.items():
        if execution_boundary.get(field_name) != expected_value:
            raise ContractValidationError(f"candidate prescreen execution boundary drifted at {field_name}")

    sources = _require_list(workflow.get("sources"), "candidate_prescreen_workflow.yaml:sources")
    if len(sources) != 2:
        raise ContractValidationError("candidate prescreen workflow must register exactly github and product_hunt sources")
    github_source = next(
        (_require_mapping(entry, "candidate_prescreen_workflow.yaml:sources[]") for entry in sources if _require_mapping(entry, "candidate_prescreen_workflow.yaml:sources[]").get("source_code") == "github"),
        None,
    )
    product_hunt_source = next(
        (_require_mapping(entry, "candidate_prescreen_workflow.yaml:sources[]") for entry in sources if _require_mapping(entry, "candidate_prescreen_workflow.yaml:sources[]").get("source_code") == "product_hunt"),
        None,
    )
    if github_source is None or product_hunt_source is None:
        raise ContractValidationError("candidate prescreen workflow must include github and product_hunt source entries")

    expected_discovery_capabilities = {
        "github": {
            "fixture_supported": True,
            "replay_supported": True,
            "live_supported": True,
            "live_enabled_in_current_phase": True,
            "current_phase_live_status": "enabled",
            "future_live_boundary_preserved": True,
        },
        "product_hunt": {
            "fixture_supported": True,
            "replay_supported": True,
            "live_supported": True,
            "live_enabled_in_current_phase": False,
            "current_phase_live_status": "deferred",
            "future_live_boundary_preserved": True,
        },
    }
    for source_name, source_entry in {"github": github_source, "product_hunt": product_hunt_source}.items():
        discovery_capabilities = _require_mapping(
            source_entry.get("discovery_capabilities"),
            f"candidate_prescreen_workflow.yaml:{source_name}:discovery_capabilities",
        )
        for field_name, expected_value in expected_discovery_capabilities[source_name].items():
            actual_value = discovery_capabilities.get(field_name)
            if actual_value != expected_value:
                raise ContractValidationError(
                    f"candidate prescreen {source_name} discovery_capabilities drifted at {field_name}"
                )

    if github_source.get("source_id") != "src_github" or github_source.get("time_field") != "pushed_at":
        raise ContractValidationError("candidate prescreen github source must stay bound to src_github + pushed_at")
    if github_source.get("selection_rule_version") != "github_qsv1":
        raise ContractValidationError("candidate prescreen github selection_rule_version must stay github_qsv1")
    github_candidate_gate = _require_mapping(
        github_source.get("candidate_gate"),
        "candidate_prescreen_workflow.yaml:github:candidate_gate",
    )
    if github_candidate_gate.get("gate_version") != "github_candidate_gate_v1":
        raise ContractValidationError("candidate prescreen github candidate_gate must stay github_candidate_gate_v1")
    expected_candidate_gate_lists = {
        "modality_signal_terms": [
            "agent",
            "agents",
            "assistant",
            "assistants",
            "copilot",
            "copilots",
            "chatbot",
            "chatbots",
            "rag",
            "workflow",
            "workflows",
        ],
        "product_context_signal_terms": [
            "workspace",
            "workbench",
            "dashboard",
            "portal",
            "app",
            "application",
            "service",
            "platform",
            "saas",
            "team",
            "teams",
            "customer",
            "customers",
            "sales",
            "support",
            "finance",
            "legal",
            "hr",
            "marketing",
            "recruiting",
            "recruiter",
            "operations",
            "field service",
            "meeting",
            "meetings",
            "notes",
            "follow-up",
            "follow up",
            "intake",
            "dispatch",
            "inbox",
            "helpdesk",
            "ticket",
            "tickets",
            "case",
            "cases",
            "crm",
            "budget",
            "document",
            "documents",
            "knowledge",
        ],
        "exclusion_signal_terms": [
            "sdk",
            "framework",
            "library",
            "boilerplate",
            "starter",
            "template",
            "plugin",
            "toolkit",
            "scaffold",
            "example",
            "tutorial",
            "course",
            "benchmark",
            "eval",
            "evaluation",
            "reference solution",
            "blueprint",
            "api client",
            "wrapper",
            "orchestration",
            "observability",
            "adapter",
            "demo",
            "sample app",
        ],
    }
    for field_name, expected_terms in expected_candidate_gate_lists.items():
        actual_terms = _require_list(
            github_candidate_gate.get(field_name),
            f"candidate_prescreen_workflow.yaml:github:candidate_gate:{field_name}",
        )
        if actual_terms != expected_terms:
            raise ContractValidationError(f"candidate prescreen github {field_name} drifted from github_candidate_gate_v1")
    if github_candidate_gate.get("min_summary_chars") != 24 or github_candidate_gate.get("min_evidence_chars") != 80:
        raise ContractValidationError("candidate prescreen github candidate_gate threshold drifted from github_candidate_gate_v1")
    github_filters = _require_list(github_source.get("fixed_filters"), "candidate_prescreen_workflow.yaml:github:fixed_filters")
    if github_filters != ["is:public", "fork:false", "archived:false", "mirror:false"]:
        raise ContractValidationError("candidate prescreen github fixed_filters drifted from github_qsv1")
    github_slices = _require_list(github_source.get("query_slices"), "candidate_prescreen_workflow.yaml:github:query_slices")
    expected_slice_ids = {
        "qf_agent",
        "qf_rag",
        "qf_ai_assistant",
        "qf_copilot",
        "qf_chatbot",
        "qf_ai_workflow",
    }
    seen_slice_ids: set[str] = set()
    for entry in github_slices:
        slice_config = _require_mapping(entry, "candidate_prescreen_workflow.yaml:github:query_slices[]")
        query_slice_id = _require_string(slice_config.get("query_slice_id"), "candidate prescreen github query_slice_id")
        seen_slice_ids.add(query_slice_id)
        if slice_config.get("query_family") != "ai_applications_and_products":
            raise ContractValidationError(f"{query_slice_id} must stay in the ai_applications_and_products family")
        _require_string(slice_config.get("query_text_template"), f"{query_slice_id}:query_text_template")
        if _require_bool(slice_config.get("enabled"), f"{query_slice_id}:enabled") is not True:
            raise ContractValidationError(f"{query_slice_id} must stay enabled in candidate prescreen workflow")
    if seen_slice_ids != expected_slice_ids:
        raise ContractValidationError("candidate prescreen github query_slice set drifted from github_qsv1")

    if product_hunt_source.get("source_id") != "src_product_hunt" or product_hunt_source.get("time_field") != "published_at":
        raise ContractValidationError("candidate prescreen product_hunt source must stay bound to src_product_hunt + published_at")
    if product_hunt_source.get("selection_rule_version") != "product_hunt_published_window_v1":
        raise ContractValidationError("candidate prescreen product_hunt selection_rule_version drifted")
    ph_slices = _require_list(product_hunt_source.get("query_slices"), "candidate_prescreen_workflow.yaml:product_hunt:query_slices")
    if len(ph_slices) != 1:
        raise ContractValidationError("candidate prescreen product_hunt must keep exactly one published-window slice in v1")
    ph_slice = _require_mapping(ph_slices[0], "candidate_prescreen_workflow.yaml:product_hunt:query_slices[0]")
    if ph_slice.get("query_slice_id") != "ph_published_launches" or ph_slice.get("query_family") != "published_launches":
        raise ContractValidationError("candidate prescreen product_hunt slice drifted from the published_at window boundary")

    model_routing = _load_config_mapping(config_dir, "model_routing.yaml")
    routes = _require_list(model_routing.get("routes"), "model_routing.yaml:routes")
    route_ids = {
        _require_string(_require_mapping(entry, "model_routing.yaml:routes[]").get("route_id"), "model_routing route_id")
        for entry in routes
    }
    if "route_candidate_prescreener_v1" not in route_ids:
        raise ContractValidationError("model_routing.yaml must register route_candidate_prescreener_v1")

    candidate_schema = _load_schema_mapping(schema_dir, "candidate_prescreen_record.schema.json")
    required_fields = _require_list(candidate_schema.get("required"), "candidate_prescreen_record.schema.json:required")
    for field_name in (
        "candidate_id",
        "source",
        "source_window",
        "external_id",
        "canonical_url",
        "llm_prescreen",
        "human_review_status",
        "human_review_note_template_key",
        "human_review_notes",
        "staging_handoff",
    ):
        if field_name not in required_fields:
            raise ContractValidationError(f"candidate_prescreen_record.schema.json must require {field_name}")


def _load_gold_set_status(gold_set_dir: Path) -> str:
    readme_path = gold_set_dir / "README.md"
    if not readme_path.exists():
        raise ContractValidationError("gold_set/README.md is required")
    readme = readme_path.read_text(encoding="utf-8")
    matches = [status for status in ("stub", "implemented") if f"status = {status}" in readme]
    if len(matches) != 1:
        raise ContractValidationError("gold_set/README.md must declare exactly one status = stub|implemented marker")
    return matches[0]


def _decision_band(value: object, description: str) -> str:
    band = _require_string(value, description)
    if band not in {"high", "medium", "low"}:
        raise ContractValidationError(f"{description} must be one of high|medium|low")
    return band


def _validate_taxonomy_change_suggestion(value: object, description: str) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{description} must be null or a non-empty string")


def _validate_local_channel_metadata(metadata: dict[str, object], description: str) -> None:
    if not any(isinstance(candidate, str) and candidate for candidate in metadata.values()):
        raise ContractValidationError(f"{description} must retain at least one non-empty channel metadata field")


def _validate_llm_channel_metadata(metadata: dict[str, object], description: str) -> None:
    _require_string(metadata.get("prompt_version"), f"{description}:prompt_version")
    _require_string(metadata.get("routing_version"), f"{description}:routing_version")


def _validate_annotation_decision(record: dict[str, object], description: str, *, allow_adjudicated: bool) -> None:
    _require_string(record.get("sample_id"), f"{description}:sample_id")
    if record.get("target_type") != "product":
        raise ContractValidationError(f"{description}:target_type must stay product")
    _require_string(record.get("target_id"), f"{description}:target_id")
    primary_category_code = _require_string(record.get("primary_category_code"), f"{description}:primary_category_code")
    if primary_category_code == "unresolved":
        raise ContractValidationError(f"{description}:primary_category_code cannot be unresolved inside gold_set_300")
    secondary_category_code = record.get("secondary_category_code")
    if secondary_category_code is not None:
        _require_string(secondary_category_code, f"{description}:secondary_category_code")
    _require_string(record.get("primary_persona_code"), f"{description}:primary_persona_code")
    _require_string(record.get("delivery_form_code"), f"{description}:delivery_form_code")
    _decision_band(record.get("build_evidence_band"), f"{description}:build_evidence_band")
    _decision_band(record.get("need_clarity_band"), f"{description}:need_clarity_band")
    _require_string(record.get("rationale"), f"{description}:rationale")
    _require_non_empty_ref_list(record.get("evidence_refs"), f"{description}:evidence_refs")
    adjudication_status = _require_string(record.get("adjudication_status"), f"{description}:adjudication_status")
    allowed_statuses = {"double_annotated", "adjudicated"} if allow_adjudicated else {"double_annotated"}
    if adjudication_status not in allowed_statuses:
        allowed = ", ".join(sorted(allowed_statuses))
        raise ContractValidationError(f"{description}:adjudication_status must stay within {{{allowed}}}")
    review_recommended = _require_bool(record.get("review_recommended"), f"{description}:review_recommended")
    review_reason = record.get("review_reason")
    if review_recommended:
        _require_string(review_reason, f"{description}:review_reason")
    elif review_reason is not None:
        _require_string(review_reason, f"{description}:review_reason")
    _validate_taxonomy_change_suggestion(record.get("taxonomy_change_suggestion"), f"{description}:taxonomy_change_suggestion")


def _validate_gold_set_sample(sample_dir: Path) -> None:
    sample_metadata_path = sample_dir / "sample_metadata.json"
    adjudication_path = sample_dir / "adjudication.json"
    local_annotation_path = sample_dir / "annotations" / "local_project_user.json"
    llm_annotation_path = sample_dir / "annotations" / "llm.json"

    for path in (sample_metadata_path, adjudication_path, local_annotation_path, llm_annotation_path):
        if not path.exists():
            raise ContractValidationError(f"gold set sample is missing required file: {path.relative_to(sample_dir.parent.parent)}")

    sample_metadata = _require_mapping(load_json(sample_metadata_path), f"{sample_dir.name}:sample_metadata")
    sample_id = _require_string(sample_metadata.get("sample_id"), f"{sample_dir.name}:sample_metadata:sample_id")
    if sample_id != sample_dir.name:
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata:sample_id must match the sample directory name")
    if sample_metadata.get("target_type") != "product":
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata:target_type must stay product")
    target_id = _require_string(sample_metadata.get("target_id"), f"{sample_dir.name}:sample_metadata:target_id")
    _require_string(sample_metadata.get("source_id"), f"{sample_dir.name}:sample_metadata:source_id")
    _require_non_empty_ref_list(sample_metadata.get("source_record_refs"), f"{sample_dir.name}:sample_metadata:source_record_refs")
    _require_non_empty_ref_list(sample_metadata.get("review_refs"), f"{sample_dir.name}:sample_metadata:review_refs")
    _require_non_empty_ref_list(sample_metadata.get("evidence_refs"), f"{sample_dir.name}:sample_metadata:evidence_refs")
    eligibility_snapshot = _require_mapping(sample_metadata.get("eligibility_snapshot"), f"{sample_dir.name}:sample_metadata:eligibility_snapshot")
    if _require_bool(eligibility_snapshot.get("review_closed"), f"{sample_dir.name}:eligibility_snapshot:review_closed") is not True:
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata must retain review_closed = true")
    if _require_bool(eligibility_snapshot.get("sufficient_evidence"), f"{sample_dir.name}:eligibility_snapshot:sufficient_evidence") is not True:
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata must retain sufficient_evidence = true")
    if _require_bool(eligibility_snapshot.get("clear_adjudication"), f"{sample_dir.name}:eligibility_snapshot:clear_adjudication") is not True:
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata must retain clear_adjudication = true")
    if _require_bool(eligibility_snapshot.get("is_unresolved"), f"{sample_dir.name}:eligibility_snapshot:is_unresolved") is not False:
        raise ContractValidationError(f"{sample_dir.name}:sample_metadata must retain is_unresolved = false")
    pool_trace = _require_mapping(sample_metadata.get("pool_trace"), f"{sample_dir.name}:sample_metadata:pool_trace")
    _require_string(pool_trace.get("candidate_pool_batch_id"), f"{sample_dir.name}:pool_trace:candidate_pool_batch_id")
    if pool_trace.get("training_pool_source") != "candidate_pool":
        raise ContractValidationError(f"{sample_dir.name}:pool_trace:training_pool_source must stay candidate_pool")
    whitelist_reason = pool_trace.get("whitelist_reason")
    if whitelist_reason is not None:
        _require_string(whitelist_reason, f"{sample_dir.name}:pool_trace:whitelist_reason")

    local_annotation = _require_mapping(load_json(local_annotation_path), f"{sample_dir.name}:annotations:local_project_user")
    if _require_string(local_annotation.get("sample_id"), f"{sample_dir.name}:annotations:local_project_user:sample_id") != sample_id:
        raise ContractValidationError(f"{sample_dir.name}: local_project_user sample_id drifted from sample_metadata")
    if _require_string(local_annotation.get("target_id"), f"{sample_dir.name}:annotations:local_project_user:target_id") != target_id:
        raise ContractValidationError(f"{sample_dir.name}: local_project_user target_id drifted from sample_metadata")
    if local_annotation.get("annotator_channel") != "local_project_user":
        raise ContractValidationError(f"{sample_dir.name}: local_project_user annotation must declare annotator_channel = local_project_user")
    _require_string(local_annotation.get("annotated_at"), f"{sample_dir.name}:annotations:local_project_user:annotated_at")
    _validate_annotation_decision(local_annotation, f"{sample_dir.name}:annotations:local_project_user", allow_adjudicated=False)
    local_channel_metadata = _require_mapping(
        local_annotation.get("channel_metadata"),
        f"{sample_dir.name}:annotations:local_project_user:channel_metadata",
    )
    _validate_local_channel_metadata(local_channel_metadata, f"{sample_dir.name}:annotations:local_project_user:channel_metadata")

    llm_annotation = _require_mapping(load_json(llm_annotation_path), f"{sample_dir.name}:annotations:llm")
    if _require_string(llm_annotation.get("sample_id"), f"{sample_dir.name}:annotations:llm:sample_id") != sample_id:
        raise ContractValidationError(f"{sample_dir.name}: llm sample_id drifted from sample_metadata")
    if _require_string(llm_annotation.get("target_id"), f"{sample_dir.name}:annotations:llm:target_id") != target_id:
        raise ContractValidationError(f"{sample_dir.name}: llm target_id drifted from sample_metadata")
    if llm_annotation.get("annotator_channel") != "llm":
        raise ContractValidationError(f"{sample_dir.name}: llm annotation must declare annotator_channel = llm")
    _require_string(llm_annotation.get("annotated_at"), f"{sample_dir.name}:annotations:llm:annotated_at")
    _validate_annotation_decision(llm_annotation, f"{sample_dir.name}:annotations:llm", allow_adjudicated=False)
    llm_channel_metadata = _require_mapping(llm_annotation.get("channel_metadata"), f"{sample_dir.name}:annotations:llm:channel_metadata")
    _validate_llm_channel_metadata(llm_channel_metadata, f"{sample_dir.name}:annotations:llm:channel_metadata")

    adjudication = _require_mapping(load_json(adjudication_path), f"{sample_dir.name}:adjudication")
    if _require_string(adjudication.get("sample_id"), f"{sample_dir.name}:adjudication:sample_id") != sample_id:
        raise ContractValidationError(f"{sample_dir.name}: adjudication sample_id drifted from sample_metadata")
    _require_string(adjudication.get("adjudicated_at"), f"{sample_dir.name}:adjudication:adjudicated_at")
    if adjudication.get("adjudicator_role") != "local_project_user":
        raise ContractValidationError(f"{sample_dir.name}:adjudication:adjudicator_role must stay local_project_user")
    source_annotation_channels = _require_list(adjudication.get("source_annotation_channels"), f"{sample_dir.name}:adjudication:source_annotation_channels")
    if source_annotation_channels != ["local_project_user", "llm"]:
        raise ContractValidationError(f"{sample_dir.name}:adjudication must retain source_annotation_channels = [local_project_user, llm]")
    final_decision = _require_mapping(adjudication.get("final_decision"), f"{sample_dir.name}:adjudication:final_decision")
    if _require_string(final_decision.get("sample_id"), f"{sample_dir.name}:adjudication:final_decision:sample_id") != sample_id:
        raise ContractValidationError(f"{sample_dir.name}: adjudication final_decision sample_id drifted from sample_metadata")
    if _require_string(final_decision.get("target_id"), f"{sample_dir.name}:adjudication:final_decision:target_id") != target_id:
        raise ContractValidationError(f"{sample_dir.name}: adjudication final_decision target_id drifted from sample_metadata")
    _validate_annotation_decision(final_decision, f"{sample_dir.name}:adjudication:final_decision", allow_adjudicated=True)
    _require_string(adjudication.get("adjudication_rationale"), f"{sample_dir.name}:adjudication:adjudication_rationale")
    _require_non_empty_ref_list(adjudication.get("review_refs"), f"{sample_dir.name}:adjudication:review_refs")
    _require_non_empty_ref_list(adjudication.get("evidence_refs"), f"{sample_dir.name}:adjudication:evidence_refs")
    _require_non_empty_ref_list(adjudication.get("decision_basis_refs"), f"{sample_dir.name}:adjudication:decision_basis_refs")


def validate_gold_set(config: AppConfig, *, require_implemented: bool = False) -> tuple[str, int]:
    status = _load_gold_set_status(config.gold_set_dir)
    gold_set_300_dir = config.gold_set_dir / "gold_set_300"
    if not gold_set_300_dir.exists() or not gold_set_300_dir.is_dir():
        raise ContractValidationError("gold_set/gold_set_300/ directory is required")

    # README/.gitkeep are scaffolding; anything else must either be a real sample directory or absent in stub mode.
    sample_entries = [
        entry
        for entry in sorted(gold_set_300_dir.iterdir())
        if entry.name not in {".gitkeep", "README.md"} and not entry.name.startswith(".")
    ]

    if status == "stub":
        if sample_entries:
            raise ContractValidationError("gold_set/README.md says status = stub but gold_set/gold_set_300/ already contains sample assets")
        if require_implemented:
            raise ContractValidationError("gold_set remains status = stub; real double-annotation assets are still required")
        return status, 0

    sample_dirs = [entry for entry in sample_entries if entry.is_dir()]
    stray_files = [entry for entry in sample_entries if not entry.is_dir()]
    if stray_files:
        raise ContractValidationError("gold_set/gold_set_300/ may only contain sample directories plus README/.gitkeep")
    if not sample_dirs:
        raise ContractValidationError("gold_set status = implemented requires at least one adjudicated sample directory")
    for sample_dir in sample_dirs:
        _validate_gold_set_sample(sample_dir)
    return status, len(sample_dirs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apo-observatory", description="Minimal runnable baseline for the observatory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Bootstrap local runtime directories and dependency checks.")
    subparsers.add_parser("validate-schemas", help="Validate JSON schema documents under schemas/.")
    subparsers.add_parser("validate-configs", help="Validate YAML config artifacts and schema alignment guardrails.")
    gold_set_parser = subparsers.add_parser(
        "validate-gold-set",
        help="Validate the gold_set/ directory contract and current formal sample asset completeness.",
    )
    gold_set_parser.add_argument("--require-implemented", action="store_true")
    subparsers.add_parser("validate-candidate-workspace", help="Validate candidate prescreen YAML documents outside gold_set/.")
    subparsers.add_parser(
        "archive-duplicate-candidate-records",
        help="Archive duplicate candidate prescreen records by semantic key while keeping the preferred active document.",
    )
    archive_future_window_parser = subparsers.add_parser(
        "archive-future-window-candidate-records",
        help="Archive candidate prescreen records whose source_window extends too far into the future.",
    )
    archive_future_window_parser.add_argument("--today")
    archive_future_window_parser.add_argument("--grace-days", type=int, default=7)
    subparsers.add_parser(
        "check-candidate-prescreen-relay",
        help="Validate relay configuration and DNS resolution before live candidate prescreen runs.",
    )
    subparsers.add_parser(
        "dedupe-staging-semantic-duplicates",
        help="Clear duplicate staging slots that point at the same source_id + external_id semantic sample.",
    )
    subparsers.add_parser(
        "probe-candidate-prescreen-relay",
        help="Send one minimal candidate-prescreener request to the relay to verify real API traffic.",
    )
    relay_probe_parser = subparsers.choices["probe-candidate-prescreen-relay"]
    relay_probe_parser.add_argument("--output-path")
    relay_probe_parser.add_argument("--max-retries", type=int, default=0)
    relay_probe_parser.add_argument("--request-interval-seconds", type=int, default=0)
    relay_probe_parser.add_argument("--retry-sleep-seconds", type=int, default=0)

    candidate_parser = subparsers.add_parser(
        "run-candidate-prescreen",
        help="Discover candidates, call the relay-LLM prescreener, and write candidate docs outside gold_set/.",
    )
    candidate_parser.add_argument("--source", required=True)
    candidate_parser.add_argument("--window", required=True)
    candidate_parser.add_argument("--query-slice")
    candidate_parser.add_argument("--limit", type=int, default=10)
    candidate_parser.add_argument("--discovery-fixture-path")
    candidate_parser.add_argument("--llm-fixture-path")
    candidate_parser.add_argument("--discovery-request-interval-seconds", type=int)
    candidate_parser.add_argument("--provider-request-interval-seconds", type=int)
    candidate_parser.add_argument("--retry-sleep-seconds", type=int)

    staging_handoff_parser = subparsers.add_parser(
        "handoff-candidates-to-staging",
        help="Write only human-approved candidate prescreen records into the external staging carrier.",
    )
    staging_handoff_parser.add_argument("--candidate-id", action="append", default=[])

    fill_parser = subparsers.add_parser(
        "fill-gold-set-staging-until-complete",
        help="Maintain the historical gold_set staging carrier by filling open slots when explicitly requested.",
    )
    fill_parser.add_argument("--source")
    fill_parser.add_argument("--initial-window")
    fill_parser.add_argument("--query-slice")
    fill_parser.add_argument("--live-limit", type=int, default=1)
    fill_parser.add_argument("--discovery-fixture-path")
    fill_parser.add_argument("--llm-fixture-path")
    fill_parser.add_argument("--max-iterations", type=int)
    fill_parser.add_argument("--discovery-request-interval-seconds", type=int)
    fill_parser.add_argument("--provider-request-interval-seconds", type=int)
    fill_parser.add_argument("--retry-sleep-seconds", type=int)

    env_parser = subparsers.add_parser(
        "validate-env",
        help="Validate resolved runtime config entries and any explicitly required non-config environment variables.",
    )
    env_parser.add_argument("--require", nargs="+", required=True)

    lint_parser = subparsers.add_parser("lint", help="Run lightweight Python lint checks.")
    lint_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    format_parser = subparsers.add_parser("format", help="Strip trailing whitespace and ensure trailing newlines.")
    format_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    typecheck_parser = subparsers.add_parser("typecheck", help="Run annotation coverage checks on Python modules.")
    typecheck_parser.add_argument("paths", nargs="*", default=["src", "tests"])

    replay_parser = subparsers.add_parser("replay-window", help="Replay a per-source window from fixture or GitHub live discovery.")
    replay_parser.add_argument("--source", required=True)
    replay_parser.add_argument("--window", required=True)
    replay_parser.add_argument("--live", action="store_true")
    replay_parser.add_argument("--query-slice")

    subparsers.add_parser("build-mart-window", help="Build the default mart fixture into a local mart artifact.")

    dashboard_view_parser = subparsers.add_parser(
        "dashboard-view",
        help="Render the mart-backed dashboard payload without rejoining runtime tables.",
    )
    dashboard_view_parser.add_argument("--mart-path")

    dashboard_reconciliation_parser = subparsers.add_parser(
        "dashboard-reconciliation",
        help="Run the local mart-backed dashboard reconciliation checks for Phase1-F/Phase1-G.",
    )
    dashboard_reconciliation_parser.add_argument("--mart-path")

    phase1_g_audit_parser = subparsers.add_parser(
        "phase1-g-audit-ready-report",
        help="Materialize the local Phase1-G audit-ready report without claiming manual audit or owner sign-off.",
    )
    phase1_g_audit_parser.add_argument("--mart-path")
    phase1_g_audit_parser.add_argument("--output-path")

    drill_down_parser = subparsers.add_parser(
        "product-drill-down",
        help="Render one mart-backed drill-down payload for a product trace path.",
    )
    drill_down_parser.add_argument("--product-id", required=True)
    drill_down_parser.add_argument("--mart-path")

    trigger_review_parser = subparsers.add_parser(
        "trigger-taxonomy-review",
        help="Run the Phase1-D taxonomy path for one source_item JSON and persist any triggered review_issue.",
    )
    trigger_review_parser.add_argument("--source-item-path", required=True)
    trigger_review_parser.add_argument("--record-path")
    trigger_review_parser.add_argument("--issue-type")
    trigger_review_parser.add_argument("--priority-code")
    trigger_review_parser.add_argument("--created-at")

    review_queue_parser = subparsers.add_parser(
        "review-queue",
        help="Render the local file-backed review_queue_view derived from review_issues.json.",
    )
    review_queue_parser.add_argument("--open-only", action="store_true")

    resolve_review_parser = subparsers.add_parser(
        "resolve-taxonomy-review",
        help="Apply taxonomy review resolution and optional maker-checker approval to a record snapshot.",
    )
    resolve_review_parser.add_argument("--record-path", required=True)
    resolve_review_parser.add_argument("--review-issue-id", required=True)
    resolve_review_parser.add_argument("--resolution-action", required=True)
    resolve_review_parser.add_argument("--resolution-notes", required=True)
    resolve_review_parser.add_argument("--reviewer", required=True)
    resolve_review_parser.add_argument("--reviewed-at")
    resolve_review_parser.add_argument("--approver")
    resolve_review_parser.add_argument("--approved-at")
    resolve_review_parser.add_argument("--override-category-code")
    resolve_review_parser.add_argument("--unresolved-mode")
    resolve_review_parser.add_argument("--output-path")

    trigger_entity_parser = subparsers.add_parser(
        "trigger-entity-review",
        help="Run the entity resolver on one source_item JSON and persist entity_merge_uncertainty when review is required.",
    )
    trigger_entity_parser.add_argument("--source-item-path", required=True)
    trigger_entity_parser.add_argument("--existing-products-path", required=True)
    trigger_entity_parser.add_argument("--priority-code")
    trigger_entity_parser.add_argument("--created-at")

    trigger_score_parser = subparsers.add_parser(
        "trigger-score-review",
        help="Persist a score_conflict or suspicious_result review issue from a traceable score snapshot JSON.",
    )
    trigger_score_parser.add_argument("--score-snapshot-path", required=True)
    trigger_score_parser.add_argument("--issue-type", required=True)
    trigger_score_parser.add_argument("--priority-code")
    trigger_score_parser.add_argument("--created-at")

    migrate_parser = subparsers.add_parser("migrate", help="Show the reserved migration entrypoint plan.")
    migrate_parser.add_argument("--plan", action="store_true")

    return parser


def validate_configs(config: AppConfig) -> int:
    _validate_source_registry_config(config.config_dir)
    _validate_taxonomy_config(config.config_dir)
    _validate_vocab_configs(config.config_dir)
    _validate_rubric_config(config.config_dir)
    _validate_review_rules_config(config.config_dir)
    _validate_schema_alignment(config.config_dir, config.schema_dir)
    _validate_candidate_prescreen_config(config.config_dir, config.schema_dir)
    return 10


def validate_schemas(config: AppConfig) -> int:
    schema_paths = sorted(config.schema_dir.glob("*.json"))
    for schema_path in schema_paths:
        validate_schema_document(schema_path)
    return len(schema_paths)


def _quality_paths(values: list[str]) -> list[Path]:
    return [Path(value).resolve() for value in values]


def bootstrap_install(config: AppConfig) -> str:
    config.raw_store_dir.mkdir(parents=True, exist_ok=True)
    config.task_store_path.parent.mkdir(parents=True, exist_ok=True)
    config.mart_output_dir.mkdir(parents=True, exist_ok=True)
    if not config.task_store_path.exists():
        dump_json(config.task_store_path, [])
    review_issue_store_path = default_review_issue_store_path(config.task_store_path)
    if not review_issue_store_path.exists():
        dump_json(review_issue_store_path, [])
    processing_error_store_path = default_processing_error_store_path(config.task_store_path)
    if not processing_error_store_path.exists():
        dump_json(processing_error_store_path, [])
    return "bootstrap_complete"


def _load_or_build_mart(config: AppConfig, mart_path: str | None) -> dict[str, object]:
    if mart_path:
        return _require_mapping(load_json(Path(mart_path)), f"mart:{mart_path}")
    return _require_mapping(build_default_mart(config), "default mart")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = AppConfig.from_env(Path.cwd())
        configure_logging(config.log_level)
        logger = get_logger("cli")

        if args.command == "install":
            status = bootstrap_install(config)
            logger.info(f"local install bootstrap status={status}")
            return 0

        if args.command == "validate-schemas":
            count = validate_schemas(config)
            logger.info(f"validated {count} schema documents")
            return 0

        if args.command == "validate-configs":
            count = validate_configs(config)
            logger.info(f"validated {count} config artifacts")
            return 0

        if args.command == "validate-gold-set":
            status, sample_count = validate_gold_set(config, require_implemented=args.require_implemented)
            logger.info(f"validated gold_set status={status} sample_count={sample_count}")
            return 0

        if args.command == "validate-candidate-workspace":
            count = workflow_validate_candidate_workspace(config)
            logger.info(f"validated candidate workspace document_count={count}")
            return 0

        if args.command == "archive-duplicate-candidate-records":
            summary = workflow_archive_duplicate_candidate_records(config)
            logger.info(
                "archive-duplicate-candidate-records "
                f"archived_record_count={summary['archived_record_count']} skipped_group_count={summary['skipped_group_count']} "
                f"active_candidate_document_count={summary['active_candidate_document_count']}"
            )
            print(json.dumps(summary, ensure_ascii=True))
            return 0

        if args.command == "archive-future-window-candidate-records":
            summary = workflow_archive_future_window_candidate_records(
                config,
                today=date.fromisoformat(args.today) if args.today else None,
                grace_days=args.grace_days,
            )
            logger.info(
                "archive-future-window-candidate-records "
                f"archived_record_count={summary['archived_record_count']} skipped_record_count={summary['skipped_record_count']} "
                f"active_candidate_document_count={summary['active_candidate_document_count']}"
            )
            print(json.dumps(summary, ensure_ascii=True))
            return 0

        if args.command == "check-candidate-prescreen-relay":
            workflow = load_candidate_prescreen_config(config.config_dir)
            llm_prescreen = _require_mapping(workflow.get("llm_prescreen"), "candidate_prescreen_workflow.yaml:llm_prescreen")
            status = relay_preflight(
                default_timeout_seconds=int(llm_prescreen["timeout_seconds_default"]),
                default_client_version=str(llm_prescreen["relay_client_version"]),
            )
            logger.info(
                "check-candidate-prescreen-relay "
                f"host={status['host']} model={status['model']} api_style={status['api_style']}"
            )
            print(json.dumps(status, ensure_ascii=True))
            return 0

        if args.command == "dedupe-staging-semantic-duplicates":
            summary = dedupe_staging_semantic_duplicates(config.gold_set_staging_dir)
            logger.info(
                "dedupe-staging-semantic-duplicates "
                f"duplicate_group_count={summary['duplicate_group_count']} "
                f"cleared_slot_count={summary['cleared_slot_count']} "
                f"staging_total_filled={summary['staging_total_filled']}"
            )
            print(json.dumps(summary, ensure_ascii=True))
            return 0

        if args.command == "probe-candidate-prescreen-relay":
            workflow = load_candidate_prescreen_config(config.config_dir)
            llm_prescreen = _require_mapping(workflow.get("llm_prescreen"), "candidate_prescreen_workflow.yaml:llm_prescreen")
            result = relay_screen_candidate(
                {
                    "source": "github",
                    "source_id": "src_github",
                    "source_window": "2026-04-01..2026-04-06",
                    "time_field": "pushed_at",
                    "external_id": "relay-probe-smoke-test",
                    "canonical_url": "https://github.com/example/relay-probe-smoke-test",
                    "title": "Relay Probe Smoke Test",
                    "summary": "Synthetic candidate used only to verify relay connectivity.",
                    "raw_evidence_excerpt": "Synthetic evidence for relay smoke testing. Not a real candidate.",
                    "query_family": "ai_applications_and_products",
                    "query_slice_id": "qf_agent",
                    "selection_rule_version": "github_qsv1",
                },
                prompt_version=str(llm_prescreen["prompt_version"]),
                routing_version=str(llm_prescreen["routing_version"]),
                relay_transport=str(llm_prescreen["relay_transport"]),
                relay_client_version=str(llm_prescreen["relay_client_version"]),
                prompt_contract=candidate_prescreener_prompt_contract(
                    prompt_spec_ref=str(llm_prescreen.get("prompt_spec_ref") or "")
                ),
                fixture_path=None,
                timeout_seconds=int(llm_prescreen["timeout_seconds_default"]),
                max_retries=args.max_retries,
                request_interval_seconds=args.request_interval_seconds,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            if args.output_path:
                dump_json(Path(args.output_path), result)
            logger.info(
                "probe-candidate-prescreen-relay "
                f"request_id={result.get('request_id')} response_id={result.get('response_id')} "
                f"attempt_count={result.get('attempt_count')} business_status={result.get('business_status')}"
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0

        if args.command == "run-candidate-prescreen":
            written_paths = run_candidate_prescreen(
                config,
                source_code=args.source,
                window=args.window,
                query_slice_id=args.query_slice,
                limit=args.limit,
                discovery_fixture_path=Path(args.discovery_fixture_path) if args.discovery_fixture_path else None,
                llm_fixture_path=Path(args.llm_fixture_path) if args.llm_fixture_path else None,
                discovery_request_interval_seconds=args.discovery_request_interval_seconds,
                request_interval_seconds=args.provider_request_interval_seconds,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            logger.info(f"candidate prescreen wrote {len(written_paths)} documents")
            for path in written_paths:
                print(path)
            return 0

        if args.command == "handoff-candidates-to-staging":
            results = workflow_handoff_candidates_to_staging(config, candidate_ids=args.candidate_id or None)
            logger.info(f"candidate-to-staging handoff wrote {len(results)} entries")
            for candidate_path, staging_document_path, slot_id in results:
                print(f"{candidate_path} -> {staging_document_path} [{slot_id}]")
            return 0

        if args.command == "fill-gold-set-staging-until-complete":
            summary = fill_gold_set_staging_until_complete(
                config,
                source_code=args.source,
                initial_window=args.initial_window,
                query_slice_id=args.query_slice,
                live_limit=args.live_limit,
                discovery_fixture_path=Path(args.discovery_fixture_path) if args.discovery_fixture_path else None,
                llm_fixture_path=Path(args.llm_fixture_path) if args.llm_fixture_path else None,
                max_iterations=args.max_iterations,
                discovery_request_interval_seconds=args.discovery_request_interval_seconds,
                provider_request_interval_seconds=args.provider_request_interval_seconds,
                retry_sleep_seconds=args.retry_sleep_seconds,
            )
            logger.info(
                "fill-gold-set-staging-until-complete "
                f"status={summary['status']} iterations={summary['iterations']} total_filled={summary['total_filled']} "
                f"audit_log_path={summary['audit_log_path']}"
            )
            print(json.dumps(summary, ensure_ascii=True))
            return 0

        if args.command == "validate-env":
            resolved = resolve_required_settings(config, args.require)
            resolved_summary = summarize_resolved_settings(resolved)
            logger.info(f"validated resolved settings: {resolved_summary}")
            return 0

        if args.command == "lint":
            result = lint_python(_quality_paths(args.paths))
            logger.info(f"lint checked {result.checked_files} files")
            return 0

        if args.command == "format":
            result = format_python(_quality_paths(args.paths))
            logger.info(f"format checked {result.checked_files} files and changed {result.changed_files}")
            return 0

        if args.command == "typecheck":
            result = typecheck_python(_quality_paths(args.paths))
            logger.info(f"typecheck checked {result.checked_files} files")
            return 0

        if args.command == "replay-window":
            result = replay_source_window(
                source_code=args.source,
                window=args.window,
                config=config,
                use_live=args.live,
                query_slice_id=args.query_slice,
            )
            replay_logger = get_logger(
                "cli",
                source_id=result["crawl_run"]["source_id"],
                run_id=result["crawl_run"]["crawl_run_id"],
                task_id=result["task_id"],
                resolution_status="succeeded",
            )
            replay_logger.info("replay finished")
            print(
                f"task_id={result['task_id']} raw_records={len(result['raw_records'])} "
                f"source_items={len(result['source_items'])}"
            )
            return 0

        if args.command == "build-mart-window":
            result = build_mart_window(config)
            mart = result["mart"]
            print(
                f"task_id={result['task_id']} mart_rows={len(mart['top_jtbd_products_30d'])} "
                f"attention_rows={len(mart['attention_distribution_30d'])}"
            )
            return 0

        if args.command == "dashboard-view":
            mart = _load_or_build_mart(config, args.mart_path)
            print(json.dumps(build_dashboard_view(mart), ensure_ascii=True))
            return 0

        if args.command == "dashboard-reconciliation":
            mart = _load_or_build_mart(config, args.mart_path)
            print(json.dumps(reconcile_dashboard_view(mart), ensure_ascii=True))
            return 0

        if args.command == "phase1-g-audit-ready-report":
            mart = _load_or_build_mart(config, args.mart_path)
            output_path = Path(args.output_path) if args.output_path else default_phase1_g_audit_report_path(config)
            report = write_phase1_g_audit_ready_report(config, mart=mart, output_path=output_path)
            logger.info(
                "phase1-g-audit-ready-report "
                f"output_path={output_path} "
                f"owner_review_package={report['gate_status']['owner_review_package']}"
            )
            print(json.dumps(report, ensure_ascii=True))
            return 0

        if args.command == "product-drill-down":
            mart = _load_or_build_mart(config, args.mart_path)
            print(json.dumps(build_product_drill_down(mart, product_id=args.product_id), ensure_ascii=True))
            return 0

        if args.command == "trigger-taxonomy-review":
            source_item = _require_mapping(
                load_json(Path(args.source_item_path)),
                f"trigger-taxonomy-review:{args.source_item_path}",
            )
            result = trigger_taxonomy_review_from_source_item(
                source_item,
                config_dir=config.config_dir,
                schema_dir=config.schema_dir,
                task_store_path=config.task_store_path,
                record_path=Path(args.record_path) if args.record_path else None,
                issue_type=args.issue_type,
                priority_code=args.priority_code,
                created_at=args.created_at,
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0

        if args.command == "review-queue":
            entries = list_review_queue(
                config_dir=config.config_dir,
                task_store_path=config.task_store_path,
                open_only=args.open_only,
            )
            print(json.dumps(entries, ensure_ascii=True))
            return 0

        if args.command == "resolve-taxonomy-review":
            result = resolve_taxonomy_review_from_record_path(
                Path(args.record_path),
                config_dir=config.config_dir,
                schema_dir=config.schema_dir,
                task_store_path=config.task_store_path,
                review_issue_id=args.review_issue_id,
                resolution_action=args.resolution_action,
                resolution_notes=args.resolution_notes,
                reviewer=args.reviewer,
                reviewed_at=args.reviewed_at,
                approver=args.approver,
                approved_at=args.approved_at,
                override_category_code=args.override_category_code,
                unresolved_mode=args.unresolved_mode,
                output_path=Path(args.output_path) if args.output_path else None,
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0

        if args.command == "trigger-entity-review":
            source_item = _require_mapping(
                load_json(Path(args.source_item_path)),
                f"trigger-entity-review:{args.source_item_path}",
            )
            existing_products = _require_list(
                load_json(Path(args.existing_products_path)),
                f"trigger-entity-review:{args.existing_products_path}",
            )
            result = trigger_entity_review_from_source_item(
                source_item,
                existing_products=existing_products,
                config_dir=config.config_dir,
                schema_dir=config.schema_dir,
                task_store_path=config.task_store_path,
                priority_code=args.priority_code,
                created_at=args.created_at,
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0

        if args.command == "trigger-score-review":
            score_snapshot = _require_mapping(
                load_json(Path(args.score_snapshot_path)),
                f"trigger-score-review:{args.score_snapshot_path}",
            )
            result = trigger_score_review_from_snapshot(
                score_snapshot,
                issue_type=args.issue_type,
                config_dir=config.config_dir,
                schema_dir=config.schema_dir,
                task_store_path=config.task_store_path,
                priority_code=args.priority_code,
                created_at=args.created_at,
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0

        if args.command == "migrate":
            if not args.plan:
                raise ConfigError("Only --plan is implemented in the minimal baseline")
            print(migration_plan())
            return 0

        raise ConfigError(f"Unsupported command: {args.command}")
    except BlockedReplayError as exc:
        print(f"Replay blocked: {exc}", file=sys.stderr)
        return 3
    except (ConfigError, ContractValidationError, ObservatoryError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
