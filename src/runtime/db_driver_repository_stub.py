"""Fake-bound repository seam for future DB-driver task queries.

This stub deliberately stops at SQL section lookup, bind-shape validation,
and statement capture. It does not open a database connection, name a driver
vendor, or claim that the runtime has cut over from the file-backed harness.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.common.constants import TASK_STATUSES
from src.runtime.backend_contract import TaskSnapshot
from src.runtime.db_driver_readiness import (
    POSTGRES_RUNTIME_SQL_TEMPLATE_PATH,
    RuntimeTaskDriverProtocolError,
    RuntimeTaskDriverRepositoryQueryShapeCheck,
    extract_sql_contract_section,
    verify_runtime_task_repository_query_shapes,
)
from src.runtime.models import TaskRecord


TASK_SNAPSHOT_FIELDS: tuple[str, ...] = tuple(TaskRecord.__dataclass_fields__)
TASK_SNAPSHOT_NULLABLE_FIELDS: tuple[str, ...] = (
    "source_id",
    "target_type",
    "target_id",
    "window_start",
    "window_end",
    "started_at",
    "finished_at",
    "lease_owner",
    "lease_expires_at",
    "parent_task_id",
    "last_error_type",
    "last_error_message",
)
TASK_SNAPSHOT_TIMESTAMP_FIELDS: tuple[str, ...] = (
    "window_start",
    "window_end",
    "scheduled_at",
    "available_at",
    "started_at",
    "finished_at",
    "lease_expires_at",
    "created_at",
    "updated_at",
)
TASK_SNAPSHOT_SEMANTIC_FIELDS: tuple[str, ...] = (
    "status",
    "lease_owner",
    "lease_expires_at",
    "attempt_count",
    "max_attempts",
    "last_error_type",
    "last_error_message",
)


@dataclass(frozen=True)
class RuntimeTaskDriverRowMappingReport:
    """Lossless fake result-row mapping report for the repository stub.

    The report validates a driver-shaped row dictionary before any real driver
    exists. It is a shadow/readiness harness only: no SQL is executed, no driver
    module is imported, and field names must already match TaskSnapshot.
    """

    status: str
    detail: str
    checked_field_count: int
    mapped_snapshot: TaskSnapshot | None
    expected_fields: tuple[str, ...]
    missing_fields: tuple[str, ...]
    extra_fields: tuple[str, ...]
    nullable_fields: tuple[str, ...]
    null_fields_preserved: tuple[str, ...]
    timestamp_fields: tuple[str, ...]
    semantic_fields: tuple[str, ...]
    value_mismatches: tuple[str, ...]
    status_semantic_drift: tuple[str, ...]
    misleading_rename_candidates: tuple[str, ...]
    real_db_connection: bool = False
    harness_mode: str = "fake_result_row_mapping_only"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "detail": self.detail,
            "checked_field_count": self.checked_field_count,
            "mapped_snapshot": self.mapped_snapshot,
            "expected_fields": list(self.expected_fields),
            "missing_fields": list(self.missing_fields),
            "extra_fields": list(self.extra_fields),
            "nullable_fields": list(self.nullable_fields),
            "null_fields_preserved": list(self.null_fields_preserved),
            "timestamp_fields": list(self.timestamp_fields),
            "semantic_fields": list(self.semantic_fields),
            "value_mismatches": list(self.value_mismatches),
            "status_semantic_drift": list(self.status_semantic_drift),
            "misleading_rename_candidates": list(self.misleading_rename_candidates),
            "real_db_connection": self.real_db_connection,
            "harness_mode": self.harness_mode,
        }


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

    def sample_task_snapshot_for_row_mapping(self) -> TaskSnapshot:
        """Return a fake snapshot that exercises row-shape readiness fields."""

        return {
            "task_id": "row-shape-task",
            "task_type": "pull_collect",
            "task_scope": "per_source_window",
            "source_id": "github",
            "target_type": None,
            "target_id": None,
            "window_start": "2026-04-01T00:00:00Z",
            "window_end": "2026-04-08T00:00:00Z",
            "payload_json": {
                "source_code": "github",
                "idempotent_write": True,
                "resume_checkpoint_verified": True,
            },
            "status": "leased",
            "attempt_count": 2,
            "max_attempts": 3,
            "scheduled_at": "2026-04-24T00:00:00Z",
            "available_at": "2026-04-24T00:00:00Z",
            "started_at": "2026-04-24T00:00:05Z",
            "finished_at": None,
            "lease_owner": "worker-row-shape",
            "lease_expires_at": "2026-04-24T00:00:35Z",
            "parent_task_id": None,
            "last_error_type": "timeout",
            "last_error_message": "previous technical timeout remains an error field, not review semantics",
            "created_at": "2026-04-24T00:00:00Z",
            "updated_at": "2026-04-24T00:00:10Z",
        }

    def fake_result_row_from_snapshot(self, snapshot: TaskSnapshot) -> dict[str, object]:
        """Create a fake driver result row using canonical TaskSnapshot names."""

        return {field: snapshot.get(field) for field in TASK_SNAPSHOT_FIELDS}

    def verify_result_row_mapping_readiness(self) -> RuntimeTaskDriverRowMappingReport:
        """Validate fake result-row readiness for future driver-returned rows."""

        snapshot = self.sample_task_snapshot_for_row_mapping()
        row = self.fake_result_row_from_snapshot(snapshot)
        return self.map_result_row_to_task_snapshot(row, expected_snapshot=snapshot)

    def map_result_row_to_task_snapshot(
        self,
        row: dict[str, object],
        *,
        expected_snapshot: TaskSnapshot | None = None,
    ) -> RuntimeTaskDriverRowMappingReport:
        """Validate that a fake result row maps losslessly to TaskSnapshot.

        Real driver rows may later be dictionaries, mapping-like row objects, or
        adapter-normalized records. Phase2-2 only proves the required result
        shape: stable field names, preserved nulls, text status semantics, and
        no silent field loss or rename.
        """

        row_fields = set(row)
        expected_fields = set(TASK_SNAPSHOT_FIELDS)
        missing_fields = tuple(field for field in TASK_SNAPSHOT_FIELDS if field not in row_fields)
        extra_fields = tuple(sorted(row_fields - expected_fields))
        mapped_snapshot: TaskSnapshot | None = None
        value_mismatches: tuple[str, ...] = ()
        null_fields_preserved: tuple[str, ...] = ()

        if not missing_fields:
            mapped_snapshot = {field: row[field] for field in TASK_SNAPSHOT_FIELDS}
            null_fields_preserved = tuple(
                field
                for field in TASK_SNAPSHOT_NULLABLE_FIELDS
                if field in mapped_snapshot and mapped_snapshot[field] is None
            )
            if expected_snapshot is not None:
                value_mismatches = tuple(
                    field
                    for field in TASK_SNAPSHOT_FIELDS
                    if mapped_snapshot.get(field) != expected_snapshot.get(field)
                )

        status_value = row.get("status")
        status_semantic_drift = (
            ("status",)
            if status_value is not None and str(status_value) not in TASK_STATUSES
            else ()
        )
        misleading_rename_candidates = tuple(
            sorted(
                extra
                for extra in extra_fields
                for missing in missing_fields
                if extra.replace("_", "").lower() == missing.replace("_", "").lower()
                or extra.replace("_", "").lower().endswith(missing.replace("_", "").lower())
            )
        )
        gap_count = (
            len(missing_fields)
            + len(extra_fields)
            + len(value_mismatches)
            + len(status_semantic_drift)
        )
        status = "verified" if gap_count == 0 else "row_shape_gap"
        return RuntimeTaskDriverRowMappingReport(
            status=status,
            detail=(
                "Fake result row maps losslessly back into TaskSnapshot with stable field names and preserved null semantics."
                if status == "verified"
                else "Fake result row cannot be losslessly mapped into TaskSnapshot without field loss, rename risk, or semantic drift."
            ),
            checked_field_count=len(TASK_SNAPSHOT_FIELDS),
            mapped_snapshot=mapped_snapshot,
            expected_fields=TASK_SNAPSHOT_FIELDS,
            missing_fields=missing_fields,
            extra_fields=extra_fields,
            nullable_fields=TASK_SNAPSHOT_NULLABLE_FIELDS,
            null_fields_preserved=null_fields_preserved,
            timestamp_fields=TASK_SNAPSHOT_TIMESTAMP_FIELDS,
            semantic_fields=TASK_SNAPSHOT_SEMANTIC_FIELDS,
            value_mismatches=value_mismatches,
            status_semantic_drift=status_semantic_drift,
            misleading_rename_candidates=misleading_rename_candidates,
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
