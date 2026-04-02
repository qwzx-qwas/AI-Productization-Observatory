from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from src.common.config import require_environment_variable
from src.common.errors import ConfigError, ContractValidationError
from src.common.schema import validate_instance
from tests.helpers import REPO_ROOT


FREEZE_BOARD_PATH = REPO_ROOT / "17_open_decisions_and_freeze_board.md"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _replace_gold_set_status(gold_set_dir: Path, status: str) -> None:
    readme_path = gold_set_dir / "README.md"
    content = readme_path.read_text(encoding="utf-8").replace("status = stub", f"status = {status}")
    readme_path.write_text(content, encoding="utf-8")


def _valid_gold_set_sample(sample_id: str = "sample_0001") -> dict[str, dict[str, object]]:
    evidence_refs = [{"evidence_id": "ev_1", "source_item_id": "src_item_1"}]
    review_refs = [{"review_issue_id": "review_1"}]
    source_record_refs = [{"raw_record_id": "raw_1"}]
    decision_basis_refs = [{"taxonomy_assignment_id": "tax_1"}]
    final_decision = {
        "sample_id": sample_id,
        "target_type": "product",
        "target_id": "product_1",
        "primary_category_code": "JTBD_KNOWLEDGE",
        "secondary_category_code": None,
        "primary_persona_code": "unknown",
        "delivery_form_code": "web_app",
        "build_evidence_band": "high",
        "need_clarity_band": "medium",
        "rationale": "Evidence points to document understanding and search.",
        "evidence_refs": evidence_refs,
        "adjudication_status": "adjudicated",
        "review_recommended": False,
        "review_reason": None,
        "taxonomy_change_suggestion": None,
    }
    return {
        "sample_metadata": {
            "sample_id": sample_id,
            "target_type": "product",
            "target_id": "product_1",
            "source_id": "product_hunt",
            "source_record_refs": source_record_refs,
            "review_refs": review_refs,
            "evidence_refs": evidence_refs,
            "eligibility_snapshot": {
                "review_closed": True,
                "sufficient_evidence": True,
                "clear_adjudication": True,
                "is_unresolved": False,
            },
            "pool_trace": {
                "candidate_pool_batch_id": "batch_2026_03_30",
                "training_pool_source": "candidate_pool",
                "whitelist_reason": None,
            },
        },
        "local_annotation": {
            "sample_id": sample_id,
            "annotator_channel": "local_project_user",
            "annotated_at": "2026-03-30T10:00:00Z",
            "target_type": "product",
            "target_id": "product_1",
            "primary_category_code": "JTBD_KNOWLEDGE",
            "secondary_category_code": None,
            "primary_persona_code": "unknown",
            "delivery_form_code": "web_app",
            "build_evidence_band": "high",
            "need_clarity_band": "medium",
            "rationale": "The product promise centers on finding and answering from knowledge assets.",
            "evidence_refs": evidence_refs,
            "adjudication_status": "double_annotated",
            "review_recommended": False,
            "review_reason": None,
            "taxonomy_change_suggestion": None,
            "channel_metadata": {
                "annotator_role": "local_project_user",
                "session_id": "manual_session_1",
            },
        },
        "llm_annotation": {
            "sample_id": sample_id,
            "annotator_channel": "llm",
            "annotated_at": "2026-03-30T10:01:00Z",
            "target_type": "product",
            "target_id": "product_1",
            "primary_category_code": "JTBD_KNOWLEDGE",
            "secondary_category_code": None,
            "primary_persona_code": "unknown",
            "delivery_form_code": "web_app",
            "build_evidence_band": "high",
            "need_clarity_band": "medium",
            "rationale": "The description emphasizes search and answer workflows over content generation.",
            "evidence_refs": evidence_refs,
            "adjudication_status": "double_annotated",
            "review_recommended": False,
            "review_reason": None,
            "taxonomy_change_suggestion": None,
            "channel_metadata": {
                "prompt_version": "gold_set_annotation_v1",
                "routing_version": "gold_set_route_v1",
                "provider": "test_provider",
            },
        },
        "adjudication": {
            "sample_id": sample_id,
            "adjudicated_at": "2026-03-30T10:05:00Z",
            "adjudicator_role": "local_project_user",
            "source_annotation_channels": ["local_project_user", "llm"],
            "final_decision": final_decision,
            "adjudication_rationale": "Both channels aligned on the same primary category and evidence band.",
            "review_refs": review_refs,
            "evidence_refs": evidence_refs,
            "decision_basis_refs": decision_basis_refs,
        },
    }


