from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

from src.common.schema import validate_instance
from src.common.errors import ContractValidationError
from tests.helpers import REPO_ROOT


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

    def test_validate_schemas(self) -> None:
        result = self.run_cli("validate-schemas")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_validate_configs(self) -> None:
        result = self.run_cli("validate-configs")
        self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_missing_env_var_fails(self) -> None:
        result = self.run_cli("validate-env", "--require", "APO_REQUIRED_FOR_TEST")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Missing required environment variables", result.stderr)

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
