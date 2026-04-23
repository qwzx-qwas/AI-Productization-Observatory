"""Fake-bound repository seam for future DB-driver task queries.

This stub deliberately stops at SQL section lookup, bind-shape validation,
and statement capture. It does not open a database connection, name a driver
vendor, or claim that the runtime has cut over from the file-backed harness.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.runtime.db_driver_readiness import (
    POSTGRES_RUNTIME_SQL_TEMPLATE_PATH,
    RuntimeTaskDriverProtocolError,
    RuntimeTaskDriverRepositoryQueryShapeCheck,
    extract_sql_contract_section,
    verify_runtime_task_repository_query_shapes,
)


@dataclass(frozen=True)
class RuntimeTaskDriverRepositoryCall:
    """One fake-bound repository call captured by the stub executor."""

    operation: str
    contract_id: str
    sql_text: str
    binds: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "contract_id": self.contract_id,
            "sql_text": self.sql_text,
            "binds": dict(self.binds),
        }


class RuntimeTaskDriverRepositoryExecutor(Protocol):
    """Statement sink used by the repository stub during fake-bound execution."""

    def execute(
        self,
        *,
        operation: str,
        contract_id: str,
        sql_text: str,
        binds: dict[str, object],
    ) -> dict[str, object]: ...


class CaptureRuntimeTaskDriverRepositoryExecutor:
    """Records fake-bound statement calls for tests and conformance evidence."""

    def __init__(self) -> None:
        self.calls: list[RuntimeTaskDriverRepositoryCall] = []

    def execute(
        self,
        *,
        operation: str,
        contract_id: str,
        sql_text: str,
        binds: dict[str, object],
    ) -> dict[str, object]:
        call = RuntimeTaskDriverRepositoryCall(
            operation=operation,
            contract_id=contract_id,
            sql_text=sql_text,
            binds=dict(binds),
        )
        self.calls.append(call)
        return call.to_dict()


class RuntimeTaskDriverRepositoryStub:
    """Loads SQL contract sections and fake-binds repository-shaped statements."""

    _OPERATION_TO_CONTRACT = {
        "claim": "runtime_task_claim_by_id_cas",
        "claim_next": "runtime_task_claim_next_cas",
        "heartbeat": "runtime_task_heartbeat_guard",
        "reclaim_expired": "runtime_task_reclaim_expired_cas",
    }

    def __init__(
        self,
        *,
        executor: RuntimeTaskDriverRepositoryExecutor | None = None,
        sql_text: str | None = None,
        sql_path: Path | None = None,
    ) -> None:
        self._executor = executor or CaptureRuntimeTaskDriverRepositoryExecutor()
        self._sql_path = sql_path or POSTGRES_RUNTIME_SQL_TEMPLATE_PATH
        self._sql_text = sql_text

    @property
    def executor(self) -> RuntimeTaskDriverRepositoryExecutor:
        return self._executor

    def verify_query_shape_readiness(self) -> tuple[RuntimeTaskDriverRepositoryQueryShapeCheck, ...]:
        return verify_runtime_task_repository_query_shapes(
            sql_text=self._sql_text,
            sql_path=self._sql_path,
        )

    def claim(
        self,
        *,
        task_id: str,
        worker_id: str,
        current_time: str,
        lease_expires_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        return self._fake_execute(
            "claim",
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "current_time": current_time,
                "lease_expires_at": lease_expires_at,
                "updated_at": updated_at,
            },
        )

    def claim_next(
        self,
        *,
        worker_id: str,
        current_time: str,
        lease_expires_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        return self._fake_execute(
            "claim_next",
            {
                "worker_id": worker_id,
                "current_time": current_time,
                "lease_expires_at": lease_expires_at,
                "updated_at": updated_at,
            },
        )

    def heartbeat(
        self,
        *,
        task_id: str,
        worker_id: str,
        current_time: str,
        lease_expires_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        return self._fake_execute(
            "heartbeat",
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "current_time": current_time,
                "lease_expires_at": lease_expires_at,
                "updated_at": updated_at,
            },
        )

    def reclaim_expired(
        self,
        *,
        task_id: str,
        worker_id: str,
        current_time: str,
        lease_expires_at: str,
        updated_at: str,
    ) -> dict[str, object]:
        return self._fake_execute(
            "reclaim_expired",
            {
                "task_id": task_id,
                "worker_id": worker_id,
                "current_time": current_time,
                "lease_expires_at": lease_expires_at,
                "updated_at": updated_at,
            },
        )

    def _load_sql_text(self) -> str:
        if self._sql_text is not None:
            return self._sql_text
        return self._sql_path.read_text(encoding="utf-8")

    def _fake_execute(self, operation: str, binds: dict[str, object]) -> dict[str, object]:
        contract_id = self._OPERATION_TO_CONTRACT[operation]
        ready_checks = {check.contract_id: check for check in self.verify_query_shape_readiness()}
        ready_check = ready_checks[contract_id]
        if ready_check.status != "verified":
            raise RuntimeTaskDriverProtocolError(
                f"Repository query-shape gap blocks {operation}: {ready_check.missing_binds} / {ready_check.missing_semantics}"
            )

        section = extract_sql_contract_section(self._load_sql_text(), contract_id)
        if section is None:
            raise RuntimeTaskDriverProtocolError(
                f"SQL contract section is missing for repository operation {operation}: {contract_id}"
            )
        return self._executor.execute(
            operation=operation,
            contract_id=contract_id,
            sql_text=section.strip(),
            binds=binds,
        )
