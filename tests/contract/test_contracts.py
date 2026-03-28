from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

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
