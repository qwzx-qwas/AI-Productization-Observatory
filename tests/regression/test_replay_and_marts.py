from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from src.common.errors import BlockedReplayError, ProcessingError
from src.marts.builder import build_mart_from_fixture
from src.runtime.models import default_payload
from src.runtime.replay import build_default_mart, build_mart_window, replay_source_window
from src.runtime.tasks import FileTaskStore
from tests.helpers import REPO_ROOT, temp_config


class ReplayAndMartRegressionTests(unittest.TestCase):
    def test_parallel_cli_runs_keep_task_store_json_valid(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )

            install = subprocess.run(
                [sys.executable, "-m", "src.cli", "install"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, msg=install.stderr)

            def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, "-m", "src.cli", *args],
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )

            commands = [
                ("replay-window", "--source", "product_hunt", "--window", "2026-03-01..2026-03-08"),
                ("build-mart-window",),
                ("replay-window", "--source", "product_hunt", "--window", "2026-03-01..2026-03-08"),
                ("build-mart-window",),
            ]
            with ThreadPoolExecutor(max_workers=len(commands)) as executor:
                results = list(executor.map(lambda argv: run_cli(*argv), commands))

            for result in results:
                self.assertEqual(result.returncode, 0, msg=result.stderr)

            tasks = json.loads((root / "task_store" / "tasks.json").read_text(encoding="utf-8"))
            self.assertEqual(len(tasks), len(commands))
            self.assertCountEqual(
                [task["task_type"] for task in tasks],
                ["pull_collect", "build_mart_window", "pull_collect", "build_mart_window"],
            )

    def test_same_window_replay_creates_new_task_with_parent(self) -> None:
        with temp_config() as config:
            first = replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)
            second = replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)

            store = FileTaskStore(config.task_store_path)
            tasks = store.all_tasks()
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[1]["parent_task_id"], first["task_id"])
            self.assertEqual(second["task_id"], tasks[1]["task_id"])

    def test_blocked_replay_stays_blocked(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            blocked = store.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_product_hunt",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("product_hunt", "2026-03-01", "2026-03-08"),
                max_attempts=0,
                status="blocked",
            )
            store.block(blocked.task_id, "seed blocked replay")

            with self.assertRaises(BlockedReplayError):
                replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)

            tasks = store.all_tasks()
            self.assertEqual(tasks[-1]["status"], "blocked")

    def test_mart_builder_filters_unresolved_from_main_stats(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            self.assertEqual(categories["research_ops"], 2)
            self.assertEqual(categories["qa_automation"], 1)
            self.assertNotIn("unresolved", categories)

            attention_rows = {(row["category_code"], row["attention_band"]): row["product_count"] for row in mart["attention_distribution_30d"]}
            self.assertEqual(attention_rows[("research_ops", "high")], 1)
            self.assertEqual(attention_rows[("research_ops", "medium")], 1)
            self.assertNotIn(("qa_automation", None), attention_rows)

    def test_mart_build_replays_same_window_with_new_task(self) -> None:
        with temp_config() as config:
            first = build_mart_window(config)
            second = build_mart_window(config)

            self.assertEqual(first["mart"]["top_jtbd_products_30d"], second["mart"]["top_jtbd_products_30d"])
            self.assertEqual(first["mart"]["attention_distribution_30d"], second["mart"]["attention_distribution_30d"])

            store = FileTaskStore(config.task_store_path)
            mart_tasks = [task for task in store.all_tasks() if task["task_type"] == "build_mart_window"]
            self.assertEqual(len(mart_tasks), 2)
            self.assertEqual(mart_tasks[1]["parent_task_id"], mart_tasks[0]["task_id"])
            self.assertEqual(mart_tasks[1]["status"], "succeeded")

    def test_mart_builder_only_consumes_active_effective_results(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "marts").mkdir(parents=True, exist_ok=True)

            mart_fixture = json.loads((REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json").read_text(encoding="utf-8"))
            mart_fixture["records"].append(
                {
                    "product_id": "prod_pending",
                    "source_id": "src_product_hunt",
                    "observed_at": "2026-03-20T08:00:00Z",
                    "effective_taxonomy": {
                        "label_role": "primary",
                        "result_status": "pending_review",
                        "category_code": "research_ops",
                    },
                    "effective_scores": {"attention_band": "high"},
                }
            )
            (fixtures_dir / "marts" / "effective_results_window.json").write_text(
                json.dumps(mart_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            mart = build_mart_from_fixture(
                fixtures_dir / "marts" / "effective_results_window.json",
                REPO_ROOT / "configs" / "source_registry.yaml",
            )
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            self.assertEqual(categories["research_ops"], 2)

    def test_replay_rejects_fixture_window_mismatch(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "collector").mkdir(parents=True, exist_ok=True)

            collector_fixture = json.loads((REPO_ROOT / "fixtures" / "collector" / "product_hunt_window.json").read_text(encoding="utf-8"))
            collector_fixture["window_end"] = "2026-03-09T00:00:00Z"
            (fixtures_dir / "collector" / "product_hunt_window.json").write_text(
                json.dumps(collector_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            with temp_config(fixtures_dir=fixtures_dir) as config:
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)

                self.assertEqual(ctx.exception.error_type, "parse_failure")
                store = FileTaskStore(config.task_store_path)
                self.assertEqual(store.all_tasks()[-1]["status"], "failed_terminal")
