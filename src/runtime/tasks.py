"""File-backed task store that mirrors the canonical runtime state machine."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from src.common.constants import (
    DEFAULT_LEASE_TIMEOUT_SECONDS,
    DEFAULT_RETRY_BASE_DELAY_SECONDS,
    DEFAULT_RETRY_MAX_DELAY_SECONDS,
    RETRY_POLICY,
    TASK_STATUSES,
    TASK_TYPES,
)
from src.common.errors import BlockedReplayError, ContractValidationError
from src.common.files import dump_json, load_json, utc_now, utc_now_iso
from src.runtime.models import TaskRecord


class FileTaskStore:
    """A deterministic local task table used for tests, replay, and CLI flows."""

    def __init__(self, store_path) -> None:
        self.store_path = store_path

    def all_tasks(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        return load_json(self.store_path)

    def _write(self, tasks: list[dict[str, Any]]) -> None:
        dump_json(self.store_path, tasks)

    def _validate_payload(self, task_type: str, payload_json: dict[str, Any]) -> None:
        if task_type not in TASK_TYPES:
            raise ContractValidationError(f"Unsupported task_type: {task_type}")
        if payload_json.get("task_type") and payload_json["task_type"] != task_type:
            raise ContractValidationError("payload_json.task_type must match task_type")

        replay_reason = payload_json.get("replay_reason")
        replay_basis = payload_json.get("replay_basis")
        if (replay_reason is None) != (replay_basis is None):
            raise ContractValidationError("Replay payload must define both replay_reason and replay_basis")

        source_code = payload_json.get("source_code")
        if replay_reason is not None and source_code == "product_hunt" and payload_json.get("window_key") != "published_at":
            raise ContractValidationError("Product Hunt replay payloads must preserve window_key = published_at")

        if replay_reason is not None and source_code == "github":
            required_fields = ("selection_rule_version", "query_slice_id")
            missing = [field for field in required_fields if not payload_json.get(field)]
            if missing:
                joined = ", ".join(missing)
                raise ContractValidationError(f"GitHub replay payload missing required fields: {joined}")

        if task_type == "build_mart_window" and payload_json.get("effective_result_policy") != "effective_resolved_only":
            raise ContractValidationError("build_mart_window payloads must declare effective_result_policy = effective_resolved_only")

    def _validate_task_snapshot(self, task: dict[str, Any]) -> None:
        if task["status"] not in TASK_STATUSES:
            raise ContractValidationError(f"Unsupported task status: {task['status']}")
        self._validate_payload(task["task_type"], task["payload_json"])

    def create_task(self, record: TaskRecord) -> TaskRecord:
        self._validate_payload(record.task_type, record.payload_json)
        tasks = self.all_tasks()
        tasks.append(record.to_dict())
        self._write(tasks)
        return record

    def update_task(self, task_id: str, **changes: Any) -> dict[str, Any]:
        tasks = self.all_tasks()
        updated: dict[str, Any] | None = None
        for task in tasks:
            if task["task_id"] == task_id:
                task.update(changes)
                task["updated_at"] = utc_now_iso()
                self._validate_task_snapshot(task)
                updated = task
                break
        if updated is None:
            raise ContractValidationError(f"Unknown task_id: {task_id}")
        self._write(tasks)
        return updated

    def latest_matching_task(
        self,
        source_id: str | None,
        task_type: str,
        window_start: str | None,
        window_end: str | None,
    ) -> dict[str, Any] | None:
        matches = [
            task
            for task in self.all_tasks()
            if task["source_id"] == source_id
            and task["task_type"] == task_type
            and task["window_start"] == window_start
            and task["window_end"] == window_end
        ]
        return matches[-1] if matches else None

    def enqueue(
        self,
        *,
        task_type: str,
        task_scope: str,
        source_id: str | None,
        target_type: str | None,
        target_id: str | None,
        window_start: str | None,
        window_end: str | None,
        payload_json: dict[str, Any],
        max_attempts: int,
        parent_task_id: str | None = None,
        status: str = "queued",
    ) -> TaskRecord:
        self._validate_payload(task_type, payload_json)
        seed = f"{task_type}:{source_id}:{window_start}:{window_end}:{utc_now_iso()}"
        task_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            task_scope=task_scope,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            window_start=window_start,
            window_end=window_end,
            payload_json=payload_json,
            status=status,
            max_attempts=max_attempts,
            parent_task_id=parent_task_id,
        )
        return self.create_task(record)

    @staticmethod
    def _is_lease_expired(task: dict[str, Any], current_iso: str) -> bool:
        expiry = task["lease_expires_at"]
        return expiry is None or expiry < current_iso

    @staticmethod
    def _can_auto_reclaim(task: dict[str, Any], current_iso: str) -> bool:
        if task["status"] not in {"leased", "running"}:
            return False
        if not FileTaskStore._is_lease_expired(task, current_iso):
            return False
        payload = task["payload_json"]
        return bool(payload.get("idempotent_write")) and bool(payload.get("resume_checkpoint_verified", True))

    def _claim_with_cas(self, task_id: str, worker_id: str, previous_updated_at: str) -> dict[str, Any] | None:
        tasks = self.all_tasks()
        now = utc_now()
        current_iso = now.isoformat().replace("+00:00", "Z")
        claimed: dict[str, Any] | None = None
        for task in tasks:
            if task["task_id"] != task_id:
                continue
            if task["updated_at"] != previous_updated_at:
                return None
            task["status"] = "leased"
            task["lease_owner"] = worker_id
            task["lease_expires_at"] = (now + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace(
                "+00:00", "Z"
            )
            task["updated_at"] = current_iso
            self._validate_task_snapshot(task)
            claimed = task
            break
        if claimed is None:
            return None
        self._write(tasks)
        return claimed

    def claim(self, task_id: str, worker_id: str) -> dict[str, Any]:
        snapshot = self.get(task_id)
        current_iso = utc_now_iso()
        available = snapshot["available_at"] <= current_iso
        claimable = snapshot["status"] in {"queued", "failed_retryable"} and available and self._is_lease_expired(snapshot, current_iso)
        reclaimable = self._can_auto_reclaim(snapshot, current_iso)
        if not claimable and not reclaimable:
            raise ContractValidationError(f"Task is not claimable: {task_id}")

        claimed = self._claim_with_cas(task_id, worker_id, snapshot["updated_at"])
        if claimed is None:
            raise ContractValidationError(f"CAS claim lost for task: {task_id}")
        return claimed

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        current_iso = utc_now_iso()
        for task in self.all_tasks():
            available = task["available_at"] <= current_iso
            claimable = task["status"] in {"queued", "failed_retryable"} and available and self._is_lease_expired(task, current_iso)
            reclaimable = self._can_auto_reclaim(task, current_iso)
            if not claimable and not reclaimable:
                continue
            claimed = self._claim_with_cas(task["task_id"], worker_id, task["updated_at"])
            if claimed is not None:
                return claimed
        return None

    def start(self, task_id: str) -> dict[str, Any]:
        task = self.get(task_id)
        if task["status"] != "leased":
            raise ContractValidationError(f"Cannot start task from status {task['status']}: {task_id}")
        return self.update_task(task_id, status="running", started_at=utc_now_iso())

    def heartbeat(self, task_id: str, worker_id: str) -> dict[str, Any]:
        task = self.get(task_id)
        if task["status"] not in {"leased", "running"}:
            raise ContractValidationError(f"Cannot heartbeat task outside leased/running states: {task_id}")
        if task["lease_owner"] != worker_id:
            raise ContractValidationError(f"Cannot heartbeat task owned by another worker: {task_id}")
        if task["lease_expires_at"] and task["lease_expires_at"] < utc_now_iso():
            raise ContractValidationError(f"Cannot heartbeat expired lease: {task_id}")
        new_expiry = (utc_now() + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace("+00:00", "Z")
        return self.update_task(task_id, lease_expires_at=new_expiry)

    def succeed(self, task_id: str) -> dict[str, Any]:
        return self.update_task(task_id, status="succeeded", finished_at=utc_now_iso(), lease_owner=None, lease_expires_at=None)

    def _next_retry_time(self, attempt_count: int) -> str:
        delay_seconds = min(DEFAULT_RETRY_BASE_DELAY_SECONDS * (2 ** max(attempt_count - 1, 0)), DEFAULT_RETRY_MAX_DELAY_SECONDS)
        return (utc_now() + timedelta(seconds=delay_seconds)).isoformat().replace("+00:00", "Z")

    def fail(self, task_id: str, error_type: str, message: str) -> dict[str, Any]:
        task = self.get(task_id)
        attempt_count = int(task["attempt_count"]) + 1
        policy = RETRY_POLICY.get(error_type, {"retryable": False, "default_max_retries": 0})
        retryable = policy["retryable"] and attempt_count <= int(task["max_attempts"])
        status = "failed_retryable" if retryable else "failed_terminal"
        changes: dict[str, Any] = {
            "status": status,
            "attempt_count": attempt_count,
            "last_error_type": error_type,
            "last_error_message": message,
            "lease_owner": None,
            "lease_expires_at": None,
            "finished_at": utc_now_iso(),
        }
        if retryable:
            changes["available_at"] = self._next_retry_time(attempt_count)
        return self.update_task(task_id, **changes)

    def block(self, task_id: str, reason: str) -> dict[str, Any]:
        return self.update_task(
            task_id,
            status="blocked",
            last_error_type="blocked_replay",
            last_error_message=reason,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=utc_now_iso(),
        )

    def cancel(self, task_id: str, reason: str) -> dict[str, Any]:
        return self.update_task(
            task_id,
            status="cancelled",
            last_error_type="cancelled",
            last_error_message=reason,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=utc_now_iso(),
        )

    def get(self, task_id: str) -> dict[str, Any]:
        for task in self.all_tasks():
            if task["task_id"] == task_id:
                self._validate_task_snapshot(task)
                return task
        raise ContractValidationError(f"Unknown task_id: {task_id}")

    def create_replay_task(
        self,
        *,
        source_id: str | None,
        task_type: str,
        task_scope: str,
        window_start: str | None,
        window_end: str | None,
        payload_json: dict[str, Any],
        max_attempts: int,
    ) -> TaskRecord:
        self._validate_payload(task_type, payload_json)
        parent = self.latest_matching_task(source_id, task_type, window_start, window_end)
        if parent and parent["status"] == "blocked":
            blocked_task = self.enqueue(
                task_type=task_type,
                task_scope=task_scope,
                source_id=source_id,
                target_type=None,
                target_id=None,
                window_start=window_start,
                window_end=window_end,
                payload_json=payload_json,
                max_attempts=max_attempts,
                parent_task_id=parent["task_id"],
                status="blocked",
            )
            self.block(blocked_task.task_id, "Replay basis is blocked; create a smaller safe task or resolve upstream first.")
            raise BlockedReplayError(blocked_task.task_id)

        parent_task_id = parent["task_id"] if parent else None
        return self.enqueue(
            task_type=task_type,
            task_scope=task_scope,
            source_id=source_id,
            target_type=None,
            target_id=None,
            window_start=window_start,
            window_end=window_end,
            payload_json=payload_json,
            max_attempts=max_attempts,
            parent_task_id=parent_task_id,
        )
