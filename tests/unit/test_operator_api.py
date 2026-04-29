from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.common.errors import ContractValidationError
from src.marts.builder import build_mart_from_fixture
from src.review.store import FileReviewIssueStore, default_review_issue_store_path, open_taxonomy_review_record
from src.runtime.models import default_payload
from src.runtime.processing_errors import default_processing_error_store_path
from src.runtime.replay import build_default_mart
from src.runtime.tasks import FileTaskStore
from src.service.operator_api import (
    build_operator_api_contract_response,
    build_operator_api_snapshot,
    build_operator_dashboard_response,
    build_operator_product_drill_down_response,
    build_operator_review_queue_response,
    build_operator_task_inspection_response,
    dispatch_operator_read,
)
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


def _operator_write_side_paths(task_store_path: Path) -> list[Path]:
    review_store_path = default_review_issue_store_path(task_store_path)
    processing_error_store_path = default_processing_error_store_path(task_store_path)
    paths = [task_store_path, review_store_path, processing_error_store_path]
    return paths + [path.with_name(f"{path.name}.lock") for path in paths]


class OperatorApiTests(unittest.TestCase):
    def test_operator_snapshot_json_shape_contract_is_stable(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)

            snapshot = build_operator_api_snapshot(
                config=config,
                mart=mart,
                product_id="prod_001",
                request_id="shape_request",
            )

            self.assertEqual(
                set(snapshot),
                {
                    "audit",
                    "api_contract",
                    "dashboard_mart_view",
                    "product_drill_down",
                    "review_queue_view",
                    "task_inspection_view",
                    "cutover_guardrails",
                    "evidence_refs",
                },
            )
            self.assertEqual(
                set(snapshot["audit"]),
                {
                    "request_id",
                    "operation",
                    "generated_at",
                    "phase",
                    "read_only",
                    "side_effects",
                    "runtime_cutover_executed",
                    "production_db_readiness_claimed",
                    "evidence_refs",
                },
            )
            self.assertEqual(snapshot["audit"]["request_id"], "shape_request")
            self.assertTrue(snapshot["audit"]["read_only"])
            self.assertEqual(snapshot["audit"]["side_effects"], [])
            self.assertEqual(snapshot["api_contract"]["service_contract_version"], "operator_api_contract_v1")
            self.assertEqual(snapshot["api_contract"]["approved_write_operations"], [])
            self.assertIn("dashboard_mart_view", snapshot["api_contract"]["endpoint_shapes"])
            self.assertEqual(snapshot["dashboard_mart_view"]["view_type"], "dashboard_mart_view")
            self.assertIn("payload", snapshot["dashboard_mart_view"])
            self.assertIn("reconciliation", snapshot["dashboard_mart_view"])
            self.assertEqual(snapshot["product_drill_down"]["view_type"], "product_drill_down")
            self.assertEqual(snapshot["review_queue_view"]["view_type"], "review_queue_view")
            self.assertEqual(snapshot["task_inspection_view"]["view_type"], "task_inspection_view")
            guardrails = snapshot["cutover_guardrails"]
            self.assertEqual(
                set(guardrails),
                {
                    "runtime_backend_default",
                    "db_backed_runtime_default",
                    "real_db_connection",
                    "cutover_eligible",
                    "runtime_cutover_executed",
                    "production_db_readiness_claimed",
                    "runtime_cutover_readiness_claimed",
                    "pending_human_selections",
                },
            )
            self.assertFalse(guardrails["db_backed_runtime_default"])
            self.assertFalse(guardrails["real_db_connection"])
            self.assertFalse(guardrails["cutover_eligible"])
            self.assertFalse(guardrails["runtime_cutover_executed"])
            self.assertFalse(guardrails["production_db_readiness_claimed"])
            self.assertFalse(guardrails["runtime_cutover_readiness_claimed"])
            self.assertIsNone(guardrails["pending_human_selections"]["runtime_db_driver"])
            self.assertIsNone(guardrails["pending_human_selections"]["dashboard_framework"])

    def test_dispatch_operator_read_routes_existing_read_views_without_write_semantics(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
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

            dashboard = dispatch_operator_read(
                "operator_dashboard_view",
                {"request_id": "dispatch_dash"},
                config=config,
                mart=mart,
            )
            drill_down = dispatch_operator_read(
                "operator_product_drill_down",
                {"product_id": "prod_001", "request_id": "dispatch_drill"},
                mart=mart,
            )
            task_view = dispatch_operator_read(
                "operator_task_inspection",
                {"task_id": task.task_id, "request_id": "dispatch_task"},
                config=config,
            )

            self.assertEqual(dashboard["audit"]["operation"], "operator_dashboard_mart_view")
            self.assertEqual(drill_down["audit"]["operation"], "operator_product_drill_down")
            self.assertEqual(task_view["audit"]["operation"], "operator_task_inspection_view")
            self.assertFalse(dashboard["cutover_guardrails"]["runtime_cutover_executed"])
            self.assertFalse(drill_down["view"]["trace_policy"].endswith("metric_recompute_allowed"))
            self.assertEqual(task_view["view"]["tasks"][0]["task_id"], task.task_id)
            self.assertFalse(task_view["view"]["blocked_replay_bypass_allowed"])

    def test_operator_api_contract_catalog_exposes_read_capabilities_only(self) -> None:
        response = build_operator_api_contract_response(request_id="contract_req")

        self.assertEqual(response["audit"]["operation"], "operator_api_contract_catalog")
        self.assertEqual(response["audit"]["request_id"], "contract_req")
        self.assertTrue(response["audit"]["read_only"])
        self.assertEqual(response["audit"]["side_effects"], [])
        self.assertEqual(response["view"]["view_type"], "operator_api_contract_catalog")
        self.assertEqual(response["view"]["service_contract_version"], "operator_api_contract_v1")
        self.assertIsNone(response["view"]["framework_binding"])
        self.assertFalse(response["view"]["write_paths_enabled"])
        self.assertEqual(response["view"]["approved_write_operations"], [])
        self.assertIn("task_submission", response["view"]["blocked_write_operations"])
        self.assertIn("review_resolution", response["view"]["write_operations_not_available"])
        commands = {item["command"]: item for item in response["view"]["supported_read_commands"]}
        self.assertEqual(commands["operator_api_contract"]["required_context"], [])
        self.assertEqual(commands["operator_product_drill_down"]["required_params"], ["product_id"])
        self.assertEqual(commands["operator_api_snapshot"]["required_context"], ["config", "mart"])
        self.assertFalse(response["view"]["guardrails"]["runtime_cutover_executed"])
        self.assertFalse(response["cutover_guardrails"]["production_db_readiness_claimed"])

    def test_dispatch_operator_read_rejects_bad_adapter_contract_inputs(self) -> None:
        with temp_config() as config:
            mart = build_mart_from_fixture(
                config.fixtures_dir / "marts" / "effective_results_window.json",
                config.config_dir / "source_registry.yaml",
            )
            bad_calls = [
                lambda: dispatch_operator_read("", {}, config=config, mart=mart),
                lambda: dispatch_operator_read("unknown_operator_read", {}, config=config, mart=mart),
                lambda: dispatch_operator_read("operator_dashboard_view", [], mart=mart),  # type: ignore[arg-type]
                lambda: dispatch_operator_read("operator_api_snapshot", {}, mart=mart),
                lambda: dispatch_operator_read("operator_dashboard_view", {}, config=config),
                lambda: dispatch_operator_read("operator_dashboard_view", {}, mart=[]),  # type: ignore[arg-type]
                lambda: dispatch_operator_read("operator_dashboard_view", {"unexpected": True}, mart=mart),
                lambda: dispatch_operator_read("operator_review_queue", {"open_only": "yes"}, config=config),
                lambda: dispatch_operator_read("operator_product_drill_down", {"product_id": 123}, mart=mart),
                lambda: dispatch_operator_read("operator_task_inspection", {"task_store_path": 123}, config=config),
            ]

            for call in bad_calls:
                with self.assertRaises(ContractValidationError):
                    call()

    def test_dispatch_operator_read_preserves_no_cutover_guardrails_and_no_write_side_files(self) -> None:
        with temp_config() as config:
            mart = build_mart_from_fixture(
                config.fixtures_dir / "marts" / "effective_results_window.json",
                config.config_dir / "source_registry.yaml",
            )
            side_effect_paths = _operator_write_side_paths(config.task_store_path)
            commands = [
                (
                    "operator_api_contract",
                    {"request_id": "dispatch_contract"},
                    {},
                ),
                (
                    "operator_api_snapshot",
                    {"product_id": "prod_001", "request_id": "dispatch_snapshot"},
                    {"config": config, "mart": mart},
                ),
                (
                    "operator_dashboard_view",
                    {"request_id": "dispatch_dashboard"},
                    {"mart": mart},
                ),
                (
                    "operator_product_drill_down",
                    {"product_id": "prod_001", "request_id": "dispatch_product"},
                    {"mart": mart},
                ),
                (
                    "operator_review_queue",
                    {"open_only": True, "review_issue_id": "missing_review", "request_id": "dispatch_review"},
                    {"config": config},
                ),
                (
                    "operator_task_inspection",
                    {"task_id": "missing_task", "status": "queued", "request_id": "dispatch_task"},
                    {"config": config},
                ),
            ]

            for command, params, context in commands:
                response = dispatch_operator_read(command, params, **context)
                self.assertTrue(response["audit"]["read_only"])
                self.assertEqual(response["audit"]["side_effects"], [])
                self.assertEqual(response["api_contract"]["approved_write_operations"], [])
                self.assertFalse(response["api_contract"]["write_paths_enabled"])
                guardrails = response["cutover_guardrails"]
                self.assertFalse(guardrails["db_backed_runtime_default"])
                self.assertFalse(guardrails["cutover_eligible"])
                self.assertFalse(guardrails["runtime_cutover_executed"])
                self.assertFalse(guardrails["production_db_readiness_claimed"])
                self.assertFalse(guardrails["runtime_cutover_readiness_claimed"])
                self.assertIsNone(guardrails["pending_human_selections"]["runtime_db_driver"])
                self.assertIsNone(guardrails["pending_human_selections"]["dashboard_framework"])
                for path in side_effect_paths:
                    self.assertFalse(path.exists(), msg=f"{command} created {path}")

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
            self.assertEqual(snapshot["api_contract"]["service_contract_version"], "operator_api_contract_v1")
            self.assertFalse(snapshot["api_contract"]["write_paths_enabled"])
            self.assertEqual(snapshot["api_contract"]["approved_write_operations"], [])
            self.assertIn("runtime_cutover", snapshot["api_contract"]["blocked_write_operations"])
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

    def test_individual_operator_responses_keep_read_only_contracts(self) -> None:
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

            dashboard = build_operator_dashboard_response(mart=mart, request_id="dash_req")
            self.assertEqual(dashboard["audit"]["operation"], "operator_dashboard_mart_view")
            self.assertEqual(dashboard["view"]["read_model"], "mart_backed")
            self.assertFalse(dashboard["view"]["mart_first_discipline"]["business_metric_recompute_allowed"])

            drill_down = build_operator_product_drill_down_response(
                mart=mart,
                product_id="prod_003",
                request_id="drill_req",
            )
            self.assertEqual(drill_down["audit"]["operation"], "operator_product_drill_down")
            self.assertIn({"ref_type": "review_issue", "review_issue_id": "rev_003"}, drill_down["view"]["evidence_refs"])

            review = build_operator_review_queue_response(
                config=config,
                open_only=True,
                review_issue_id=opened["review_issue"]["review_issue_id"],
                request_id="review_req",
            )
            self.assertEqual(review["audit"]["operation"], "operator_review_queue_view")
            self.assertEqual(review["view"]["review_issue_id"], opened["review_issue"]["review_issue_id"])
            self.assertEqual(review["view"]["items"][0]["review_issue_id"], opened["review_issue"]["review_issue_id"])
            self.assertFalse(review["view"]["maker_checker_bypass_allowed"])

            task_view = build_operator_task_inspection_response(
                task_store_path=config.task_store_path,
                task_id=task.task_id,
                status="blocked",
                request_id="task_req",
            )
            self.assertEqual(task_view["audit"]["operation"], "operator_task_inspection_view")
            self.assertEqual(task_view["view"]["task_id"], task.task_id)
            self.assertEqual(task_view["view"]["status"], "blocked")
            blocked_items = [item for item in task_view["view"]["tasks"] if item["task_id"] == task.task_id]
            self.assertTrue(blocked_items[0]["blocked_replay"])
            self.assertFalse(task_view["cutover_guardrails"]["runtime_cutover_executed"])

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
            self.assertEqual(payload["api_contract"]["approved_write_operations"], [])
            self.assertFalse(payload["cutover_guardrails"]["cutover_eligible"])
            self.assertFalse(payload["cutover_guardrails"]["runtime_cutover_executed"])
            self.assertFalse(payload["product_drill_down"]["payload"]["main_report_included"])
            self.assertIn(
                {"ref_type": "review_issue", "review_issue_id": "rev_003"},
                payload["product_drill_down"]["evidence_refs"],
            )
            task_store_path = root / "task_store" / "tasks.json"
            self.assertFalse(task_store_path.exists())

    def test_operator_api_contract_cli_is_read_only_json_without_runtime_store_files(self) -> None:
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
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "operator-api-contract",
                    "--request-id",
                    "contract_cli",
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["audit"]["operation"], "operator_api_contract_catalog")
            self.assertEqual(payload["audit"]["request_id"], "contract_cli")
            self.assertEqual(payload["view"]["approved_write_operations"], [])
            self.assertIn("runtime_cutover", payload["view"]["blocked_write_operations"])
            self.assertFalse(payload["view"]["guardrails"]["cutover_eligible"])
            for path in _operator_write_side_paths(root / "task_store" / "tasks.json"):
                self.assertFalse(path.exists())

    def test_individual_operator_cli_views_are_read_only_json(self) -> None:
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
            commands = [
                ("operator-dashboard-view", "--request-id", "dash_cli"),
                ("operator-product-drill-down", "--product-id", "prod_003", "--request-id", "drill_cli"),
                ("operator-review-queue", "--open-only", "--review-issue-id", "missing_review", "--request-id", "review_cli"),
                ("operator-task-inspection", "--status", "blocked", "--request-id", "task_cli"),
            ]

            payloads = []
            for command in commands:
                result = subprocess.run(
                    [sys.executable, "-m", "src.cli", *command],
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, msg=result.stderr)
                payloads.append(json.loads(result.stdout))

            self.assertEqual(payloads[0]["audit"]["operation"], "operator_dashboard_mart_view")
            self.assertEqual(payloads[1]["audit"]["operation"], "operator_product_drill_down")
            self.assertEqual(payloads[2]["audit"]["operation"], "operator_review_queue_view")
            self.assertEqual(payloads[3]["audit"]["operation"], "operator_task_inspection_view")
            self.assertFalse(payloads[0]["view"]["mart_first_discipline"]["business_metric_recompute_allowed"])
            self.assertEqual(payloads[2]["view"]["review_issue_id"], "missing_review")
            self.assertEqual(payloads[3]["view"]["status"], "blocked")
            self.assertFalse(payloads[3]["view"]["blocked_replay_bypass_allowed"])
            self.assertFalse(payloads[3]["cutover_guardrails"]["production_db_readiness_claimed"])
            self.assertFalse((root / "task_store" / "tasks.json").exists())
            self.assertFalse((root / "task_store" / "tasks.json.lock").exists())

    def test_invalid_task_status_filter_fails_as_contract_error(self) -> None:
        with temp_config() as config:
            with self.assertRaises(ContractValidationError):
                build_operator_task_inspection_response(
                    task_store_path=config.task_store_path,
                    status="done",
                    request_id="bad_status",
                )

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
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", "operator-task-inspection", "--status", "done"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("Unsupported task status filter: done", result.stderr)
            self.assertFalse((root / "task_store" / "tasks.json").exists())
            self.assertFalse((root / "task_store" / "tasks.json.lock").exists())

    def test_unknown_product_drill_down_is_traceable_contract_failure_without_service_write_side_effects(self) -> None:
        with temp_config() as config:
            mart = build_mart_from_fixture(
                config.fixtures_dir / "marts" / "effective_results_window.json",
                config.config_dir / "source_registry.yaml",
            )
            with self.assertRaisesRegex(ContractValidationError, "product_id=missing_product"):
                build_operator_product_drill_down_response(
                    mart=mart,
                    product_id="missing_product",
                    request_id="missing_product_req",
                )
            self.assertFalse(config.task_store_path.exists())
            self.assertFalse(config.task_store_path.with_name(f"{config.task_store_path.name}.lock").exists())
            self.assertFalse(default_review_issue_store_path(config.task_store_path).exists())

    def test_unknown_product_operator_cli_failures_do_not_create_write_side_files(self) -> None:
        commands = [
            ("operator-product-drill-down", "--product-id", "missing_product"),
            ("operator-api-snapshot", "--product-id", "missing_product"),
        ]
        for command in commands:
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
                result = subprocess.run(
                    [sys.executable, "-m", "src.cli", *command],
                    cwd=REPO_ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    check=False,
                )

                self.assertEqual(result.returncode, 2)
                self.assertIn("product_id=missing_product", result.stderr)
                for path in _operator_write_side_paths(root / "task_store" / "tasks.json"):
                    self.assertFalse(path.exists())

    def test_malformed_operator_read_stores_fail_as_contract_errors_without_lock_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            task_store_path = root / "task_store" / "tasks.json"
            review_store_path = default_review_issue_store_path(task_store_path)
            task_store_path.parent.mkdir(parents=True)
            task_store_path.write_text("{}", encoding="utf-8")
            review_store_path.write_text("{}", encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(task_store_path),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )

            task_result = subprocess.run(
                [sys.executable, "-m", "src.cli", "operator-task-inspection"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            review_result = subprocess.run(
                [sys.executable, "-m", "src.cli", "operator-review-queue"],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(task_result.returncode, 2)
            self.assertIn("task store must contain a JSON list", task_result.stderr)
            self.assertEqual(review_result.returncode, 2)
            self.assertIn("review_issue store must contain a JSON list", review_result.stderr)
            self.assertFalse(task_store_path.with_name(f"{task_store_path.name}.lock").exists())
            self.assertFalse(review_store_path.with_name(f"{review_store_path.name}.lock").exists())
            processing_error_path = default_processing_error_store_path(task_store_path)
            self.assertFalse(processing_error_path.exists())
            self.assertFalse(processing_error_path.with_name(f"{processing_error_path.name}.lock").exists())

    def test_missing_operator_mart_path_fails_as_config_error_without_review_issue(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            missing_mart = root / "missing_mart.json"
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.cli",
                    "operator-dashboard-view",
                    "--mart-path",
                    str(missing_mart),
                ],
                cwd=REPO_ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("Mart path does not exist", result.stderr)
            self.assertFalse((root / "task_store" / "tasks.json").exists())
            self.assertFalse((root / "task_store" / "tasks.json.lock").exists())
            self.assertFalse(default_review_issue_store_path(root / "task_store" / "tasks.json").exists())


if __name__ == "__main__":
    unittest.main()
