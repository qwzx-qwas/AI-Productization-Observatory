"""Shadow PostgreSQL task backend that proves parity without a live DB connection."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from src.common.errors import BlockedReplayError
from src.runtime.backend_contract import TaskSnapshot
from src.runtime.db_driver_readiness import (
    RuntimeTaskDriverAdapter,
    RuntimeTaskDriverConformanceReport,
    RuntimeTaskDriverErrorClassifier,
    RuntimeTaskDriverReadinessSnapshot,
    compare_runtime_task_snapshots,
    default_runtime_task_driver_readiness_snapshot,
)
from src.runtime.models import TaskRecord
from src.runtime.tasks import FileTaskStore


class InMemoryPostgresTaskShadowExecutor:
    """A fake PostgreSQL task table used to mirror runtime-task rows in tests."""

    def __init__(self, *, sql_contract_text: str | None = None) -> None:
        self._tasks: list[TaskSnapshot] = []
        self._sql_contract_text = sql_contract_text
        self.operation_log: list[dict[str, int | str]] = []

    def replace_runtime_tasks(self, tasks: list[TaskSnapshot]) -> None:
        self._tasks = [deepcopy(task) for task in tasks]
        self.operation_log.append(
            {
                "action": "replace_runtime_tasks",
                "task_count": len(self._tasks),
            }
        )

    def all_runtime_tasks(self) -> list[TaskSnapshot]:
        return [deepcopy(task) for task in self._tasks]

    def readiness_snapshot(self) -> RuntimeTaskDriverReadinessSnapshot:
        return default_runtime_task_driver_readiness_snapshot()

    def verify_runtime_tasks(self, expected_tasks: list[TaskSnapshot]) -> RuntimeTaskDriverConformanceReport:
        return compare_runtime_task_snapshots(
            expected_tasks=expected_tasks,
            actual_tasks=self.all_runtime_tasks(),
            readiness=self.readiness_snapshot(),
            sql_contract_text=self._sql_contract_text,
        )

    def get_task(self, task_id: str) -> TaskSnapshot | None:
        for task in self._tasks:
            if task["task_id"] == task_id:
                return deepcopy(task)
        return None


class PostgresTaskBackendShadow:
    """Shadow adapter that mirrors FileTaskStore semantics through a fake executor.

    The Phase2 goal is parity proof, not real database connectivity or cutover.
    This adapter keeps the current file-backed harness as the runnable baseline
    while exposing a DB-shaped seam that future driver-backed code can replace.
    """

    def __init__(
        self,
        store_path: str | Path,
        *,
        executor: RuntimeTaskDriverAdapter | None = None,
        error_classifier: RuntimeTaskDriverErrorClassifier | None = None,
    ) -> None:
        self._delegate = FileTaskStore(store_path)
        self._executor = executor or InMemoryPostgresTaskShadowExecutor()
        self._error_classifier = error_classifier or RuntimeTaskDriverErrorClassifier()
        self._sync_shadow()

    @property
    def executor(self) -> RuntimeTaskDriverAdapter:
        return self._executor

    def driver_readiness(self) -> dict[str, object]:
        snapshot = self._executor.readiness_snapshot()
        return snapshot.to_dict()

    def shadow_conformance(self, *, sync_before_check: bool = False) -> dict[str, object]:
        if sync_before_check:
            self._sync_shadow()
        report = self._driver_call(
            "verify_runtime_tasks",
            self._executor.verify_runtime_tasks,
            self._delegate.all_tasks(),
        )
        return report.to_dict()

    def _driver_call(self, operation: str, fn, *args):
        try:
            return fn(*args)
        except Exception as exc:  # pragma: no cover - exercised via unit tests with fake driver failures.
            raise self._error_classifier.coerce(exc, operation=operation) from exc

    def _sync_shadow(self) -> None:
        expected_tasks = self._delegate.all_tasks()
        self._driver_call("replace_runtime_tasks", self._executor.replace_runtime_tasks, expected_tasks)
        self._driver_call("verify_runtime_tasks", self._executor.verify_runtime_tasks, expected_tasks)

    def all_tasks(self) -> list[TaskSnapshot]:
        self._sync_shadow()
        return self._driver_call("all_runtime_tasks", self._executor.all_runtime_tasks)

    def create_task(self, record: TaskRecord) -> TaskRecord:
        created = self._delegate.create_task(record)
        self._sync_shadow()
        return created

    def update_task(self, task_id: str, **changes) -> TaskSnapshot:
        updated = self._delegate.update_task(task_id, **changes)
        self._sync_shadow()
        return updated

    def latest_matching_task(
        self,
        source_id: str | None,
        task_type: str,
        window_start: str | None,
        window_end: str | None,
    ) -> TaskSnapshot | None:
        self._sync_shadow()
        return self._delegate.latest_matching_task(source_id, task_type, window_start, window_end)

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
        payload_json: dict[str, object],
        max_attempts: int,
        parent_task_id: str | None = None,
        status: str = "queued",
    ) -> TaskRecord:
        record = self._delegate.enqueue(
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
        self._sync_shadow()
        return record

    def claim(self, task_id: str, worker_id: str) -> TaskSnapshot:
        claimed = self._delegate.claim(task_id, worker_id)
        self._sync_shadow()
        return claimed

    def claim_next(self, worker_id: str) -> TaskSnapshot | None:
        claimed = self._delegate.claim_next(worker_id)
        self._sync_shadow()
        return claimed

    def start(self, task_id: str) -> TaskSnapshot:
        started = self._delegate.start(task_id)
        self._sync_shadow()
        return started

    def heartbeat(self, task_id: str, worker_id: str) -> TaskSnapshot:
        heartbeat = self._delegate.heartbeat(task_id, worker_id)
        self._sync_shadow()
        return heartbeat

    def succeed(self, task_id: str) -> TaskSnapshot:
        updated = self._delegate.succeed(task_id)
        self._sync_shadow()
        return updated

    def fail(self, task_id: str, error_type: str, message: str) -> TaskSnapshot:
        updated = self._delegate.fail(task_id, error_type, message)
        self._sync_shadow()
        return updated

    def block(self, task_id: str, reason: str) -> TaskSnapshot:
        updated = self._delegate.block(task_id, reason)
        self._sync_shadow()
        return updated

    def cancel(self, task_id: str, reason: str) -> TaskSnapshot:
        updated = self._delegate.cancel(task_id, reason)
        self._sync_shadow()
        return updated

    def get(self, task_id: str) -> TaskSnapshot:
        self._sync_shadow()
        return self._delegate.get(task_id)

    def create_replay_task(
        self,
        *,
        source_id: str | None,
        task_type: str,
        task_scope: str,
        window_start: str | None,
        window_end: str | None,
        payload_json: dict[str, object],
        max_attempts: int,
    ) -> TaskRecord:
        try:
            record = self._delegate.create_replay_task(
                source_id=source_id,
                task_type=task_type,
                task_scope=task_scope,
                window_start=window_start,
                window_end=window_end,
                payload_json=payload_json,
                max_attempts=max_attempts,
            )
        except BlockedReplayError:
            self._sync_shadow()
            raise
        self._sync_shadow()
        return record