def _materialize_gold_set_sample(gold_set_dir: Path, sample_id: str = "sample_0001") -> None:
    payload = _valid_gold_set_sample(sample_id)
    sample_dir = gold_set_dir / "gold_set_300" / sample_id
    _write_json(sample_dir / "sample_metadata.json", payload["sample_metadata"])
    _write_json(sample_dir / "annotations" / "local_project_user.json", payload["local_annotation"])
    _write_json(sample_dir / "annotations" / "llm.json", payload["llm_annotation"])
    _write_json(sample_dir / "adjudication.json", payload["adjudication"])


def _markdown_section_lines(path: Path, heading: str) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    target_heading = f"## {heading}"
    collecting = False
    collected: list[str] = []
    for line in lines:
        if line == target_heading:
            collecting = True
            continue
        if collecting and line.startswith("## "):
            break
        if collecting and line.strip():
            collected.append(line)
    if not collected:
        raise AssertionError(f"Section not found or empty: {heading}")
    return collected


def _strip_backticks(value: str) -> str:
    if len(value) < 2 or not value.startswith("`") or not value.endswith("`"):
        raise AssertionError(f"Expected backtick-wrapped value, got: {value}")
    return value[1:-1]


def _split_inline_backtick_list(value: str) -> list[str]:
    items = []
    for raw_item in value.split(","):
        candidate = raw_item.strip()
        if candidate.startswith("`") and candidate.endswith("`"):
            candidate = candidate[1:-1]
        items.append(candidate)
    if not items or not all(items):
        raise AssertionError(f"Malformed inline list value: {value}")
    return items


