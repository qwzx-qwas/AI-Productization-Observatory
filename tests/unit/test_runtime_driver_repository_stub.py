from __future__ import annotations

from datetime import datetime
import unittest

from src.runtime.db_driver_readiness import RuntimeTaskDriverProtocolError
from src.runtime.db_driver_repository_stub import (
    CaptureRuntimeTaskDriverRepositoryExecutor,
    RuntimeTaskDriverRepositoryStub,
)


class RuntimeTaskDriverRepositoryStubUnitTests(unittest.TestCase):
    def test_repository_stub_fake_binds_claim_next_without_db_connection(self) -> None:
        executor = CaptureRuntimeTaskDriverRepositoryExecutor()
        repository = RuntimeTaskDriverRepositoryStub(executor=executor)

        call = repository.claim_next(
            worker_id="worker-a",
            current_time="2026-04-23T00:00:00Z",
            lease_expires_at="2026-04-23T00:00:30Z",
            updated_at="2026-04-23T00:00:00Z",
        )

        self.assertEqual(call["operation"], "claim_next")
        self.assertEqual(call["contract_id"], "runtime_task_claim_next_cas")
        self.assertEqual(
            set(call["binds"]),
            {"worker_id", "current_time", "lease_expires_at", "updated_at"},
        )
        self.assertIn("ORDER BY available_at, scheduled_at, task_id", call["sql_text"])
        self.assertIn("FOR UPDATE SKIP LOCKED", call["sql_text"])
        self.assertEqual(len(executor.calls), 1)

    def test_repository_query_shape_readiness_covers_claim_next_and_reclaim_guards(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()

        checks = {check.contract_id: check for check in repository.verify_query_shape_readiness()}

        claim_next = checks["runtime_task_claim_next_cas"]
        self.assertEqual(claim_next.status, "verified")
        self.assertIn(
            "ordering_available_at_scheduled_at_task_id",
            claim_next.required_semantics,
        )
        self.assertIn(
            "locking_for_update_skip_locked",
            claim_next.required_semantics,
        )

        reclaim = checks["runtime_task_reclaim_expired_cas"]
        self.assertEqual(reclaim.status, "verified")
        self.assertIn(
            "payload_guard_idempotent_write",
            reclaim.required_semantics,
        )
        self.assertIn(
            "payload_guard_resume_checkpoint_verified",
            reclaim.required_semantics,
        )

    def test_repository_stub_validates_fake_result_row_mapping_to_task_snapshot(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()

        report = repository.verify_result_row_mapping_readiness()

        self.assertEqual(report.status, "verified")
        self.assertFalse(report.real_db_connection)
        self.assertEqual(report.harness_mode, "fake_result_row_mapping_only")
        self.assertIn("lease_owner", report.semantic_fields)
        self.assertIn("lease_expires_at", report.timestamp_fields)
        self.assertIn("finished_at", report.null_fields_preserved)
        self.assertEqual(report.missing_fields, ())
        self.assertEqual(report.extra_fields, ())
        self.assertEqual(report.value_mismatches, ())
        self.assertEqual(report.status_semantic_drift, ())
        self.assertEqual(report.timestamp_semantic_drift, ())
        self.assertEqual(report.nullability_drift, ())
        self.assertIsNotNone(report.mapped_snapshot)
        self.assertEqual(report.mapped_snapshot["status"], "leased")
        self.assertEqual(report.mapped_snapshot["last_error_type"], "timeout")

    def test_repository_stub_validates_driver_like_result_row_variants(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()

        reports = {
            report.row_variant: report
            for report in repository.verify_driver_like_result_row_variants()
        }

        self.assertEqual(
            set(reports),
            {
                "canonical_dict",
                "mapping_like_driver_row",
                "aware_datetime_driver_row",
                "all_nullable_fields_preserved_as_null",
            },
        )
        self.assertTrue(all(report.status == "verified" for report in reports.values()))
        self.assertIn(
            "scheduled_at",
            reports["aware_datetime_driver_row"].normalized_datetime_fields,
        )
        self.assertEqual(reports["aware_datetime_driver_row"].timestamp_semantic_drift, ())
        self.assertIn(
            "source_id",
            reports["all_nullable_fields_preserved_as_null"].null_fields_preserved,
        )
        self.assertEqual(reports["all_nullable_fields_preserved_as_null"].nullability_drift, ())

    def test_repository_stub_detects_result_row_shape_gap_and_rename_risk(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()
        snapshot = repository.sample_task_snapshot_for_row_mapping()
        row = repository.fake_result_row_from_snapshot(snapshot)
        row["taskStatus"] = row.pop("status")
        row["lease_owner"] = "stale-worker"

        report = repository.map_result_row_to_task_snapshot(row, expected_snapshot=snapshot)

        self.assertEqual(report.status, "row_shape_gap")
        self.assertIn("status", report.missing_fields)
        self.assertIn("taskStatus", report.extra_fields)
        self.assertIn("taskStatus", report.misleading_rename_candidates)
        self.assertIsNone(report.mapped_snapshot)

    def test_repository_stub_detects_result_row_status_semantic_drift(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()
        snapshot = repository.sample_task_snapshot_for_row_mapping()
        row = repository.fake_result_row_from_snapshot(snapshot)
        row["status"] = "driver_only_status"

        report = repository.map_result_row_to_task_snapshot(row, expected_snapshot=snapshot)

        self.assertEqual(report.status, "row_shape_gap")
        self.assertIn("status", report.status_semantic_drift)
        self.assertIn("status", report.value_mismatches)

    def test_repository_stub_detects_timezone_and_nullability_drift_controls(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()
        snapshot = repository.sample_task_snapshot_for_row_mapping()
        row = repository.fake_result_row_from_snapshot(snapshot)
        row["scheduled_at"] = datetime(2026, 4, 24, 0, 0, 0)
        row["task_id"] = None

        report = repository.map_result_row_to_task_snapshot(
            row,
            expected_snapshot=snapshot,
            row_variant="combined_negative_control",
        )

        self.assertEqual(report.status, "row_shape_gap")
        self.assertIn("scheduled_at", report.timestamp_semantic_drift)
        self.assertIn("task_id", report.nullability_drift)
        self.assertIn("task_id", report.value_mismatches)

    def test_repository_stub_negative_gap_controls_stay_auditable(self) -> None:
        repository = RuntimeTaskDriverRepositoryStub()

        reports = {
            report.row_variant: report
            for report in repository.verify_result_row_gap_controls()
        }

        self.assertTrue(all(report.status == "row_shape_gap" for report in reports.values()))
        self.assertIn("task_id", reports["missing_required_task_id_control"].missing_fields)
        self.assertIn("driver_row_number", reports["extra_driver_column_control"].extra_fields)
        self.assertIn("taskStatus", reports["renamed_status_control"].misleading_rename_candidates)
        self.assertIn("status", reports["status_semantic_drift_control"].status_semantic_drift)
        self.assertIn(
            "scheduled_at",
            reports["naive_timestamp_timezone_control"].timestamp_semantic_drift,
        )
        self.assertIn("task_id", reports["nullability_drift_control"].nullability_drift)
        self.assertIn("lease_owner", reports["nullability_drift_control"].nullability_drift)

    def test_repository_stub_rejects_query_shape_gap_before_fake_execution(self) -> None:
        broken_sql = """
        -- contract: runtime_task_claim_next_cas
        WITH candidate AS (
            SELECT task_id
            FROM runtime_task
            WHERE status IN ('queued', 'failed_retryable')
              AND available_at <= :current_time
              AND (lease_expires_at IS NULL OR lease_expires_at <= :current_time)
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        UPDATE runtime_task
        SET status = 'leased',
            lease_owner = :worker_id,
            lease_expires_at = :lease_expires_at
        WHERE task_id = (SELECT task_id FROM candidate)
        RETURNING task_id, status, lease_owner, lease_expires_at;
        -- end-contract: runtime_task_claim_next_cas
        """
        repository = RuntimeTaskDriverRepositoryStub(sql_text=broken_sql)

        checks = {check.contract_id: check for check in repository.verify_query_shape_readiness()}
        self.assertEqual(checks["runtime_task_claim_next_cas"].status, "repository_gap")
        self.assertIn(
            "ordering_available_at_scheduled_at_task_id",
            checks["runtime_task_claim_next_cas"].missing_semantics,
        )

        with self.assertRaises(RuntimeTaskDriverProtocolError):
            repository.claim_next(
                worker_id="worker-a",
                current_time="2026-04-23T00:00:00Z",
                lease_expires_at="2026-04-23T00:00:30Z",
                updated_at="2026-04-23T00:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
