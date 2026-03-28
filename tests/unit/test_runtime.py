from __future__ import annotations

import unittest

from src.common.errors import ContractValidationError
from src.runtime.models import default_payload
from src.runtime.tasks import FileTaskStore
from tests.helpers import temp_config


class RuntimeUnitTests(unittest.TestCase):
    def test_task_lifecycle_retryable_failure(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            task = store.enqueue(
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

            claimed = store.claim_next(worker_id="worker-a")
            self.assertEqual(claimed["task_id"], task.task_id)
            self.assertEqual(claimed["status"], "leased")

            running = store.start(task.task_id)
            self.assertEqual(running["status"], "running")

            heartbeat = store.heartbeat(task.task_id, worker_id="worker-a")
            self.assertIsNotNone(heartbeat["lease_expires_at"])

            failed = store.fail(task.task_id, "network_error", "temporary failure")
            self.assertEqual(failed["status"], "failed_retryable")
            self.assertEqual(failed["attempt_count"], 1)
            self.assertGreater(failed["available_at"], failed["finished_at"])

    def test_terminal_failure_for_non_retryable_error(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            task = store.enqueue(
                task_type="normalize_raw",
                task_scope="per_raw_record",
                source_id="src_product_hunt",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("product_hunt", "2026-03-01", "2026-03-08"),
                max_attempts=2,
            )

            store.claim_next(worker_id="worker-b")
            store.start(task.task_id)
            failed = store.fail(task.task_id, "json_schema_validation_failed", "contract mismatch")
            self.assertEqual(failed["status"], "failed_terminal")

    def test_expired_running_task_can_be_reclaimed_when_write_is_idempotent(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            task = store.enqueue(
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

            store.claim(task.task_id, worker_id="worker-a")
            store.start(task.task_id)
            store.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            reclaimed = store.claim_next(worker_id="worker-b")
            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed["task_id"], task.task_id)
            self.assertEqual(reclaimed["status"], "leased")
            self.assertEqual(reclaimed["lease_owner"], "worker-b")

    def test_expired_running_task_stays_unclaimed_without_idempotent_write(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            payload["idempotent_write"] = False
            task = store.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_product_hunt",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=payload,
                max_attempts=2,
            )

            store.claim(task.task_id, worker_id="worker-a")
            store.start(task.task_id)
            store.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            self.assertIsNone(store.claim_next(worker_id="worker-b"))

    def test_replay_task_requires_reason_and_basis_fields_together(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            payload["replay_reason"] = "same_window_fixture_replay"

            with self.assertRaises(ContractValidationError):
                store.create_replay_task(
                    source_id="src_product_hunt",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=payload,
                    max_attempts=2,
                )