def _parse_field_value(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("`") and candidate.endswith("`") and "`, `" not in candidate:
        return candidate[1:-1]
    return candidate


def _parse_signoff_line(line: str) -> dict[str, str]:
    if not line.startswith("- "):
        raise AssertionError(f"Expected bullet line, got: {line}")
    parts = line[2:].split(" / ")
    if len(parts) != 7:
        raise AssertionError(f"Malformed signoff record: {line}")
    record = {
        "date": _strip_backticks(parts[0]),
        "decision_id": _strip_backticks(parts[1]),
    }
    for item in parts[2:]:
        key, _, value = item.partition("=")
        if not key or not value:
            raise AssertionError(f"Malformed signoff field: {item}")
        record[key] = _parse_field_value(value)
    return record


def _parse_task4_checklist_line(line: str) -> dict[str, str]:
    if not line.startswith("- "):
        raise AssertionError(f"Expected bullet line, got: {line}")
    parts = line[2:].split(" / ")
    if len(parts) != 4:
        raise AssertionError(f"Malformed Task 4 checklist entry: {line}")
    record: dict[str, str] = {}
    for item in parts:
        key, _, value = item.partition("=")
        if not key or not value:
            raise AssertionError(f"Malformed Task 4 checklist field: {item}")
        record[key] = _parse_field_value(value)
    return record


class ContractCommandTests(unittest.TestCase):
    def run_cli(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=REPO_ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_cli_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("replay-window", result.stdout)
        self.assertIn("run-candidate-prescreen", result.stdout)
        self.assertIn("validate-candidate-workspace", result.stdout)

    def test_validate_schemas(self) -> None:
        result = self.run_cli("validate-schemas")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_validate_configs(self) -> None:
        result = self.run_cli("validate-configs")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_validate_gold_set_stub_contract(self) -> None:
        result = self.run_cli("validate-gold-set")
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("status=stub", result.stderr)

    def test_validate_gold_set_require_implemented_rejects_stub(self) -> None:
        result = self.run_cli("validate-gold-set", "--require-implemented")
        self.assertEqual(result.returncode, 2)
        self.assertIn("status = stub", result.stderr)

    def test_validate_gold_set_accepts_minimal_implemented_sample(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            gold_set_dir = root / "gold_set"
            shutil.copytree(REPO_ROOT / "gold_set", gold_set_dir)
            _replace_gold_set_status(gold_set_dir, "implemented")
            _materialize_gold_set_sample(gold_set_dir)

            result = self.run_cli("validate-gold-set", "--require-implemented", env={"APO_GOLD_SET_DIR": str(gold_set_dir)})
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertIn("status=implemented", result.stderr)
            self.assertIn("sample_count=1", result.stderr)

    def test_validate_gold_set_rejects_llm_channel_without_prompt_version(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            gold_set_dir = root / "gold_set"
            shutil.copytree(REPO_ROOT / "gold_set", gold_set_dir)
            _replace_gold_set_status(gold_set_dir, "implemented")
            _materialize_gold_set_sample(gold_set_dir)

            llm_annotation_path = gold_set_dir / "gold_set_300" / "sample_0001" / "annotations" / "llm.json"
            llm_annotation = json.loads(llm_annotation_path.read_text(encoding="utf-8"))
            llm_annotation["channel_metadata"].pop("prompt_version")
            llm_annotation_path.write_text(json.dumps(llm_annotation, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

            result = self.run_cli("validate-gold-set", "--require-implemented", env={"APO_GOLD_SET_DIR": str(gold_set_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("prompt_version", result.stderr)

    def test_missing_env_var_fails(self) -> None:
        result = self.run_cli("validate-env", "--require", "APO_REQUIRED_FOR_TEST")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing required environment variables", result.stderr)
        self.assertIn(".env.example", result.stderr)
        self.assertIn(".env", result.stderr)

    def test_validate_env_uses_runtime_defaults_for_known_config_paths(self) -> None:
        result = self.run_cli("validate-env", "--require", "APO_CONFIG_DIR", "APO_SCHEMA_DIR")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_validate_env_redacts_sensitive_values(self) -> None:
        result = self.run_cli(
            "validate-env",
            "--require",
            "APO_CONFIG_DIR",
            "GITHUB_TOKEN",
            env={"GITHUB_TOKEN": "your_github_token_here"},
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("GITHUB_TOKEN=[REDACTED]", result.stderr)
        self.assertNotIn("your_github_token_here", result.stderr)
        self.assertIn("APO_CONFIG_DIR=", result.stderr)

    def test_validate_env_fails_when_resolved_config_path_is_missing(self) -> None:
        missing_dir = REPO_ROOT / "does-not-exist-config-dir"
        result = self.run_cli("validate-env", "--require", "APO_CONFIG_DIR", env={"APO_CONFIG_DIR": str(missing_dir)})
        self.assertEqual(result.returncode, 2)
        self.assertIn("APO_CONFIG_DIR points to missing directory", result.stderr)

    def test_require_environment_variable_guides_local_secret_setup(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigError) as context:
                require_environment_variable("GITHUB_TOKEN")
        self.assertIn(".env.example", str(context.exception))
        self.assertIn(".env", str(context.exception))
        self.assertIn("private", str(context.exception))
        self.assertIn("Never commit real secrets", str(context.exception))

    def test_invalid_config_path_fails(self) -> None:
        missing_dir = REPO_ROOT / "does-not-exist-config-dir"
        result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(missing_dir)})
        self.assertEqual(result.returncode, 2)
        self.assertIn("APO_CONFIG_DIR points to missing directory", result.stderr)

    def test_validate_configs_rejects_taxonomy_adjacent_confusion_without_negative_example(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            taxonomy_path = config_dir / "taxonomy_v0.yaml"
            taxonomy = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
            taxonomy["adjacent_confusion_rules"][0]["example_negative"] = ""
            taxonomy_path.write_text(yaml.safe_dump(taxonomy, sort_keys=False, allow_unicode=True), encoding="utf-8")

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("example_negative", result.stderr)

    def test_validate_configs_rejects_taxonomy_long_term_l1_only_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            taxonomy_path = config_dir / "taxonomy_v0.yaml"
            taxonomy = yaml.safe_load(taxonomy_path.read_text(encoding="utf-8"))
            taxonomy["assignment_policy"]["long_term_l1_only_codes"] = ["JTBD_OTHER_VERTICAL", "JTBD_CONTENT"]
            taxonomy_path.write_text(yaml.safe_dump(taxonomy, sort_keys=False, allow_unicode=True), encoding="utf-8")

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("long_term_l1_only_codes", result.stderr)

    def test_validate_configs_rejects_review_rules_gold_set_channel_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            review_rules_path = config_dir / "review_rules_v0.yaml"
            review_rules = yaml.safe_load(review_rules_path.read_text(encoding="utf-8"))
            review_rules["annotation_contract"]["default_double_annotation_channels"] = ["llm", "llm"]
            review_rules_path.write_text(
                yaml.safe_dump(review_rules, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("default_double_annotation_channels", result.stderr)

    def test_validate_configs_rejects_taxonomy_change_suggestion_auto_writeback(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            review_rules_path = config_dir / "review_rules_v0.yaml"
            review_rules = yaml.safe_load(review_rules_path.read_text(encoding="utf-8"))
            review_rules["annotation_contract"]["taxonomy_change_suggestion"]["auto_writeback_allowed"] = True
            review_rules_path.write_text(
                yaml.safe_dump(review_rules, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("taxonomy_change_suggestion", result.stderr)

    def test_validate_configs_rejects_candidate_prescreen_action_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            workflow_path = config_dir / "candidate_prescreen_workflow.yaml"
            workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
            workflow["llm_prescreen"]["recommended_actions"] = ["reject", "hold", "candidate_pool"]
            workflow_path.write_text(yaml.safe_dump(workflow, sort_keys=False, allow_unicode=True), encoding="utf-8")

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("recommended_actions", result.stderr)

    def test_validate_configs_rejects_candidate_prescreen_note_template_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_dir = root / "configs"
            shutil.copytree(REPO_ROOT / "configs", config_dir)

            workflow_path = config_dir / "candidate_prescreen_workflow.yaml"
            workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
            workflow["workspace"]["human_review_note_templates"]["approved"] = "free-form approval note"
            workflow_path.write_text(yaml.safe_dump(workflow, sort_keys=False, allow_unicode=True), encoding="utf-8")

            result = self.run_cli("validate-configs", env={"APO_CONFIG_DIR": str(config_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("note templates", result.stderr)

    def test_validate_configs_rejects_score_schema_required_field_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            schema_dir = root / "schemas"
            shutil.copytree(REPO_ROOT / "schemas", schema_dir)

            score_schema_path = schema_dir / "score_component.schema.json"
            score_schema = yaml.safe_load(score_schema_path.read_text(encoding="utf-8"))
            score_schema["required"] = ["score_type", "rationale", "evidence_refs_json"]
            score_schema_path.write_text(
                json.dumps(score_schema, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            result = self.run_cli("validate-configs", env={"APO_SCHEMA_DIR": str(schema_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("score_component.schema.json required fields", result.stderr)

    def test_validate_configs_rejects_review_packet_issue_type_drift(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            schema_dir = root / "schemas"
            shutil.copytree(REPO_ROOT / "schemas", schema_dir)

            review_packet_path = schema_dir / "review_packet.schema.json"
            review_packet = yaml.safe_load(review_packet_path.read_text(encoding="utf-8"))
            review_packet["properties"]["issue_type"]["enum"] = ["taxonomy_conflict"]
            review_packet_path.write_text(
                json.dumps(review_packet, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            result = self.run_cli("validate-configs", env={"APO_SCHEMA_DIR": str(schema_dir)})
            self.assertEqual(result.returncode, 2)
            self.assertIn("review_packet.schema.json issue_type enum", result.stderr)

    def test_taxonomy_assignment_schema_rejects_invalid_label_role(self) -> None:
        instance = {
            "target_type": "product",
            "target_id": "prod_1",
            "taxonomy_version": "v0",
            "label_level": 1,
            "label_role": "fallback",
            "category_code": "JTBD_KNOWLEDGE",
            "rationale": "Core value is document search and answering.",
            "assigned_by": "taxonomy_classifier",
            "model_or_rule_version": "taxonomy_classifier_v1",
            "assigned_at": "2026-03-28T00:00:00Z",
            "evidence_refs_json": [{"evidence_id": "ev_1"}],
        }

        with self.assertRaises(ContractValidationError):
            validate_instance(instance, REPO_ROOT / "schemas" / "taxonomy_assignment.schema.json")

    def test_score_component_schema_accepts_explicit_nulls_for_band_only_output(self) -> None:
        instance = {
            "score_type": "build_evidence_score",
            "raw_value": None,
            "normalized_value": None,
            "band": "high",
            "rationale": "Traceable prompt demo exists.",
            "evidence_refs_json": [{"evidence_id": "ev_1"}],
        }

        validate_instance(instance, REPO_ROOT / "schemas" / "score_component.schema.json")

    def test_score_component_schema_rejects_missing_required_output_field(self) -> None:
        instance = {
            "score_type": "attention_score",
            "raw_value": 123,
            "normalized_value": 0.82,
            "rationale": "Percentile benchmark is available.",
            "evidence_refs_json": [{"observation_id": "obs_1"}],
        }

        with self.assertRaises(ContractValidationError):
            validate_instance(instance, REPO_ROOT / "schemas" / "score_component.schema.json")

    def test_score_component_schema_rejects_null_band_for_required_band_score(self) -> None:
        instance = {
            "score_type": "need_clarity_score",
            "raw_value": None,
            "normalized_value": None,
            "band": None,
            "rationale": "Band must still be produced for need_clarity_score.",
            "evidence_refs_json": [{"evidence_id": "ev_1"}],
        }

        with self.assertRaises(ContractValidationError):
            validate_instance(instance, REPO_ROOT / "schemas" / "score_component.schema.json")

    def test_score_component_schema_rejects_nonstandard_band(self) -> None:
        instance = {
            "score_type": "commercial_score",
            "raw_value": None,
            "normalized_value": None,
            "band": "critical",
            "rationale": "Unsupported band value.",
            "evidence_refs_json": [{"evidence_id": "ev_1"}],
        }

        with self.assertRaises(ContractValidationError):
            validate_instance(instance, REPO_ROOT / "schemas" / "score_component.schema.json")

    def test_review_packet_schema_rejects_unknown_issue_type(self) -> None:
        instance = {
            "target_summary": "Taxonomy conflict on product profile.",
            "issue_type": "taxonomy_override",
            "current_auto_result": {"category_code": "JTBD_CONTENT"},
            "related_evidence": [{"evidence_id": "ev_1"}],
            "conflict_point": "Evidence points to knowledge search instead of content generation.",
            "recommended_action": "mark_unresolved",
            "upstream_downstream_links": [{"taxonomy_assignment_id": "tax_1"}],
        }

        with self.assertRaises(ContractValidationError):
            validate_instance(instance, REPO_ROOT / "schemas" / "review_packet.schema.json")

    def test_review_packet_schema_accepts_traceable_review_packet(self) -> None:
        instance = {
            "target_summary": "Attention null case requires review follow-up.",
            "issue_type": "score_conflict",
            "current_auto_result": {"score_type": "attention_score", "band": None},
            "related_evidence": [{"observation_id": "obs_1"}],
            "conflict_point": "Benchmark sample is insufficient in both 30d and 90d windows.",
            "recommended_action": "needs_more_evidence",
            "upstream_downstream_links": [{"score_run_id": "score_run_1"}],
        }

        validate_instance(instance, REPO_ROOT / "schemas" / "review_packet.schema.json")

    def test_install_bootstraps_runtime_directories_and_task_store(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            result = self.run_cli(
                "install",
                env={
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                },
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((root / "raw_store").is_dir())
            self.assertTrue((root / "task_store").is_dir())
            self.assertTrue((root / "marts").is_dir())
            self.assertEqual((root / "task_store" / "tasks.json").read_text(encoding="utf-8").strip(), "[]")


class FreezeBoardSignoffContractTests(unittest.TestCase):
    def test_high_risk_signoff_records_are_complete(self) -> None:
        lines = _markdown_section_lines(FREEZE_BOARD_PATH, "2026-03-29 高风险决策签字记录")
        self.assertGreaterEqual(len(lines), 1)

        for line in lines:
            record = _parse_signoff_line(line)
            self.assertTrue(record["owner"])
            self.assertTrue(record["effective_scope"])
            self.assertIn(record["implementation_blocked"], {"yes", "no"})
            writeback_files = _split_inline_backtick_list(record["writeback_files"])
            self.assertTrue(all(writeback_files), msg=f"Empty writeback target in: {line}")

    def test_task4_writeback_checklist_covers_signed_files(self) -> None:
        signoff_lines = _markdown_section_lines(FREEZE_BOARD_PATH, "2026-03-29 高风险决策签字记录")
        checklist_lines = _markdown_section_lines(FREEZE_BOARD_PATH, "2026-03-29 Task 4 统一回写清单")

        expected_mapping: dict[str, set[str]] = {}
        known_decisions: set[str] = set()
        for line in signoff_lines:
            record = _parse_signoff_line(line)
            decision_id = record["decision_id"]
            known_decisions.add(decision_id)
            for file_path in _split_inline_backtick_list(record["writeback_files"]):
                expected_mapping.setdefault(file_path, set()).add(decision_id)

        actual_mapping: dict[str, set[str]] = {}
        allowed_actions = {
            "confirm_unchanged",
            "verify_or_update_note",
            "keep_stub_with_signed_boundary",
        }
        for line in checklist_lines:
            entry = _parse_task4_checklist_line(line)
            self.assertIn(entry["task4_action"], allowed_actions)
            self.assertTrue(entry["task4_note"])
            source_decisions = set(_split_inline_backtick_list(entry["source_decisions"]))
            self.assertTrue(source_decisions)
            self.assertTrue(source_decisions.issubset(known_decisions))
            actual_mapping[entry["file"]] = source_decisions

        self.assertEqual(actual_mapping, expected_mapping)
