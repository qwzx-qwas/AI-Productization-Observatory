"""Replaceable DB-driver readiness seam for runtime task backends.

This layer keeps DB-driver concerns deliberately narrow in Phase2:
future driver work should implement an adapter and reuse the existing
claim/lease/replay state semantics instead of re-deriving them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Protocol, runtime_checkable

from src.common.errors import ContractValidationError, ProcessingError
from src.runtime.backend_contract import TaskSnapshot

POSTGRES_RUNTIME_SQL_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "sql" / "postgresql_task_runtime_phase2_1.sql"
)


class RuntimeTaskDriverAdapterError(Exception):
    """Base class for driver-adapter readiness failures."""


class RuntimeTaskDriverClaimConflict(RuntimeTaskDriverAdapterError):
    """Raised when a DB compare-and-swap claim loses an existing lease owner."""


class RuntimeTaskDriverLeaseExpired(RuntimeTaskDriverAdapterError):
    """Raised when a heartbeat or write targets an expired lease."""


class RuntimeTaskDriverConnectivityError(RuntimeTaskDriverAdapterError):
    """Raised when the driver cannot reach the backing database service."""


class RuntimeTaskDriverTimeout(RuntimeTaskDriverAdapterError):
    """Raised when the driver times out before a DB operation completes."""


class RuntimeTaskDriverProtocolError(RuntimeTaskDriverAdapterError):
    """Raised when an adapter violates the runtime-task row contract."""


@dataclass(frozen=True)
class RuntimeTaskDriverErrorCategory:
    """Canonical error mapping for future driver-backed runtime adapters."""

    code: str
    canonical_error_type: str
    retryable: bool
    boundary: str
    resolution_hint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "canonical_error_type": self.canonical_error_type,
            "retryable": self.retryable,
            "boundary": self.boundary,
            "resolution_hint": self.resolution_hint,
        }


@dataclass(frozen=True)
class RuntimeTaskDriverReadinessSnapshot:
    """Machine-readable readiness metadata for the current DB-driver seam."""

    adapter_contract: str
    adapter_mode: str
    semantics_owner: str
    real_db_connection: bool
    shadow_sync_strategy: str
    pending_human_selection_fields: tuple[str, ...]
    error_categories: tuple[RuntimeTaskDriverErrorCategory, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "adapter_contract": self.adapter_contract,
            "adapter_mode": self.adapter_mode,
            "semantics_owner": self.semantics_owner,
            "real_db_connection": self.real_db_connection,
            "shadow_sync_strategy": self.shadow_sync_strategy,
            "pending_human_selection_fields": list(self.pending_human_selection_fields),
            "error_categories": [category.to_dict() for category in self.error_categories],
        }


@dataclass(frozen=True)
class RuntimeTaskDriverConformanceMismatch:
    """A single row-level drift finding between runtime and DB-shadow state."""

    task_id: str
    mismatch_type: str
    detail: str
    expected: TaskSnapshot | None
    actual: TaskSnapshot | None

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "mismatch_type": self.mismatch_type,
            "detail": self.detail,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class RuntimeTaskDriverSqlContractCheck:
    """Result of validating one SQL contract template section."""

    contract_id: str
    status: str
    detail: str
    required_fragments: tuple[str, ...]
    missing_fragments: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "status": self.status,
            "detail": self.detail,
            "required_fragments": list(self.required_fragments),
            "missing_fragments": list(self.missing_fragments),
        }


@dataclass(frozen=True)
class RuntimeTaskDriverRepositoryQueryShapeCheck:
    """Result of validating one fake-bound repository query shape."""

    contract_id: str
    operation: str
    status: str
    detail: str
    expected_binds: tuple[str, ...]
    missing_binds: tuple[str, ...]
    required_semantics: tuple[str, ...]
    missing_semantics: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_id": self.contract_id,
            "operation": self.operation,
            "status": self.status,
            "detail": self.detail,
            "expected_binds": list(self.expected_binds),
            "missing_binds": list(self.missing_binds),
            "required_semantics": list(self.required_semantics),
            "missing_semantics": list(self.missing_semantics),
        }


@dataclass(frozen=True)
class RuntimeTaskDriverConformanceReport:
    """DB-side behavior parity report for the shadow runtime adapter."""

    status: str
    adapter_mode: str
    real_db_connection: bool
    checked_task_count: int
    row_conformance_status: str
    mismatch_count: int
    sql_contract_status: str
    sql_gap_count: int
    repository_query_shape_status: str
    repository_gap_count: int
    checked_contracts: tuple[str, ...]
    cutover_eligible: bool
    mismatches: tuple[RuntimeTaskDriverConformanceMismatch, ...]
    sql_contract_checks: tuple[RuntimeTaskDriverSqlContractCheck, ...]
    repository_query_shape_checks: tuple[RuntimeTaskDriverRepositoryQueryShapeCheck, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "adapter_mode": self.adapter_mode,
            "real_db_connection": self.real_db_connection,
            "checked_task_count": self.checked_task_count,
            "row_conformance_status": self.row_conformance_status,
            "mismatch_count": self.mismatch_count,
            "sql_contract_status": self.sql_contract_status,
            "sql_gap_count": self.sql_gap_count,
            "repository_query_shape_status": self.repository_query_shape_status,
            "repository_gap_count": self.repository_gap_count,
            "checked_contracts": list(self.checked_contracts),
            "cutover_eligible": self.cutover_eligible,
            "mismatches": [mismatch.to_dict() for mismatch in self.mismatches],
            "sql_contract_checks": [check.to_dict() for check in self.sql_contract_checks],
            "repository_query_shape_checks": [
                check.to_dict() for check in self.repository_query_shape_checks
            ],
        }


@runtime_checkable
class RuntimeTaskDriverAdapter(Protocol):
    """Persistence-facing adapter that a future real DB driver can implement."""

    def replace_runtime_tasks(self, tasks: list[TaskSnapshot]) -> None: ...

    def all_runtime_tasks(self) -> list[TaskSnapshot]: ...

    def readiness_snapshot(self) -> RuntimeTaskDriverReadinessSnapshot: ...

    def verify_runtime_tasks(self, expected_tasks: list[TaskSnapshot]) -> RuntimeTaskDriverConformanceReport: ...


class RuntimeTaskDriverErrorClassifier:
    """Maps adapter exceptions to canonical runtime failure categories."""

    def __init__(self) -> None:
        self._categories = {
            "claim_conflict": RuntimeTaskDriverErrorCategory(
                code="claim_conflict",
                canonical_error_type="claim_conflict",
                retryable=False,
                boundary="runtime_state_semantics",
                resolution_hint="Refresh the current lease owner and retry claim only after lease expiry or manual requeue.",
            ),
            "lease_expired": RuntimeTaskDriverErrorCategory(
                code="lease_expired",
                canonical_error_type="lease_expired",
                retryable=False,
                boundary="runtime_state_semantics",
                resolution_hint="Do not extend or write through an expired lease; reclaim only through the CAS-safe resume path.",
            ),
            "driver_unavailable": RuntimeTaskDriverErrorCategory(
                code="driver_unavailable",
                canonical_error_type="dependency_unavailable",
                retryable=True,
                boundary="processing_error_retry_policy",
                resolution_hint="Treat connectivity loss as a retryable technical dependency outage.",
            ),
            "driver_timeout": RuntimeTaskDriverErrorCategory(
                code="driver_timeout",
                canonical_error_type="timeout",
                retryable=True,
                boundary="processing_error_retry_policy",
                resolution_hint="Treat slow or stalled DB operations as retryable technical timeouts.",
            ),
            "driver_protocol_violation": RuntimeTaskDriverErrorCategory(
                code="driver_protocol_violation",
                canonical_error_type="driver_protocol_violation",
                retryable=False,
                boundary="runtime_contract_guardrail",
                resolution_hint="Fix the adapter or row-shape mapping before retrying; do not fold protocol drift into review logic.",
            ),
        }

    def categories(self) -> tuple[RuntimeTaskDriverErrorCategory, ...]:
        return tuple(self._categories.values())

    def classify(self, exc: Exception) -> RuntimeTaskDriverErrorCategory:
        if isinstance(exc, RuntimeTaskDriverClaimConflict):
            return self._categories["claim_conflict"]
        if isinstance(exc, RuntimeTaskDriverLeaseExpired):
            return self._categories["lease_expired"]
        if isinstance(exc, (RuntimeTaskDriverTimeout, TimeoutError)):
            return self._categories["driver_timeout"]
        if isinstance(exc, (RuntimeTaskDriverConnectivityError, ConnectionError, OSError)):
            return self._categories["driver_unavailable"]
        return self._categories["driver_protocol_violation"]

    def coerce(self, exc: Exception, *, operation: str) -> Exception:
        category = self.classify(exc)
        message = (
            f"Runtime DB driver {operation} failed with {category.code}: "
            f"{category.resolution_hint}"
        )
        if category.retryable:
            return ProcessingError(category.canonical_error_type, message)
        return ContractValidationError(message)


def default_runtime_task_driver_readiness_snapshot() -> RuntimeTaskDriverReadinessSnapshot:
    """Return the Phase2 readiness contract for shadow-mode DB adapters."""

    classifier = RuntimeTaskDriverErrorClassifier()
    return RuntimeTaskDriverReadinessSnapshot(
        adapter_contract="src/runtime/db_driver_readiness.py:RuntimeTaskDriverAdapter",
        adapter_mode="shadow_mirror_only",
        semantics_owner="src/runtime/tasks.py:FileTaskStore",
        real_db_connection=False,
        shadow_sync_strategy="file-backed state machine remains authoritative; the adapter mirrors task rows for parity only",
        pending_human_selection_fields=(
            "migration_tool",
            "runtime_db_driver",
            "managed_postgresql_vendor",
            "secrets_manager",
        ),
        error_categories=classifier.categories(),
    )


SQL_CONTRACT_SPECS: tuple[dict[str, object], ...] = (
    {
        "contract_id": "runtime_task_claim_by_id_cas",
        "required_fragments": (
            "update runtime_task",
            "where task_id = :task_id",
            "status in ('queued', 'failed_retryable')",
            "available_at <= :current_time",
            "(lease_expires_at is null or lease_expires_at <= :current_time)",
            "status = 'leased'",
            "lease_owner = :worker_id",
            "lease_expires_at = :lease_expires_at",
            "returning",
        ),
    },
    {
        "contract_id": "runtime_task_claim_next_cas",
        "required_fragments": (
            "with candidate as",
            "status in ('queued', 'failed_retryable')",
            "available_at <= :current_time",
            "(lease_expires_at is null or lease_expires_at <= :current_time)",
            "for update skip locked",
            "limit 1",
            "status = 'leased'",
            "lease_owner = :worker_id",
            "lease_expires_at = :lease_expires_at",
            "returning",
        ),
    },
    {
        "contract_id": "runtime_task_heartbeat_guard",
        "required_fragments": (
            "update runtime_task",
            "where task_id = :task_id",
            "status in ('leased', 'running')",
            "lease_owner = :worker_id",
            "lease_expires_at is not null",
            "lease_expires_at > :current_time",
            "lease_expires_at = :lease_expires_at",
            "returning",
        ),
    },
    {
        "contract_id": "runtime_task_reclaim_expired_cas",
        "required_fragments": (
            "update runtime_task",
            "where task_id = :task_id",
            "status in ('leased', 'running')",
            "lease_expires_at is not null",
            "lease_expires_at <= :current_time",
            "coalesce((payload_json ->> 'idempotent_write')::boolean, false) is true",
            "coalesce((payload_json ->> 'resume_checkpoint_verified')::boolean, true) is true",
            "status = 'leased'",
            "lease_owner = :worker_id",
            "lease_expires_at = :lease_expires_at",
            "returning",
        ),
    },
)

REPOSITORY_QUERY_SHAPE_SPECS: tuple[dict[str, object], ...] = (
    {
        "contract_id": "runtime_task_claim_by_id_cas",
        "operation": "claim",
        "expected_binds": (
            "current_time",
            "lease_expires_at",
            "task_id",
            "updated_at",
            "worker_id",
        ),
        "required_semantics": (
            (
                "target_task_id_only",
                "where task_id = :task_id",
            ),
            (
                "claimable_status_gate",
                "status in ('queued', 'failed_retryable')",
            ),
            (
                "expired_or_unleased_guard",
                "(lease_expires_at is null or lease_expires_at <= :current_time)",
            ),
        ),
    },
    {
        "contract_id": "runtime_task_claim_next_cas",
        "operation": "claim_next",
        "expected_binds": (
            "current_time",
            "lease_expires_at",
            "updated_at",
            "worker_id",
        ),
        "required_semantics": (
            (
                "ordering_available_at_scheduled_at_task_id",
                "order by available_at, scheduled_at, task_id",
            ),
            (
                "locking_for_update_skip_locked",
                "for update skip locked",
            ),
            (
                "single_candidate_limit",
                "limit 1",
            ),
        ),
    },
    {
        "contract_id": "runtime_task_heartbeat_guard",
        "operation": "heartbeat",
        "expected_binds": (
            "current_time",
            "lease_expires_at",
            "task_id",
            "updated_at",
            "worker_id",
        ),
        "required_semantics": (
            (
                "owner_must_match",
                "lease_owner = :worker_id",
            ),
            (
                "live_lease_only",
                "lease_expires_at > :current_time",
            ),
        ),
    },
    {
        "contract_id": "runtime_task_reclaim_expired_cas",
        "operation": "reclaim_expired",
        "expected_binds": (
            "current_time",
            "lease_expires_at",
            "task_id",
            "updated_at",
            "worker_id",
        ),
        "required_semantics": (
            (
                "payload_guard_idempotent_write",
                "coalesce((payload_json ->> 'idempotent_write')::boolean, false) is true",
            ),
            (
                "payload_guard_resume_checkpoint_verified",
                "coalesce((payload_json ->> 'resume_checkpoint_verified')::boolean, true) is true",
            ),
            (
                "expired_lease_only",
                "lease_expires_at <= :current_time",
            ),
        ),
    },
)


def _normalize_sql(sql_text: str) -> str:
    return " ".join(sql_text.lower().split())


def _extract_sql_contract_section(sql_text: str, contract_id: str) -> str | None:
    start_marker = f"-- contract: {contract_id}"
    end_marker = f"-- end-contract: {contract_id}"
    start_index = sql_text.find(start_marker)
    if start_index < 0:
        return None
    start_index += len(start_marker)
    end_index = sql_text.find(end_marker, start_index)
    if end_index < 0:
        return None
    return sql_text[start_index:end_index]


def extract_sql_contract_section(sql_text: str, contract_id: str) -> str | None:
    """Return the raw SQL text for one named contract section."""

    return _extract_sql_contract_section(sql_text, contract_id)


def _extract_bind_names(section: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r":([a-zA-Z_][a-zA-Z0-9_]*)", section))))


def verify_postgresql_runtime_sql_contracts(
    *,
    sql_text: str | None = None,
    sql_path: Path | None = None,
) -> tuple[RuntimeTaskDriverSqlContractCheck, ...]:
    """Validate SQL template sections for claim/heartbeat/CAS guardrails.

    The SQL file stays a non-executed contract artifact in Phase2-2. These checks
    only prove that the PostgreSQL scaffold carries the required clauses before a
    future real driver tries to bind or execute them.
    """

    template_text = sql_text
    if template_text is None:
        path = sql_path or POSTGRES_RUNTIME_SQL_TEMPLATE_PATH
        try:
            template_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            template_text = f"-- missing template: {exc}"

    checks: list[RuntimeTaskDriverSqlContractCheck] = []
    for spec in SQL_CONTRACT_SPECS:
        contract_id = str(spec["contract_id"])
        required_fragments = tuple(str(item) for item in spec["required_fragments"])
        section = _extract_sql_contract_section(template_text, contract_id)
        if section is None:
            checks.append(
                RuntimeTaskDriverSqlContractCheck(
                    contract_id=contract_id,
                    status="contract_gap",
                    detail="SQL template section is missing from the PostgreSQL contract artifact.",
                    required_fragments=required_fragments,
                    missing_fragments=required_fragments,
                )
            )
            continue

        normalized_section = _normalize_sql(section)
        missing_fragments = tuple(
            fragment for fragment in required_fragments if fragment not in normalized_section
        )
        checks.append(
            RuntimeTaskDriverSqlContractCheck(
                contract_id=contract_id,
                status="verified" if not missing_fragments else "contract_gap",
                detail=(
                    "SQL template section retains the required claim/lease/CAS guards."
                    if not missing_fragments
                    else "SQL template section is missing required claim/lease/CAS guard clauses."
                ),
                required_fragments=required_fragments,
                missing_fragments=missing_fragments,
            )
        )

    return tuple(checks)


def verify_runtime_task_repository_query_shapes(
    *,
    sql_text: str | None = None,
    sql_path: Path | None = None,
) -> tuple[RuntimeTaskDriverRepositoryQueryShapeCheck, ...]:
    """Validate bind shape and query-shape semantics for the repository seam."""

    template_text = sql_text
    if template_text is None:
        path = sql_path or POSTGRES_RUNTIME_SQL_TEMPLATE_PATH
        try:
            template_text = path.read_text(encoding="utf-8")
        except OSError as exc:
            template_text = f"-- missing template: {exc}"

    checks: list[RuntimeTaskDriverRepositoryQueryShapeCheck] = []
    for spec in REPOSITORY_QUERY_SHAPE_SPECS:
        contract_id = str(spec["contract_id"])
        operation = str(spec["operation"])
        expected_binds = tuple(str(item) for item in spec["expected_binds"])
        required_semantics = tuple(
            str(item[0]) for item in spec["required_semantics"]  # type: ignore[index]
        )
        section = extract_sql_contract_section(template_text, contract_id)
        if section is None:
            checks.append(
                RuntimeTaskDriverRepositoryQueryShapeCheck(
                    contract_id=contract_id,
                    operation=operation,
                    status="repository_gap",
                    detail="Repository stub cannot prepare a statement because the SQL contract section is missing.",
                    expected_binds=expected_binds,
                    missing_binds=expected_binds,
                    required_semantics=required_semantics,
                    missing_semantics=required_semantics,
                )
            )
            continue

        normalized_section = _normalize_sql(section)
        bind_names = set(_extract_bind_names(section))
        missing_binds = tuple(bind for bind in expected_binds if bind not in bind_names)
        missing_semantics = tuple(
            str(name)
            for name, fragment in spec["required_semantics"]  # type: ignore[index]
            if str(fragment) not in normalized_section
        )
        checks.append(
            RuntimeTaskDriverRepositoryQueryShapeCheck(
                contract_id=contract_id,
                operation=operation,
                status="verified" if not missing_binds and not missing_semantics else "repository_gap",
                detail=(
                    "Repository stub can fake-bind this SQL contract with the expected bind shape and query semantics."
                    if not missing_binds and not missing_semantics
                    else "Repository stub is missing required bind markers or query semantics for this SQL contract."
                ),
                expected_binds=expected_binds,
                missing_binds=missing_binds,
                required_semantics=required_semantics,
                missing_semantics=missing_semantics,
            )
        )

    return tuple(checks)


def compare_runtime_task_snapshots(
    *,
    expected_tasks: list[TaskSnapshot],
    actual_tasks: list[TaskSnapshot],
    readiness: RuntimeTaskDriverReadinessSnapshot | None = None,
    sql_contract_text: str | None = None,
    sql_contract_path: Path | None = None,
    repository_query_shape_checks: tuple[RuntimeTaskDriverRepositoryQueryShapeCheck, ...] | None = None,
) -> RuntimeTaskDriverConformanceReport:
    """Compare canonical runtime snapshots with DB-shadow rows.

    Phase2-2 keeps this as a row-snapshot parity check instead of a real
    PostgreSQL query path, so DB behavior can be tested without freezing the
    future driver or migration tool.
    """

    snapshot = readiness or default_runtime_task_driver_readiness_snapshot()
    expected_by_id = {str(task.get("task_id")): task for task in expected_tasks}
    actual_by_id = {str(task.get("task_id")): task for task in actual_tasks}
    mismatches: list[RuntimeTaskDriverConformanceMismatch] = []

    for task_id in sorted(expected_by_id):
        expected = expected_by_id[task_id]
        actual = actual_by_id.get(task_id)
        if actual is None:
            mismatches.append(
                RuntimeTaskDriverConformanceMismatch(
                    task_id=task_id,
                    mismatch_type="missing_from_driver",
                    detail="Runtime task is absent from the DB-shadow adapter.",
                    expected=expected,
                    actual=None,
                )
            )
            continue
        if actual != expected:
            mismatches.append(
                RuntimeTaskDriverConformanceMismatch(
                    task_id=task_id,
                    mismatch_type="row_mismatch",
                    detail="DB-shadow row does not match the runtime task snapshot.",
                    expected=expected,
                    actual=actual,
                )
            )

    for task_id in sorted(set(actual_by_id) - set(expected_by_id)):
        mismatches.append(
            RuntimeTaskDriverConformanceMismatch(
                task_id=task_id,
                mismatch_type="unexpected_in_driver",
                detail="DB-shadow adapter has a row that is not present in runtime state.",
                expected=None,
                actual=actual_by_id[task_id],
            )
        )

    sql_contract_checks = verify_postgresql_runtime_sql_contracts(
        sql_text=sql_contract_text,
        sql_path=sql_contract_path,
    )
    repository_checks = repository_query_shape_checks or verify_runtime_task_repository_query_shapes(
        sql_text=sql_contract_text,
        sql_path=sql_contract_path,
    )
    sql_gap_count = sum(1 for check in sql_contract_checks if check.status != "verified")
    repository_gap_count = sum(1 for check in repository_checks if check.status != "verified")
    row_conformance_status = "verified" if not mismatches else "drift_detected"
    checked_contracts = (
        "task_id_row_presence",
        "row_snapshot_equivalence",
        "payload_json_equivalence",
        "status_text_code_equivalence",
        "lease_owner_and_expiry_equivalence",
        *(check.contract_id for check in sql_contract_checks),
        *(f"repository_query_shape:{check.contract_id}" for check in repository_checks),
    )

    return RuntimeTaskDriverConformanceReport(
        status=(
            "verified"
            if row_conformance_status == "verified" and sql_gap_count == 0 and repository_gap_count == 0
            else "drift_detected"
        ),
        adapter_mode=snapshot.adapter_mode,
        real_db_connection=snapshot.real_db_connection,
        checked_task_count=len(expected_by_id),
        row_conformance_status=row_conformance_status,
        mismatch_count=len(mismatches),
        sql_contract_status="verified" if sql_gap_count == 0 else "contract_gap",
        sql_gap_count=sql_gap_count,
        repository_query_shape_status="verified" if repository_gap_count == 0 else "repository_gap",
        repository_gap_count=repository_gap_count,
        checked_contracts=checked_contracts,
        cutover_eligible=False,
        mismatches=tuple(mismatches),
        sql_contract_checks=sql_contract_checks,
        repository_query_shape_checks=tuple(repository_checks),
    )
