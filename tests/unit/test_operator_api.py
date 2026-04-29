from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.review.store import FileReviewIssueStore, default_review_issue_store_path, open_taxonomy_review_record
from src.runtime.models import default_payload
from src.runtime.replay import build_default_mart
from src.runtime.tasks import FileTaskStore
from src.service.operator_api import build_operator_api_snapshot
from tests.helpers import REPO_ROOT, temp_config


def _sample_review_record() -> dict[str, object]:
    return {
        "product_id": "prod_operator",
        "source_id": "src_github",
        "source_item_id": "srcitem_operator_v1",
        "source_url": "https://example.com/operator",
        "taxonomy_assignments": [
            {
                "target_type": "product",
                "target_id": "prod_operator",
                "taxonomy_version": "v0",
                "label_level": 1,
                "label_role": "primary",
                "category_code": "JTBD_KNOWLEDGE",
                "confidence": 0.68,
                "rationale": "Auto result is low confidence.",
                "assigned_by": "taxonomy_classifier",
                "model_or_rule_version": "taxonomy_classifier_v1",
                "assigned_at": "2026-03-10T10:00:00Z",
                "is_override": False,
                "override_review_issue_id": None,
                "result_status": "active",
                "effective_from": "2026-03-10T10:00:00Z",
                "supersedes_assignment_id": None,
                "evidence_refs_json": [
                    {
                        "source_item_id": "srcitem_operator_v1",
                        "evidence_type": "job_statement",
                        "source_url": "https://example.com/operator",
                    }
                ],
            }
        ],
        "review_issues": [],
        "drill_down_refs": {
            "product_id": "prod_operator",
            "source_item_id": "srcitem_operator_v1",
            "review_issue_ids": [],
        },
    }


class OperatorApiTests(unittest.TestCase):
    def test_operator_snapshot_preserves_mart_review_task_and_cutover_boundaries(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            store = FileReviewIssueStore(default_review_issue_store_path(config.task_store_path))
            opened = open_taxonomy_review_record(
                _sample_review_record(),
                store=store,
                target_summary="Open operator taxonomy review.",
                upstream_downstream_links=[{"product_id": "prod_operator", "source_item_id": "srcitem_operator_v1"}],
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
                issue_type="taxonomy_conflict",
                priority_code="P1",
                created_at="2026-03-12T09:00:00Z",
            )

            task_store = FileTaskStore(config.task_store_path)
            task = task_store.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_github",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("github", "2026-03-01", "2026-03-08", task_type="pull_collect"),
                max_attempts=1,
                status="queued",
            )
            task_store.block(task.task_id, "blocked replay requires human confirmation")

            snapshot = build_operator_api_snapshot(
                config=config,
                mart=mart,
                product_id="prod_001",
                open_review_only=True,
                request_id="test_request_001",
            )

            self.assertEqual(snapshot["audit"]["request_id"], "test_request_001")
            self.assertEqual(snapshot["audit"]["operation"], "operator_api_snapshot")
            self.assertTrue(snapshot["audit"]["read_only"])
            self.assertEqual(snapshot["audit"]["side_effects"], [])
            self.assertFalse(snapshot["audit"]["runtime_cutover_executed"])
            self.assertFalse(snapshot["audit"]["production_db_readiness_claimed"])
            self.assertGreaterEqual(len(snapshot["audit"]["evidence_refs"]), 1)
            self.assertEqual(snapshot["api_contract"]["framework_binding"], None)
            self.assertFalse(snapshot["api_contract"]["write_paths_enabled"])
            dashboard = snapshot["dashboard_mart_view"]
            self.assertEqual(dashboard["read_model"], "mart_backed")
            self.assertFalse(dashboard["mart_first_discipline"]["business_metric_recompute_allowed"])
            self.assertTrue(dashboard["reconciliation"]["all_passed"])

            drill_down = snapshot["product_drill_down"]
            self.assertEqual(drill_down["product_id"], "prod_001")
            self.assertIn({"ref_type": "evidence", "evidence_id": "ev_prod_001_homepage"}, drill_down["evidence_refs"])

            review = snapshot["review_queue_view"]
            self.assertFalse(review["generic_success_failure_flattening_allowed"])
            self.assertFalse(review["maker_checker_bypass_allowed"])
            self.assertEqual(review["items"][0]["review_issue_id"], opened["review_issue"]["review_issue_id"])
            self.assertEqual(review["items"][0]["issue_type"], "taxonomy_conflict")
            self.assertEqual(review["items"][0]["status"], "open")
            self.assertGreaterEqual(len(review["items"][0]["evidence_refs"]), 1)

            task_view = snapshot["task_inspection_view"]
            self.assertFalse(task_view["generic_success_failure_flattening_allowed"])
            self.assertFalse(task_view["blocked_replay_bypass_allowed"])
            blocked_items = [item for item in task_view["tasks"] if item["task_id"] == task.task_id]
            self.assertEqual(blocked_items[0]["status"], "blocked")
            self.assertTrue(blocked_items[0]["blocked_replay"])
            self.assertEqual(task_view["processing_errors"][0]["resolution_status"], "blocked")

            guardrails = snapshot["cutover_guardrails"]
            self.assertFalse(guardrails["db_backed_runtime_default"])
            self.assertFalse(guardrails["cutover_eligible"])
            self.assertFalse(guardrails["runtime_cutover_executed"])
            self.assertFalse(guardrails["production_db_readiness_claimed"])
            self.assertIsNone(guardrails["pending_human_selections"]["runtime_db_driver"])
            self.assertIsNone(guardrails["pending_human_selections"]["dashboard_framework"])

    def test_operator_api_snapshot_cli_is_json_and_keeps_no_cutover_flags(self) -> None:
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

            build = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "operator-api-snapshot",
                    "--product-id",
                    "prod_003",
                    "--request-id",
                    "cli_request_001",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(build.returncode, 0, msg=build.stderr)
            payload = json.loads(build.stdout)
            self.assertEqual(payload["audit"]["request_id"], "cli_request_001")
            self.assertTrue(payload["audit"]["read_only"])
            self.assertEqual(payload["api_contract"]["status"], "service_api_contract_started")
            self.assertFalse(payload["cutover_guardrails"]["cutover_eligible"])
            self.assertFalse(payload["cutover_guardrails"]["runtime_cutover_executed"])
            self.assertFalse(payload["product_drill_down"]["payload"]["main_report_included"])
            self.assertIn(
                {"ref_type": "review_issue", "review_issue_id": "rev_003"},
                payload["product_drill_down"]["evidence_refs"],
            )
            task_store_path = root / "task_store" / "tasks.json"
            self.assertFalse(task_store_path.exists())


if __name__ == "__main__":
    unittest.main()
