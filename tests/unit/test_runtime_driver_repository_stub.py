from __future__ import annotations

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
