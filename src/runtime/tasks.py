"""File-backed task store that mirrors the canonical runtime state machine."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from src.common.constants import DEFAULT_LEASE_TIMEOUT_SECONDS, RETRY_POLICY
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

    def create_task(self, record: TaskRecord) -> TaskRecord:
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
                updated = task
                break
        if updated is None:
            raise ContractValidationError(f"Unknown task_id: {task_id}")
        self._write(tasks)
        return updated

    def latest_matching_task(self, source_id: str, task_type: str, window_start: str, window_end: str) -> dict[str, Any] | None:
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

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        tasks = self.all_tasks()
        now = utc_now()
        current_iso = utc_now_iso()
        for task in tasks:
            lease_expired = not task["lease_expires_at"] or task["lease_expires_at"] < current_iso
            available = task["available_at"] <= current_iso
            if task["status"] in {"queued", "failed_retryable"} and available and lease_expired:
                task["status"] = "leased"
                task["lease_owner"] = worker_id
                task["lease_expires_at"] = (now + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace(
                    "+00:00", "Z"
                )
                task["updated_at"] = current_iso
                self._write(tasks)
                return task
        return None

    def start(self, task_id: str) -> dict[str, Any]:
        return self.update_task(task_id, status="running", started_at=utc_now_iso())

    def heartbeat(self, task_id: str, worker_id: str) -> dict[str, Any]:
        task = self.get(task_id)
        if task["lease_owner"] != worker_id:
            raise ContractValidationError(f"Cannot heartbeat task owned by another worker: {task_id}")
        new_expiry = (utc_now() + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace("+00:00", "Z")
        return self.update_task(task_id, lease_expires_at=new_expiry)

    def succeed(self, task_id: str) -> dict[str, Any]:
        return self.update_task(task_id, status="succeeded", finished_at=utc_now_iso(), lease_owner=None, lease_expires_at=None)

    def fail(self, task_id: str, error_type: str, message: str) -> dict[str, Any]:
        task = self.get(task_id)
        attempt_count = int(task["attempt_count"]) + 1
        policy = RETRY_POLICY.get(error_type, {"retryable": False, "default_max_retries": 0})
        retryable = policy["retryable"] and attempt_count <= int(task["max_attempts"])
        status = "failed_retryable" if retryable else "failed_terminal"
        return self.update_task(
            task_id,
            status=status,
            attempt_count=attempt_count,
            last_error_type=error_type,
            last_error_message=message,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=utc_now_iso(),
        )

    def block(self, task_id: str, reason: str) -> dict[str, Any]:
        return self.update_task(
            task_id,
            status="blocked",
            last_error_type="blocked_replay",
            last_error_message=reason,
            lease_owner=None,
            lease_expires_at=None,
        )

    def get(self, task_id: str) -> dict[str, Any]:
        for task in self.all_tasks():
            if task["task_id"] == task_id:
                return task
        raise ContractValidationError(f"Unknown task_id: {task_id}")

    def create_replay_task(
        self,
        *,
        source_id: str,
        task_type: str,
        task_scope: str,
        window_start: str,
        window_end: str,
        payload_json: dict[str, Any],
        max_attempts: int,
    ) -> TaskRecord:
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
