"""Command-line entrypoints for the minimal runnable baseline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.config import AppConfig, resolve_required_settings
from src.common.errors import BlockedReplayError, ConfigError, ContractValidationError, ObservatoryError
from src.common.files import dump_json, load_json, load_yaml
from src.common.logging_utils import configure_logging, get_logger
from src.common.schema import validate_schema_document
from src.devtools.quality import format_python, lint_python, typecheck_python
from src.runtime.migrations import migration_plan
from src.runtime.replay import build_mart_window, replay_source_window


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apo-observatory", description="Minimal runnable baseline for the observatory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Bootstrap local runtime directories and dependency checks.")
    subparsers.add_parser("validate-schemas", help="Validate JSON schema documents under schemas/.")
    subparsers.add_parser("validate-configs", help="Validate YAML config artifacts and schema alignment guardrails.")

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

    replay_parser = subparsers.add_parser("replay-window", help="Replay a deterministic per-source window fixture.")
    replay_parser.add_argument("--source", required=True)
    replay_parser.add_argument("--window", required=True)

    subparsers.add_parser("build-mart-window", help="Build the default mart fixture into a local mart artifact.")

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
    return 9


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
    return "bootstrap_complete"


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

        if args.command == "validate-env":
            resolved = resolve_required_settings(config, args.require)
            resolved_summary = ", ".join(f"{name}={value}" for name, value in resolved.items())
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
            result = replay_source_window(source_code=args.source, window=args.window, config=config)
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
