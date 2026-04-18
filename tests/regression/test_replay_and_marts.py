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
from src.review.review_packet_builder import apply_taxonomy_review_resolution
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

    def test_github_same_window_replay_keeps_parent_link_and_slice_metadata(self) -> None:
        with temp_config() as config:
            first = replay_source_window(source_code="github", window="2026-03-01..2026-03-08", config=config)
            second = replay_source_window(source_code="github", window="2026-03-01..2026-03-08", config=config)

            store = FileTaskStore(config.task_store_path)
            tasks = [task for task in store.all_tasks() if task["source_id"] == "src_github"]
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[1]["parent_task_id"], first["task_id"])
            self.assertEqual(tasks[1]["payload_json"]["selection_rule_version"], "github_qsv1")
            self.assertEqual(tasks[1]["payload_json"]["query_slice_id"], "qf_agent")
            self.assertEqual(second["crawl_run"]["watermark_after"]["time_field"], "pushed_at")

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
            self.assertEqual(categories["JTBD_KNOWLEDGE_RESEARCH"], 2)
            self.assertEqual(categories["JTBD_DEV_TOOLS_TESTING"], 1)
            self.assertNotIn("unresolved", categories)

            attention_rows = {(row["category_code"], row["attention_band"]): row["product_count"] for row in mart["attention_distribution_30d"]}
            self.assertEqual(attention_rows[("JTBD_KNOWLEDGE_RESEARCH", "high")], 1)
            self.assertEqual(attention_rows[("JTBD_KNOWLEDGE_RESEARCH", "medium")], 1)
            self.assertNotIn(("JTBD_DEV_TOOLS_TESTING", None), attention_rows)

            unresolved_rows = {row["review_issue_id"]: row for row in mart["unresolved_registry_view"]}
            self.assertEqual(len(unresolved_rows), 1)
            self.assertTrue(unresolved_rows["rev_003"]["is_effective_unresolved"])
            self.assertFalse(unresolved_rows["rev_003"]["is_stale"])

    def test_mart_builder_emits_fact_dimensions_and_dashboard_contract(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)

            facts = {row["product_id"]: row for row in mart["fact_product_observation"]}
            self.assertCountEqual(facts, ["prod_001", "prod_002", "prod_004"])
            self.assertEqual(facts["prod_001"]["taxonomy_primary_code"], "JTBD_KNOWLEDGE_RESEARCH")
            self.assertEqual(facts["prod_004"]["taxonomy_primary_code"], "JTBD_DEV_TOOLS_TESTING")
            self.assertEqual(facts["prod_002"]["attention_metric_definition_version"], "attention_metric_v1")
            self.assertEqual(facts["prod_002"]["attention_formula_version"], "attention_v1")
            self.assertEqual(facts["prod_001"]["metric_version"], "source_metric_registry_v4")

            products = {row["product_id"]: row for row in mart["dim_product"]}
            self.assertEqual(products["prod_001"]["current_primary_persona_code"], "researcher")
            self.assertEqual(products["prod_004"]["current_delivery_form_code"], "web_app")
            self.assertTrue(products["prod_003"]["is_unresolved"])

            sources = {row["source_id"]: row for row in mart["dim_source"]}
            self.assertEqual(sources["src_github"]["source_name"], "GitHub")
            self.assertTrue(sources["src_product_hunt"]["enabled"])

            taxonomy = {row["category_code"]: row for row in mart["dim_taxonomy"]}
            self.assertEqual(taxonomy["JTBD_KNOWLEDGE_RESEARCH"]["parent_code"], "JTBD_KNOWLEDGE")
            self.assertEqual(taxonomy["JTBD_DEV_TOOLS_TESTING"]["parent_code"], "JTBD_DEV_TOOLS")

            personas = {row["code"]: row for row in mart["dim_persona"]}
            self.assertEqual(personas["researcher"]["label"], "Researcher / 研究人员")
            self.assertTrue(personas["unknown"]["is_unknown"])

            delivery_forms = {row["code"]: row for row in mart["dim_delivery_form"]}
            self.assertEqual(delivery_forms["web_app"]["label"], "Web App / Web 应用")

            dashboard_contract = mart["dashboard_read_contract"]
            self.assertEqual(dashboard_contract["main_report_dataset"], "fact_product_observation")
            self.assertEqual(dashboard_contract["main_report_semantics"], "effective resolved taxonomy")
            self.assertFalse(dashboard_contract["runtime_detail_join_allowed"])

    def test_drill_down_trace_covers_main_report_and_unresolved_paths(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            trace = {row["product_id"]: row for row in mart["drill_down_trace"]}

            self.assertEqual(trace["prod_001"]["path_type"], "source_to_main_mart")
            self.assertTrue(trace["prod_001"]["main_report_included"])
            self.assertEqual(trace["prod_001"]["evidence_ids"], ["ev_prod_001_homepage", "ev_prod_001_description"])

            self.assertEqual(trace["prod_003"]["path_type"], "effective_unresolved_registry")
            self.assertFalse(trace["prod_003"]["main_report_included"])
            self.assertTrue(trace["prod_003"]["unresolved_registry_required"])
            self.assertEqual(trace["prod_003"]["review_issue_ids"], ["rev_003"])

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

    def test_dashboard_reconciliation_and_drill_down_cli_follow_mart_outputs(self) -> None:
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

            build = subprocess.run(
                [sys.executable, "-m", "src.cli", "build-mart-window"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(build.returncode, 0, msg=build.stderr)

            mart_path = root / "marts" / "mart_window.json"
            reconciliation = subprocess.run(
                [sys.executable, "-m", "src.cli", "dashboard-reconciliation", "--mart-path", str(mart_path)],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(reconciliation.returncode, 0, msg=reconciliation.stderr)
            reconciliation_payload = json.loads(reconciliation.stdout)
            self.assertTrue(reconciliation_payload["all_passed"])
            self.assertEqual(reconciliation_payload["pass_rate"], 1.0)

            drill_down = subprocess.run(
                [sys.executable, "-m", "src.cli", "product-drill-down", "--mart-path", str(mart_path), "--product-id", "prod_003"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(drill_down.returncode, 0, msg=drill_down.stderr)
            drill_down_payload = json.loads(drill_down.stdout)
            self.assertFalse(drill_down_payload["main_report_included"])
            self.assertEqual(drill_down_payload["effective_taxonomy_code"], "unresolved")
            self.assertEqual(drill_down_payload["trace_refs"]["review_issue_ids"], ["rev_003"])

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
                        "category_code": "JTBD_KNOWLEDGE_RESEARCH",
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
            self.assertEqual(categories["JTBD_KNOWLEDGE_RESEARCH"], 2)

    def test_mart_builder_prefers_canonical_taxonomy_assignments_over_prebaked_effective_taxonomy(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "marts").mkdir(parents=True, exist_ok=True)

            mart_fixture = json.loads((REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json").read_text(encoding="utf-8"))
            mart_fixture["records"][2]["effective_taxonomy"]["category_code"] = "JTBD_KNOWLEDGE_RESEARCH"
            (fixtures_dir / "marts" / "effective_results_window.json").write_text(
                json.dumps(mart_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            mart = build_mart_from_fixture(
                fixtures_dir / "marts" / "effective_results_window.json",
                REPO_ROOT / "configs" / "source_registry.yaml",
            )
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            unresolved_rows = {row["review_issue_id"]: row for row in mart["unresolved_registry_view"]}

            self.assertEqual(categories["JTBD_KNOWLEDGE_RESEARCH"], 2)
            self.assertNotIn("unresolved", categories)
            self.assertTrue(unresolved_rows["rev_003"]["is_effective_unresolved"])

    def test_taxonomy_writeback_resolution_flows_into_effective_mart_outputs(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "marts").mkdir(parents=True, exist_ok=True)

            mart_fixture = json.loads((REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json").read_text(encoding="utf-8"))
            applied = apply_taxonomy_review_resolution(
                mart_fixture["records"][0],
                target_summary="Research ops sample resolved to unresolved after human review",
                upstream_downstream_links=[{"product_id": "prod_001", "source_item_id": "srcitem_ph_1001_v1"}],
                resolution_action="mark_unresolved",
                resolution_notes="Human review could not defend a stable primary taxonomy.",
                reviewer="local_project_user",
                reviewed_at="2026-03-18T09:00:00Z",
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
                issue_type="taxonomy_conflict",
                priority_code="P1",
            )
            mart_fixture["records"][0] = applied["record"]
            (fixtures_dir / "marts" / "effective_results_window.json").write_text(
                json.dumps(mart_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            mart = build_mart_from_fixture(
                fixtures_dir / "marts" / "effective_results_window.json",
                REPO_ROOT / "configs" / "source_registry.yaml",
            )
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            unresolved_rows = {row["review_issue_id"]: row for row in mart["unresolved_registry_view"]}

            self.assertEqual(categories["JTBD_KNOWLEDGE_RESEARCH"], 1)
            self.assertNotIn("unresolved", categories)
            self.assertTrue(unresolved_rows[applied["review_issue"]["review_issue_id"]]["is_effective_unresolved"])

    def test_review_only_unresolved_stays_in_main_stats_but_appears_in_registry(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "marts").mkdir(parents=True, exist_ok=True)

            mart_fixture = json.loads((REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json").read_text(encoding="utf-8"))
            applied = apply_taxonomy_review_resolution(
                mart_fixture["records"][0],
                target_summary="Research ops sample remains review-only unresolved",
                upstream_downstream_links=[{"product_id": "prod_001", "source_item_id": "srcitem_ph_1001_v1"}],
                resolution_action="mark_unresolved",
                resolution_notes="Human review keeps the issue in backlog without overriding the auto result.",
                reviewer="local_project_user",
                reviewed_at="2026-03-18T09:00:00Z",
                unresolved_mode="review_only_unresolved",
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
                issue_type="taxonomy_conflict",
                priority_code="P2",
            )
            mart_fixture["records"][0] = applied["record"]
            (fixtures_dir / "marts" / "effective_results_window.json").write_text(
                json.dumps(mart_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            mart = build_mart_from_fixture(
                fixtures_dir / "marts" / "effective_results_window.json",
                REPO_ROOT / "configs" / "source_registry.yaml",
            )
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            unresolved_rows = {row["review_issue_id"]: row for row in mart["unresolved_registry_view"]}

            self.assertEqual(categories["JTBD_KNOWLEDGE_RESEARCH"], 2)
            self.assertFalse(unresolved_rows[applied["review_issue"]["review_issue_id"]]["is_effective_unresolved"])

    def test_consumption_contract_examples_match_fixture_records(self) -> None:
        examples = json.loads((REPO_ROOT / "fixtures" / "marts" / "consumption_contract_examples.json").read_text(encoding="utf-8"))
        mart_fixture = json.loads((REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json").read_text(encoding="utf-8"))
        expected_source_items = json.loads(
            (REPO_ROOT / "fixtures" / "normalizer" / "product_hunt_expected_source_items.json").read_text(encoding="utf-8")
        )

        fixture_records = {record["product_id"]: record for record in mart_fixture["records"]}
        source_items = {item["external_id"]: item for item in expected_source_items}
        built_mart = build_mart_from_fixture(
            REPO_ROOT / "fixtures" / "marts" / "effective_results_window.json",
            REPO_ROOT / "configs" / "source_registry.yaml",
        )
        main_mart_categories = {row["category_code"] for row in built_mart["top_jtbd_products_30d"]}
        attention_distribution = {(row["category_code"], row["attention_band"]) for row in built_mart["attention_distribution_30d"]}

        for example in examples["examples"]:
            record = fixture_records[example["product_id"]]
            expected_outcome = example["expected_outcome"]
            self.assertIn(Path(example["effective_result_fixture"]).name, {"effective_results_window.json"})
            self.assertIn(
                "tests/regression/test_replay_and_marts.py::test_consumption_contract_examples_match_fixture_records",
                example["test_refs"],
            )

            if example["path_type"] == "source_to_main_mart":
                source_item = source_items[example["source_item_external_id"]]
                self.assertEqual(record["source_external_id"], source_item["external_id"])
                self.assertEqual(record["source_id"], source_item["source_id"])
                self.assertTrue(expected_outcome["main_report_included"])
                self.assertIn(expected_outcome["main_mart_category_code"], main_mart_categories)
                self.assertIn("drill_down_refs", record)
                self.assertEqual(record["drill_down_refs"]["source_item_id"], record["source_item_id"])
                self.assertEqual(record["drill_down_refs"]["product_id"], record["product_id"])
                if expected_outcome["attention_band"] is None:
                    self.assertNotIn((record["effective_taxonomy"]["category_code"], None), attention_distribution)
                else:
                    self.assertIn(
                        (record["effective_taxonomy"]["category_code"], expected_outcome["attention_band"]),
                        attention_distribution,
                    )
            elif example["path_type"] == "effective_unresolved_registry":
                self.assertEqual(record["effective_taxonomy"]["category_code"], "unresolved")
                self.assertFalse(expected_outcome["main_report_included"])
                self.assertNotIn("unresolved", main_mart_categories)
                registry_entry = record["unresolved_registry_entry"]
                self.assertEqual(registry_entry["target_id"], record["product_id"])
                self.assertTrue(registry_entry["is_effective_unresolved"])
                self.assertEqual(record["drill_down_refs"]["review_issue_ids"], [registry_entry["review_issue_id"]])
            else:
                self.fail(f"Unknown path_type in consumption contract examples fixture: {example['path_type']}")

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
