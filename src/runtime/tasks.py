"""File-backed task store that mirrors the canonical runtime state machine."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path
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
from src.common.files import dump_json, ensure_parent, load_json, utc_now, utc_now_iso
from src.runtime.models import TaskRecord
from src.runtime.processing_errors import FileProcessingErrorStore, default_processing_error_store_path

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class FileTaskStore:
    """A deterministic local task table used for tests, replay, and CLI flows."""

    def __init__(self, store_path) -> None:
        self.store_path = Path(store_path)

    @property
    def lock_path(self) -> Path:
        return self.store_path.with_name(f"{self.store_path.name}.lock")

    @property
    def processing_error_store(self) -> FileProcessingErrorStore:
        return FileProcessingErrorStore(default_processing_error_store_path(self.store_path))

    @contextmanager
    def _exclusive_lock(self):
        ensure_parent(self.lock_path)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load_tasks_unlocked(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        try:
            payload = load_json(self.store_path)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"Task store is not valid JSON: {self.store_path}") from exc
        if not isinstance(payload, list):
            raise ContractValidationError(f"Task store must contain a JSON list: {self.store_path}")
        return payload

    def all_tasks(self) -> list[dict[str, Any]]:
        with self._exclusive_lock():
            return self._load_tasks_unlocked()

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

    def _get_from_tasks(self, tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any]:
        for task in tasks:
            if task["task_id"] == task_id:
                self._validate_task_snapshot(task)
                return task
        raise ContractValidationError(f"Unknown task_id: {task_id}")

    def _update_in_tasks(self, tasks: list[dict[str, Any]], task_id: str, **changes: Any) -> dict[str, Any]:
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
        return updated

    def _latest_matching_task_from_tasks(
        self,
        tasks: list[dict[str, Any]],
        source_id: str | None,
        task_type: str,
        window_start: str | None,
        window_end: str | None,
    ) -> dict[str, Any] | None:
        matches = [
            task
            for task in tasks
            if task["source_id"] == source_id
            and task["task_type"] == task_type
            and task["window_start"] == window_start
            and task["window_end"] == window_end
        ]
        return matches[-1] if matches else None

    def _enqueue_in_tasks(
        self,
        tasks: list[dict[str, Any]],
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
        tasks.append(record.to_dict())
        return record

    def create_task(self, record: TaskRecord) -> TaskRecord:
        self._validate_payload(record.task_type, record.payload_json)
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            tasks.append(record.to_dict())
            self._write(tasks)
        return record

    def update_task(self, task_id: str, **changes: Any) -> dict[str, Any]:
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            updated = self._update_in_tasks(tasks, task_id, **changes)
            self._write(tasks)
            return updated

    def latest_matching_task(
        self,
        source_id: str | None,
        task_type: str,
        window_start: str | None,
        window_end: str | None,
    ) -> dict[str, Any] | None:
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            return self._latest_matching_task_from_tasks(tasks, source_id, task_type, window_start, window_end)

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
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            record = self._enqueue_in_tasks(
                tasks,
                task_type=task_type,
                task_scope=task_scope,
                source_id=source_id,
                target_type=target_type,
                target_id=target_id,
                window_start=window_start,
                window_end=window_end,
                payload_json=payload_json,
                max_attempts=max_attempts,
                parent_task_id=parent_task_id,
                status=status,
            )
            self._write(tasks)
            return record

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

    def claim(self, task_id: str, worker_id: str) -> dict[str, Any]:
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            snapshot = self._get_from_tasks(tasks, task_id)
            current_iso = utc_now_iso()
            available = snapshot["available_at"] <= current_iso
            claimable = (
                snapshot["status"] in {"queued", "failed_retryable"}
                and available
                and self._is_lease_expired(snapshot, current_iso)
            )
            reclaimable = self._can_auto_reclaim(snapshot, current_iso)
            if not claimable and not reclaimable:
                raise ContractValidationError(f"Task is not claimable: {task_id}")

            now = utc_now()
            snapshot["status"] = "leased"
            snapshot["lease_owner"] = worker_id
            snapshot["lease_expires_at"] = (now + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace(
                "+00:00", "Z"
            )
            snapshot["updated_at"] = now.isoformat().replace("+00:00", "Z")
            self._validate_task_snapshot(snapshot)
            self._write(tasks)
            return snapshot

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            current_iso = utc_now_iso()
            for task in tasks:
                available = task["available_at"] <= current_iso
                claimable = (
                    task["status"] in {"queued", "failed_retryable"}
                    and available
                    and self._is_lease_expired(task, current_iso)
                )
                reclaimable = self._can_auto_reclaim(task, current_iso)
                if not claimable and not reclaimable:
                    continue

                now = utc_now()
                task["status"] = "leased"
                task["lease_owner"] = worker_id
                task["lease_expires_at"] = (now + timedelta(seconds=DEFAULT_LEASE_TIMEOUT_SECONDS)).isoformat().replace(
                    "+00:00", "Z"
                )
                task["updated_at"] = now.isoformat().replace("+00:00", "Z")
                self._validate_task_snapshot(task)
                self._write(tasks)
                return task
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
        updated = self.update_task(task_id, status="succeeded", finished_at=utc_now_iso(), lease_owner=None, lease_expires_at=None)
        self.processing_error_store.resolve_for_task(updated, resolved_at=updated["finished_at"])
        return updated

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
        updated = self.update_task(task_id, **changes)
        self.processing_error_store.record_failure(
            updated,
            error_type=error_type,
            error_message=message,
            retry_count=attempt_count,
            resolution_status="retry_scheduled" if retryable else "open",
            failed_at=updated["finished_at"],
            next_retry_at=updated.get("available_at") if retryable else None,
        )
        return updated

    def block(self, task_id: str, reason: str) -> dict[str, Any]:
        updated = self.update_task(
            task_id,
            status="blocked",
            last_error_type="blocked_replay",
            last_error_message=reason,
            lease_owner=None,
            lease_expires_at=None,
            finished_at=utc_now_iso(),
        )
        self.processing_error_store.record_failure(
            updated,
            error_type="blocked_replay",
            error_message=reason,
            retry_count=int(updated["attempt_count"]),
            resolution_status="blocked",
            failed_at=updated["finished_at"],
            next_retry_at=None,
        )
        return updated

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
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            return self._get_from_tasks(tasks, task_id)

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
        with self._exclusive_lock():
            tasks = self._load_tasks_unlocked()
            parent = self._latest_matching_task_from_tasks(tasks, source_id, task_type, window_start, window_end)
            if parent and parent["status"] == "blocked":
                blocked_task = self._enqueue_in_tasks(
                    tasks,
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
                blocked_snapshot = self._update_in_tasks(
                    tasks,
                    blocked_task.task_id,
                    last_error_type="blocked_replay",
                    last_error_message="Replay basis is blocked; create a smaller safe task or resolve upstream first.",
                    finished_at=utc_now_iso(),
                    lease_owner=None,
                    lease_expires_at=None,
                )
                blocked_snapshot["status"] = "blocked"
                self._validate_task_snapshot(blocked_snapshot)
                self._write(tasks)
                self.processing_error_store.record_failure(
                    blocked_snapshot,
                    error_type="blocked_replay",
                    error_message=blocked_snapshot["last_error_message"],
                    retry_count=int(blocked_snapshot["attempt_count"]),
                    resolution_status="blocked",
                    failed_at=blocked_snapshot["finished_at"],
                    next_retry_at=None,
                )
                raise BlockedReplayError(blocked_task.task_id)

            record = self._enqueue_in_tasks(
                tasks,
                task_type=task_type,
                task_scope=task_scope,
                source_id=source_id,
                target_type=None,
                target_id=None,
                window_start=window_start,
                window_end=window_end,
                payload_json=payload_json,
                max_attempts=max_attempts,
                parent_task_id=parent["task_id"] if parent else None,
            )
            self._write(tasks)
            return record
