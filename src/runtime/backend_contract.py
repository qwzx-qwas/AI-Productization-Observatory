"""Shared runtime task backend contract for file-backed and future DB-backed adapters."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from src.runtime.models import TaskRecord

TaskSnapshot = dict[str, Any]


@runtime_checkable
class RuntimeTaskBackend(Protocol):
    """Behavioral contract that every runtime task backend must preserve."""

    def all_tasks(self) -> list[TaskSnapshot]: ...

    def create_task(self, record: TaskRecord) -> TaskRecord: ...

    def update_task(self, task_id: str, **changes: Any) -> TaskSnapshot: ...

    def latest_matching_task(
        self,
        source_id: str | None,
        task_type: str,
        window_start: str | None,
        window_end: str | None,
    ) -> TaskSnapshot | None: ...

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
    ) -> TaskRecord: ...

    def claim(self, task_id: str, worker_id: str) -> TaskSnapshot: ...

    def claim_next(self, worker_id: str) -> TaskSnapshot | None: ...

    def start(self, task_id: str) -> TaskSnapshot: ...

    def heartbeat(self, task_id: str, worker_id: str) -> TaskSnapshot: ...

    def succeed(self, task_id: str) -> TaskSnapshot: ...

    def fail(self, task_id: str, error_type: str, message: str) -> TaskSnapshot: ...

    def block(self, task_id: str, reason: str) -> TaskSnapshot: ...

    def cancel(self, task_id: str, reason: str) -> TaskSnapshot: ...

    def get(self, task_id: str) -> TaskSnapshot: ...

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
    ) -> TaskRecord: ...
