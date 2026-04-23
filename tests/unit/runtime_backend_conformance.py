from __future__ import annotations

from src.common.errors import BlockedReplayError, ContractValidationError
from src.runtime.backend_contract import RuntimeTaskBackend
from src.runtime.models import default_payload
from tests.helpers import temp_config


class RuntimeTaskBackendConformanceMixin:
    """Shared behavior assertions for the local harness and future DB adapters."""

    def build_backend(self, config) -> RuntimeTaskBackend:
        raise NotImplementedError

    def test_backend_exposes_shared_runtime_contract(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            self.assertIsInstance(backend, RuntimeTaskBackend)

    def test_task_lifecycle_retryable_failure(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            claimed = backend.claim_next(worker_id="worker-a")
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["task_id"], task.task_id)
            self.assertEqual(claimed["status"], "leased")

            running = backend.start(task.task_id)
            self.assertEqual(running["status"], "running")

            heartbeat = backend.heartbeat(task.task_id, worker_id="worker-a")
            self.assertIsNotNone(heartbeat["lease_expires_at"])

            failed = backend.fail(task.task_id, "network_error", "temporary failure")
            self.assertEqual(failed["status"], "failed_retryable")
            self.assertEqual(failed["attempt_count"], 1)
            self.assertGreater(failed["available_at"], failed["finished_at"])

    def test_claim_sets_leased_state_and_owner(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            claimed = backend.claim(task.task_id, worker_id="worker-claim")
            self.assertEqual(claimed["status"], "leased")
            self.assertEqual(claimed["lease_owner"], "worker-claim")
            self.assertIsNotNone(claimed["lease_expires_at"])

    def test_claim_conflict_is_rejected_without_duplicate_side_effects(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            backend.claim(task.task_id, worker_id="worker-a")
            with self.assertRaises(ContractValidationError):
                backend.claim(task.task_id, worker_id="worker-b")

            snapshot = backend.get(task.task_id)
            self.assertEqual(snapshot["status"], "leased")
            self.assertEqual(snapshot["lease_owner"], "worker-a")
            self.assertEqual(len(backend.all_tasks()), 1)

    def test_claim_next_prefers_earliest_available_then_scheduled_task(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            later_available = backend.enqueue(
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
            same_available_later_schedule = backend.enqueue(
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
            earliest = backend.enqueue(
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

            backend.update_task(
                later_available.task_id,
                available_at="2000-01-01T00:00:10Z",
                scheduled_at="2000-01-01T00:00:00Z",
            )
            backend.update_task(
                same_available_later_schedule.task_id,
                available_at="2000-01-01T00:00:00Z",
                scheduled_at="2000-01-01T00:00:10Z",
            )
            backend.update_task(
                earliest.task_id,
                available_at="2000-01-01T00:00:00Z",
                scheduled_at="2000-01-01T00:00:00Z",
            )

            claimed = backend.claim_next(worker_id="worker-order")
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["task_id"], earliest.task_id)

    def test_claim_next_skips_active_lease_and_returns_next_eligible_task(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            active_lease = backend.enqueue(
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
            next_eligible = backend.enqueue(
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

            backend.update_task(
                active_lease.task_id,
                available_at="2000-01-01T00:00:00Z",
                scheduled_at="2000-01-01T00:00:00Z",
            )
            backend.update_task(
                next_eligible.task_id,
                available_at="2000-01-01T00:00:05Z",
                scheduled_at="2000-01-01T00:00:05Z",
            )
            backend.claim(active_lease.task_id, worker_id="worker-lock")

            claimed = backend.claim_next(worker_id="worker-next")
            self.assertIsNotNone(claimed)
            self.assertEqual(claimed["task_id"], next_eligible.task_id)
            self.assertEqual(backend.get(active_lease.task_id)["lease_owner"], "worker-lock")

    def test_heartbeat_renews_lease_before_expiry(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            claimed = backend.claim(task.task_id, worker_id="worker-a")
            renewed = backend.heartbeat(task.task_id, worker_id="worker-a")

            self.assertEqual(renewed["status"], "leased")
            self.assertEqual(renewed["lease_owner"], "worker-a")
            self.assertGreaterEqual(renewed["lease_expires_at"], claimed["lease_expires_at"])

    def test_heartbeat_rejects_expired_lease(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            backend.claim(task.task_id, worker_id="worker-a")
            backend.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            with self.assertRaises(ContractValidationError):
                backend.heartbeat(task.task_id, worker_id="worker-a")

            snapshot = backend.get(task.task_id)
            self.assertEqual(snapshot["status"], "leased")
            self.assertEqual(snapshot["lease_owner"], "worker-a")

    def test_terminal_failure_for_non_retryable_error(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            task = backend.enqueue(
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

            backend.claim_next(worker_id="worker-b")
            backend.start(task.task_id)
            failed = backend.fail(task.task_id, "json_schema_validation_failed", "contract mismatch")
            self.assertEqual(failed["status"], "failed_terminal")

    def test_expired_running_task_can_be_reclaimed_when_write_is_idempotent(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
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

            backend.claim(task.task_id, worker_id="worker-a")
            backend.start(task.task_id)
            backend.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            reclaimed = backend.claim_next(worker_id="worker-b")
            self.assertIsNotNone(reclaimed)
            self.assertEqual(reclaimed["task_id"], task.task_id)
            self.assertEqual(reclaimed["status"], "leased")
            self.assertEqual(reclaimed["lease_owner"], "worker-b")

    def test_expired_running_task_stays_unclaimed_without_idempotent_write(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            payload["idempotent_write"] = False
            task = backend.enqueue(
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

            backend.claim(task.task_id, worker_id="worker-a")
            backend.start(task.task_id)
            backend.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            self.assertIsNone(backend.claim_next(worker_id="worker-b"))

    def test_expired_running_task_stays_unclaimed_without_verified_resume_checkpoint(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            payload["resume_checkpoint_verified"] = False
            task = backend.enqueue(
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

            backend.claim(task.task_id, worker_id="worker-a")
            backend.start(task.task_id)
            backend.update_task(task.task_id, lease_expires_at="2000-01-01T00:00:00Z")

            self.assertIsNone(backend.claim_next(worker_id="worker-b"))

    def test_replay_task_requires_reason_and_basis_fields_together(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            payload["replay_reason"] = "same_window_fixture_replay"

            with self.assertRaises(ContractValidationError):
                backend.create_replay_task(
                    source_id="src_product_hunt",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=payload,
                    max_attempts=2,
                )

    def test_blocked_replay_creates_blocked_child_task(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            parent = backend.enqueue(
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
            backend.block(parent.task_id, "seed blocked replay")

            replay_payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            replay_payload["replay_reason"] = "manual_requeue"
            replay_payload["replay_basis"] = "blocked_parent"

            with self.assertRaises(BlockedReplayError):
                backend.create_replay_task(
                    source_id="src_product_hunt",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=replay_payload,
                    max_attempts=2,
                )

            blocked_child = backend.all_tasks()[-1]
            self.assertEqual(blocked_child["status"], "blocked")
            self.assertEqual(blocked_child["parent_task_id"], parent.task_id)
            self.assertEqual(blocked_child["last_error_type"], "blocked_replay")
            self.assertEqual(blocked_child["payload_json"]["replay_reason"], "manual_requeue")

    def test_blocked_replay_cannot_be_promoted_to_success(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            parent = backend.enqueue(
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
            backend.block(parent.task_id, "seed blocked replay")

            replay_payload = default_payload("product_hunt", "2026-03-01", "2026-03-08")
            replay_payload["replay_reason"] = "manual_requeue"
            replay_payload["replay_basis"] = "blocked_parent"

            with self.assertRaises(BlockedReplayError):
                backend.create_replay_task(
                    source_id="src_product_hunt",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=replay_payload,
                    max_attempts=2,
                )

            blocked_child = backend.all_tasks()[-1]
            with self.assertRaises(ContractValidationError):
                backend.succeed(blocked_child["task_id"])
            self.assertEqual(backend.get(blocked_child["task_id"])["status"], "blocked")

    def test_resume_gating_blocks_unverified_checkpoint(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            parent = backend.enqueue(
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
            backend.claim(parent.task_id, worker_id="worker-a")
            backend.start(parent.task_id)
            backend.fail(parent.task_id, "network_error", "temporary failure")

            replay_payload = default_payload("github", "2026-03-01", "2026-03-08")
            replay_payload["replay_reason"] = "resume_retryable_failure"
            replay_payload["replay_basis"] = "durable_checkpoint"
            replay_payload["selection_rule_version"] = "github_qsv1"
            replay_payload["query_slice_id"] = "qf_agent"
            replay_payload["resume_from_task_id"] = parent.task_id
            replay_payload["resume_checkpoint_verified"] = False
            replay_payload["resume_state"] = {
                "window_start": "2026-03-01",
                "window_end": "2026-03-08",
            }

            with self.assertRaises(BlockedReplayError):
                backend.create_replay_task(
                    source_id="src_github",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=replay_payload,
                    max_attempts=2,
                )

            blocked_child = backend.all_tasks()[-1]
            self.assertEqual(blocked_child["status"], "blocked")
            self.assertIn("checkpoint", blocked_child["last_error_message"])

    def test_resume_gating_blocks_window_mismatch(self) -> None:
        with temp_config() as config:
            backend = self.build_backend(config)
            parent = backend.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_github",
                target_type=None,
                target_id=None,
                window_start="2026-02-01",
                window_end="2026-02-08",
                payload_json=default_payload("github", "2026-02-01", "2026-02-08"),
                max_attempts=2,
            )
            backend.claim(parent.task_id, worker_id="worker-a")
            backend.start(parent.task_id)
            backend.fail(parent.task_id, "network_error", "temporary failure")

            replay_payload = default_payload("github", "2026-03-01", "2026-03-08")
            replay_payload["replay_reason"] = "resume_retryable_failure"
            replay_payload["replay_basis"] = "durable_checkpoint"
            replay_payload["selection_rule_version"] = "github_qsv1"
            replay_payload["query_slice_id"] = "qf_agent"
            replay_payload["resume_from_task_id"] = parent.task_id
            replay_payload["resume_state"] = {
                "window_start": "2026-02-01",
                "window_end": "2026-02-08",
            }

            with self.assertRaises(BlockedReplayError):
                backend.create_replay_task(
                    source_id="src_github",
                    task_type="pull_collect",
                    task_scope="per_source_window",
                    window_start="2026-03-01",
                    window_end="2026-03-08",
                    payload_json=replay_payload,
                    max_attempts=2,
                )

            blocked_child = backend.all_tasks()[-1]
            self.assertEqual(blocked_child["status"], "blocked")
            self.assertIn("window", blocked_child["last_error_message"])
