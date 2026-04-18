from __future__ import annotations

import unittest

from src.common.errors import BlockedReplayError
from src.runtime.models import default_payload
from src.runtime.processing_errors import FileProcessingErrorStore, default_processing_error_store_path
from src.runtime.tasks import FileTaskStore
from tests.helpers import temp_config


class ProcessingErrorStoreTests(unittest.TestCase):
    def test_retryable_failure_persists_processing_error_and_success_resolves_it(self) -> None:
        with temp_config() as config:
            task_store = FileTaskStore(config.task_store_path)
            error_store = FileProcessingErrorStore(default_processing_error_store_path(config.task_store_path))
            task = task_store.enqueue(
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

            task_store.claim(task.task_id, worker_id="worker-a")
            task_store.start(task.task_id)
            failed = task_store.fail(task.task_id, "network_error", "temporary failure")

            errors = error_store.all_errors()
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["run_id"], task.task_id)
            self.assertEqual(errors[0]["module_name"], "pull_collector")
            self.assertEqual(errors[0]["error_type"], "network_error")
            self.assertEqual(errors[0]["resolution_status"], "retry_scheduled")
            self.assertEqual(errors[0]["retry_count"], 1)
            self.assertEqual(errors[0]["next_retry_at"], failed["available_at"])

            task_store.update_task(task.task_id, available_at="2000-01-01T00:00:00Z")
            task_store.claim(task.task_id, worker_id="worker-a")
            task_store.start(task.task_id)
            task_store.succeed(task.task_id)

            resolved_errors = error_store.all_errors()
            self.assertEqual(resolved_errors[0]["resolution_status"], "resolved")
            self.assertIsNone(resolved_errors[0]["next_retry_at"])

    def test_blocked_replay_persists_blocked_processing_error(self) -> None:
        with temp_config() as config:
            task_store = FileTaskStore(config.task_store_path)
            error_store = FileProcessingErrorStore(default_processing_error_store_path(config.task_store_path))
            seed = task_store.enqueue(
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
            task_store.block(seed.task_id, "seed blocked replay")

            replay_payload = default_payload("product_hunt", "2026-03-01", "2026-03-08", task_type="pull_collect")
            replay_payload["replay_reason"] = "same_window_fixture_replay"
            replay_payload["replay_basis"] = "deterministic_fixture"

            with self.assertRaises(BlockedReplayError):
                task_store.create_replay_task(
                    source_id="src_product_hunt",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=replay_payload,
                    max_attempts=0,
                )

            errors = error_store.all_errors()
            self.assertEqual(len(errors), 2)
            self.assertEqual(errors[-1]["error_type"], "blocked_replay")
            self.assertEqual(errors[-1]["resolution_status"], "blocked")


if __name__ == "__main__":
    unittest.main()
