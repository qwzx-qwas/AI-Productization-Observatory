"""Command-line entrypoints for the minimal runnable baseline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.common.config import AppConfig, require_environment_variables
from src.common.errors import BlockedReplayError, ConfigError, ContractValidationError, ObservatoryError
from src.common.files import dump_json, load_yaml
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


def _load_config_mapping(config_dir: Path, file_name: str) -> dict[str, object]:
    return _require_mapping(load_yaml(config_dir / file_name), file_name)


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

    sample_pool_rules = _require_mapping(review_rules.get("sample_pool_rules"), "review_rules_v0.yaml:sample_pool_rules")
    candidate_pool = _require_mapping(sample_pool_rules.get("candidate_pool"), "review_rules_v0.yaml:candidate_pool")
    if candidate_pool.get("per_batch_top_limit") != 10:
        raise ContractValidationError("candidate_pool.per_batch_top_limit must remain 10")
    if "unresolved" not in _require_list(candidate_pool.get("exclude_effective_category_codes"), "review_rules_v0.yaml:candidate_pool:exclude_effective_category_codes"):
        raise ContractValidationError("candidate_pool must exclude unresolved")

    annotation_contract = _require_mapping(review_rules.get("annotation_contract"), "review_rules_v0.yaml:annotation_contract")
    if set(_require_list(annotation_contract.get("adjudication_statuses"), "review_rules_v0.yaml:annotation_contract:adjudication_statuses")) != {
        "single_annotated",
        "double_annotated",
        "adjudicated",
        "needs_review",
    }:
        raise ContractValidationError("annotation adjudication statuses drifted from the frozen annotation workflow")
    field_mappings = _require_mapping(annotation_contract.get("field_mappings"), "review_rules_v0.yaml:annotation_contract:field_mappings")
    if _require_mapping(field_mappings.get("build_evidence_band"), "build_evidence_band").get("score_type") != "build_evidence_score":
        raise ContractValidationError("build_evidence_band must map to build_evidence_score")
    if _require_mapping(field_mappings.get("need_clarity_band"), "need_clarity_band").get("score_type") != "need_clarity_score":
        raise ContractValidationError("need_clarity_band must map to need_clarity_score")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="apo-observatory", description="Minimal runnable baseline for the observatory.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("install", help="Bootstrap local runtime directories and dependency checks.")
    subparsers.add_parser("validate-schemas", help="Validate JSON schema documents under schemas/.")
    subparsers.add_parser("validate-configs", help="Validate YAML config artifacts under configs/.")

    env_parser = subparsers.add_parser("validate-env", help="Fail when required environment variables are missing.")
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
    return 6


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
            require_environment_variables(args.require)
            logger.info(f"validated env vars: {', '.join(args.require)}")
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
