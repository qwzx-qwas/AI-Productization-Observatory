from __future__ import annotations

import unittest

from src.common.errors import ContractValidationError, ProcessingError
from src.runtime.db_driver_readiness import (
    RuntimeTaskDriverClaimConflict,
    RuntimeTaskDriverConnectivityError,
    RuntimeTaskDriverErrorClassifier,
)
from src.runtime.db_shadow import InMemoryPostgresTaskShadowExecutor, PostgresTaskBackendShadow
from src.runtime.models import default_payload
from src.runtime.tasks import FileTaskStore
from tests.unit.runtime_backend_conformance import RuntimeTaskBackendConformanceMixin


class FileTaskStoreConformanceTests(RuntimeTaskBackendConformanceMixin, unittest.TestCase):
    def build_backend(self, config):
        return FileTaskStore(config.task_store_path)


class PostgresTaskBackendShadowConformanceTests(RuntimeTaskBackendConformanceMixin, unittest.TestCase):
    def build_backend(self, config):
        return PostgresTaskBackendShadow(
            config.task_store_path,
            executor=InMemoryPostgresTaskShadowExecutor(),
        )


class PostgresTaskBackendShadowUnitTests(unittest.TestCase):
    def test_shadow_executor_tracks_latest_task_snapshot(self) -> None:
        from tests.helpers import temp_config

        with temp_config() as config:
            executor = InMemoryPostgresTaskShadowExecutor()
            backend = PostgresTaskBackendShadow(config.task_store_path, executor=executor)

            task = backend.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_product_hunt",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("product_hunt", "2026-03-01", "2026-03-08"),
                max_attempts=2,
            )
            backend.claim(task.task_id, worker_id="worker-shadow")
            backend.start(task.task_id)
            backend.block(task.task_id, "manual approval required")

            shadow_task = executor.get_task(task.task_id)
            self.assertIsNotNone(shadow_task)
            self.assertEqual(shadow_task["status"], "blocked")
            self.assertEqual(shadow_task["last_error_type"], "blocked_replay")
            self.assertGreaterEqual(len(executor.operation_log), 4)

    def test_shadow_backend_exposes_driver_readiness_metadata(self) -> None:
        from tests.helpers import temp_config

        with temp_config() as config:
            backend = PostgresTaskBackendShadow(
                config.task_store_path,
                executor=InMemoryPostgresTaskShadowExecutor(),
            )

            readiness = backend.driver_readiness()
            self.assertEqual(readiness["adapter_mode"], "shadow_mirror_only")
            self.assertFalse(readiness["real_db_connection"])
            self.assertIn("migration_tool", readiness["pending_human_selection_fields"])
            error_codes = {item["code"] for item in readiness["error_categories"]}
            self.assertEqual(
                error_codes,
                {
                    "claim_conflict",
                    "lease_expired",
                    "driver_unavailable",
                    "driver_timeout",
                    "driver_protocol_violation",
                },
            )

    def test_shadow_backend_reports_db_side_conformance(self) -> None:
        from tests.helpers import temp_config

        with temp_config() as config:
            backend = PostgresTaskBackendShadow(
                config.task_store_path,
                executor=InMemoryPostgresTaskShadowExecutor(),
            )

            task = backend.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_github",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("github", "2026-03-01", "2026-03-08"),
                max_attempts=2,
            )
            backend.claim(task.task_id, worker_id="worker-shadow")
            backend.start(task.task_id)

            report = backend.shadow_conformance()
            self.assertEqual(report["status"], "verified")
            self.assertEqual(report["checked_task_count"], 1)
            self.assertEqual(report["mismatch_count"], 0)
            self.assertEqual(report["sql_contract_status"], "verified")
            self.assertEqual(report["sql_gap_count"], 0)
            self.assertFalse(report["cutover_eligible"])
            self.assertIn("row_snapshot_equivalence", report["checked_contracts"])
            sql_contract_ids = {item["contract_id"] for item in report["sql_contract_checks"]}
            self.assertEqual(
                sql_contract_ids,
                {
                    "runtime_task_claim_by_id_cas",
                    "runtime_task_claim_next_cas",
                    "runtime_task_heartbeat_guard",
                    "runtime_task_reclaim_expired_cas",
                },
            )

    def test_shadow_backend_detects_db_side_snapshot_drift_without_resync(self) -> None:
        from tests.helpers import temp_config

        with temp_config() as config:
            executor = InMemoryPostgresTaskShadowExecutor()
            backend = PostgresTaskBackendShadow(config.task_store_path, executor=executor)

            task = backend.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_github",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("github", "2026-03-01", "2026-03-08"),
                max_attempts=2,
            )
            drifted_rows = executor.all_runtime_tasks()
            drifted_rows[0]["status"] = "succeeded"
            executor.replace_runtime_tasks(drifted_rows)

            report = backend.shadow_conformance()
            self.assertEqual(report["status"], "drift_detected")
            self.assertEqual(report["mismatch_count"], 1)
            self.assertEqual(report["sql_contract_status"], "verified")
            self.assertEqual(report["mismatches"][0]["task_id"], task.task_id)
            self.assertEqual(report["mismatches"][0]["mismatch_type"], "row_mismatch")

    def test_shadow_backend_detects_sql_contract_gap_without_cutover(self) -> None:
        from tests.helpers import temp_config

        broken_sql = """
        -- contract: runtime_task_heartbeat_guard
        UPDATE runtime_task
        SET lease_expires_at = :lease_expires_at,
            updated_at = :updated_at
        WHERE task_id = :task_id
          AND status IN ('leased', 'running')
          AND lease_owner = :worker_id
        RETURNING task_id, status, lease_owner, lease_expires_at, updated_at;
        -- end-contract: runtime_task_heartbeat_guard
        """

        with temp_config() as config:
            backend = PostgresTaskBackendShadow(
                config.task_store_path,
                executor=InMemoryPostgresTaskShadowExecutor(sql_contract_text=broken_sql),
            )

            report = backend.shadow_conformance()
            self.assertEqual(report["status"], "drift_detected")
            self.assertEqual(report["mismatch_count"], 0)
            self.assertEqual(report["sql_contract_status"], "contract_gap")
            self.assertGreater(report["sql_gap_count"], 0)
            gap_ids = {
                item["contract_id"]
                for item in report["sql_contract_checks"]
                if item["status"] == "contract_gap"
            }
            self.assertIn("runtime_task_heartbeat_guard", gap_ids)
            self.assertIn("runtime_task_claim_by_id_cas", gap_ids)

    def test_driver_error_classifier_maps_runtime_conflicts_and_technical_failures(self) -> None:
        classifier = RuntimeTaskDriverErrorClassifier()

        conflict_error = classifier.coerce(RuntimeTaskDriverClaimConflict("lost CAS"), operation="claim")
        self.assertIsInstance(conflict_error, ContractValidationError)
        self.assertIn("claim_conflict", str(conflict_error))

        technical_error = classifier.coerce(RuntimeTaskDriverConnectivityError("db down"), operation="replace_runtime_tasks")
        self.assertIsInstance(technical_error, ProcessingError)
        self.assertEqual(technical_error.error_type, "dependency_unavailable")

    def test_shadow_backend_coerces_driver_failures_without_rewriting_runtime_semantics(self) -> None:
        from tests.helpers import temp_config

        class BrokenExecutor(InMemoryPostgresTaskShadowExecutor):
            def replace_runtime_tasks(self, tasks):
                raise RuntimeTaskDriverConnectivityError("db unavailable")

        with temp_config() as config:
            with self.assertRaises(ProcessingError) as ctx:
                PostgresTaskBackendShadow(
                    config.task_store_path,
                    executor=BrokenExecutor(),
                )

        self.assertEqual(ctx.exception.error_type, "dependency_unavailable")
