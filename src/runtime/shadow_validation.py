"""Real PostgreSQL shadow validation for the Phase2 runtime task table.

This module is intentionally narrow: it connects only to an explicitly supplied
local shadow DSN, applies the reviewed raw SQL task-table scaffold to a clean
shadow database, and records shadow-only evidence. It does not switch the
runtime backend, freeze a production driver, or claim cutover readiness.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import importlib
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from src.common.errors import ConfigError, ContractValidationError
from src.runtime.db_driver_readiness import POSTGRES_RUNTIME_SQL_TEMPLATE_PATH
from src.runtime.db_driver_repository_stub import RuntimeTaskDriverRepositoryStub


SHADOW_DATABASE_ENV_VAR = "APO_SHADOW_DATABASE_URL"
DDL_CONTRACT_SPLIT_MARKER = "-- Phase2-2 SQL contract templates."
LOCAL_SHADOW_HOSTS = {"localhost", "127.0.0.1", "::1"}


def redact_shadow_database_url(database_url: str) -> str:
    """Return a display-safe DSN with any password removed."""

    if not database_url:
        return "<unset>"
    parsed = urlsplit(database_url)
    if not parsed.scheme or not parsed.netloc:
        return "[REDACTED]"

    hostname = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    username = unquote(parsed.username or "<shadow_user>")
    if parsed.password is None:
        netloc = f"{username}@{hostname}{port}" if parsed.username else f"{hostname}{port}"
    else:
        netloc = f"{username}:[REDACTED]@{hostname}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _redact_text(value: str, *, database_url: str) -> str:
    redacted = redact_shadow_database_url(database_url)
    text = value.replace(database_url, redacted)
    password = urlsplit(database_url).password
    if password:
        text = text.replace(password, "[REDACTED]")
    return text


def validate_shadow_database_url(database_url: str) -> None:
    """Reject DSNs that do not look like the owner-approved local shadow DB."""

    parsed = urlsplit(database_url)
    hostname = parsed.hostname
    database_name = parsed.path.lstrip("/")
    username = parsed.username or ""
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ConfigError(f"{SHADOW_DATABASE_ENV_VAR} must use a PostgreSQL URL scheme.")
    if hostname not in LOCAL_SHADOW_HOSTS:
        raise ConfigError(f"{SHADOW_DATABASE_ENV_VAR} must point to localhost for shadow validation.")
    if "shadow" not in database_name.lower():
        raise ConfigError(f"{SHADOW_DATABASE_ENV_VAR} database name must visibly identify a shadow database.")
    if "shadow" not in username.lower():
        raise ConfigError(f"{SHADOW_DATABASE_ENV_VAR} user name must visibly identify a shadow user.")


def load_runtime_task_ddl(sql_path: Path = POSTGRES_RUNTIME_SQL_TEMPLATE_PATH) -> str:
    """Load only executable DDL, excluding abstract :bind SQL contract templates."""

    sql_text = sql_path.read_text(encoding="utf-8")
    ddl_text = sql_text.split(DDL_CONTRACT_SPLIT_MARKER, 1)[0]
    if "CREATE TABLE IF NOT EXISTS runtime_task" not in ddl_text:
        raise ContractValidationError("runtime_task DDL is missing from the PostgreSQL scaffold.")
    return ddl_text.strip()


def _split_sql_statements(sql_text: str) -> list[str]:
    statements = []
    for statement in sql_text.split(";"):
        stripped = statement.strip()
        if stripped:
            statements.append(stripped)
    return statements


def _utc_iso(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{utc_value.isoformat(timespec='seconds')}Z"


def _connect_with_psycopg(database_url: str):
    try:
        psycopg = importlib.import_module("psycopg")
        rows = importlib.import_module("psycopg.rows")
    except ModuleNotFoundError as exc:
        raise ConfigError(
            "Real PostgreSQL shadow validation requires the optional shadow-validation dependency "
            "`psycopg[binary]`. Install it locally for this shadow-only check; this does not freeze "
            "the production runtime driver."
        ) from exc
    return psycopg.connect(
        database_url,
        autocommit=True,
        connect_timeout=10,
        row_factory=rows.dict_row,
    )


def _jsonb(value: dict[str, object]) -> object:
    try:
        json_module = importlib.import_module("psycopg.types.json")
    except ModuleNotFoundError as exc:
        raise ConfigError("psycopg JSONB support is unavailable for shadow validation.") from exc
    return json_module.Jsonb(value)


def run_postgresql_shadow_validation(
    *,
    database_url: str | None = None,
    connector: Callable[[str], Any] | None = None,
    sql_path: Path = POSTGRES_RUNTIME_SQL_TEMPLATE_PATH,
) -> dict[str, object]:
    """Run a guarded real PostgreSQL shadow validation against a local DSN."""

    dsn = database_url or os.environ.get(SHADOW_DATABASE_ENV_VAR)
    if not dsn:
        raise ConfigError(f"{SHADOW_DATABASE_ENV_VAR} is required for real PostgreSQL shadow validation.")
    validate_shadow_database_url(dsn)

    connect = connector or _connect_with_psycopg
    redacted_dsn = redact_shadow_database_url(dsn)
    checks: list[dict[str, object]] = []
    repository = RuntimeTaskDriverRepositoryStub()
    shanghai = ZoneInfo("Asia/Shanghai")
    window_start = datetime(2026, 4, 25, 8, 0, tzinfo=shanghai)
    window_end = datetime(2026, 4, 25, 9, 0, tzinfo=shanghai)
    now = datetime(2026, 4, 25, 0, 0, 5, tzinfo=timezone.utc)
    lease_expires = datetime(2026, 4, 25, 0, 0, 35, tzinfo=timezone.utc)
    payload = {
        "source_code": "github",
        "idempotent_write": True,
        "resume_checkpoint_verified": True,
    }

    try:
        with connect(dsn) as connection:
            version_row = connection.execute("SELECT version() AS version, current_database() AS database_name").fetchone()
            checks.append({"check_id": "psycopg_shadow_connection", "status": "passed"})

            connection.execute("DROP TABLE IF EXISTS runtime_task CASCADE")
            for statement in _split_sql_statements(load_runtime_task_ddl(sql_path)):
                connection.execute(statement)
            checks.append({"check_id": "raw_sql_runtime_task_ddl_applied", "status": "passed"})

            connection.execute(
                """
                INSERT INTO runtime_task (
                    task_id, task_type, task_scope, source_id, target_type, target_id,
                    window_start, window_end, payload_json, status, attempt_count, max_attempts,
                    scheduled_at, available_at, started_at, finished_at, lease_owner,
                    lease_expires_at, parent_task_id, last_error_type, last_error_message,
                    created_at, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    "shadow-task-001",
                    "pull_collect",
                    "per_source_window",
                    "github",
                    None,
                    None,
                    window_start,
                    window_end,
                    _jsonb(payload),
                    "queued",
                    0,
                    3,
                    now,
                    now,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    now,
                    now,
                ),
            )
            row = connection.execute("SELECT * FROM runtime_task WHERE task_id = %s", ("shadow-task-001",)).fetchone()
            expected_snapshot = {
                "task_id": "shadow-task-001",
                "task_type": "pull_collect",
                "task_scope": "per_source_window",
                "source_id": "github",
                "target_type": None,
                "target_id": None,
                "window_start": _utc_iso(window_start),
                "window_end": _utc_iso(window_end),
                "payload_json": payload,
                "status": "queued",
                "attempt_count": 0,
                "max_attempts": 3,
                "scheduled_at": _utc_iso(now),
                "available_at": _utc_iso(now),
                "started_at": None,
                "finished_at": None,
                "lease_owner": None,
                "lease_expires_at": None,
                "parent_task_id": None,
                "last_error_type": None,
                "last_error_message": None,
                "created_at": _utc_iso(now),
                "updated_at": _utc_iso(now),
            }
            mapping_report = repository.map_result_row_to_task_snapshot(
                row,
                expected_snapshot=expected_snapshot,
                row_variant="psycopg_dict_row",
            )
            checks.append(
                {
                    "check_id": "runtime_task_row_round_trip",
                    "status": "passed" if mapping_report.status == "verified" else "failed",
                    "row_mapping_status": mapping_report.status,
                }
            )

            tz_row = connection.execute(
                """
                SELECT
                    to_char(window_start AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS utc_value,
                    to_char(window_start AT TIME ZONE 'Asia/Shanghai', 'YYYY-MM-DD"T"HH24:MI:SS') AS shanghai_value,
                    target_type IS NULL AS target_type_is_null,
                    parent_task_id IS NULL AS parent_task_id_is_null
                FROM runtime_task
                WHERE task_id = %s
                """,
                ("shadow-task-001",),
            ).fetchone()
            checks.append(
                {
                    "check_id": "utc_and_asia_shanghai_round_trip",
                    "status": (
                        "passed"
                        if tz_row["utc_value"] == "2026-04-25T00:00:00Z"
                        and tz_row["shanghai_value"] == "2026-04-25T08:00:00"
                        else "failed"
                    ),
                }
            )
            checks.append(
                {
                    "check_id": "nullable_fields_preserved",
                    "status": (
                        "passed"
                        if tz_row["target_type_is_null"] and tz_row["parent_task_id_is_null"]
                        else "failed"
                    ),
                }
            )

            claimed = connection.execute(
                """
                UPDATE runtime_task
                SET status = 'leased',
                    lease_owner = %s,
                    lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                  AND status IN ('queued', 'failed_retryable')
                  AND available_at <= %s
                  AND (lease_expires_at IS NULL OR lease_expires_at <= %s)
                RETURNING task_id, status, lease_owner, lease_expires_at, updated_at
                """,
                ("worker-shadow", lease_expires, now, "shadow-task-001", now, now),
            ).fetchone()
            checks.append(
                {
                    "check_id": "claim_by_id_cas",
                    "status": (
                        "passed"
                        if claimed and claimed["status"] == "leased" and claimed["lease_owner"] == "worker-shadow"
                        else "failed"
                    ),
                }
            )

            heartbeat_expiry = datetime(2026, 4, 25, 0, 0, 45, tzinfo=timezone.utc)
            heartbeat = connection.execute(
                """
                UPDATE runtime_task
                SET lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                  AND status IN ('leased', 'running')
                  AND lease_owner = %s
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at > %s
                RETURNING task_id, status, lease_owner, lease_expires_at, updated_at
                """,
                (heartbeat_expiry, now, "shadow-task-001", "worker-shadow", now),
            ).fetchone()
            wrong_worker_heartbeat = connection.execute(
                """
                UPDATE runtime_task
                SET lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                  AND status IN ('leased', 'running')
                  AND lease_owner = %s
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at > %s
                RETURNING task_id
                """,
                (heartbeat_expiry, now, "shadow-task-001", "worker-other", now),
            ).fetchone()
            checks.append(
                {
                    "check_id": "heartbeat_guard",
                    "status": "passed" if heartbeat and wrong_worker_heartbeat is None else "failed",
                }
            )

            expired_at = datetime(2026, 4, 24, 23, 59, 59, tzinfo=timezone.utc)
            connection.execute(
                """
                UPDATE runtime_task
                SET status = 'running',
                    lease_owner = %s,
                    lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                """,
                ("worker-stale", expired_at, expired_at, "shadow-task-001"),
            )
            reclaimed = connection.execute(
                """
                UPDATE runtime_task
                SET status = 'leased',
                    lease_owner = %s,
                    lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                  AND status IN ('leased', 'running')
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= %s
                  AND COALESCE((payload_json ->> 'idempotent_write')::boolean, false) IS TRUE
                  AND COALESCE((payload_json ->> 'resume_checkpoint_verified')::boolean, true) IS TRUE
                RETURNING task_id, status, lease_owner, lease_expires_at, updated_at
                """,
                ("worker-reclaim", lease_expires, now, "shadow-task-001", now),
            ).fetchone()
            checks.append(
                {
                    "check_id": "expired_cas_reclaim",
                    "status": (
                        "passed"
                        if reclaimed and reclaimed["status"] == "leased" and reclaimed["lease_owner"] == "worker-reclaim"
                        else "failed"
                    ),
                }
            )

            connection.execute(
                """
                INSERT INTO runtime_task (
                    task_id, task_type, task_scope, payload_json, status, attempt_count, max_attempts,
                    scheduled_at, available_at, lease_owner, lease_expires_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "shadow-task-no-reclaim",
                    "pull_collect",
                    "per_source_window",
                    _jsonb({"source_code": "github", "idempotent_write": False, "resume_checkpoint_verified": True}),
                    "running",
                    0,
                    3,
                    now,
                    now,
                    "worker-stale",
                    expired_at,
                    now,
                    now,
                ),
            )
            blocked_reclaim = connection.execute(
                """
                UPDATE runtime_task
                SET status = 'leased',
                    lease_owner = %s,
                    lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = %s
                  AND status IN ('leased', 'running')
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at <= %s
                  AND COALESCE((payload_json ->> 'idempotent_write')::boolean, false) IS TRUE
                  AND COALESCE((payload_json ->> 'resume_checkpoint_verified')::boolean, true) IS TRUE
                RETURNING task_id
                """,
                ("worker-reclaim", lease_expires, now, "shadow-task-no-reclaim", now),
            ).fetchone()
            checks.append(
                {
                    "check_id": "negative_reclaim_payload_guard",
                    "status": "passed" if blocked_reclaim is None else "failed",
                }
            )

            connection.execute(
                """
                INSERT INTO runtime_task (
                    task_id, task_type, task_scope, payload_json, status, attempt_count, max_attempts,
                    scheduled_at, available_at, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    "shadow-task-claim-next",
                    "pull_collect",
                    "per_source_window",
                    _jsonb(payload),
                    "queued",
                    0,
                    3,
                    now,
                    now,
                    now,
                    now,
                ),
            )
            claim_next = connection.execute(
                """
                WITH candidate AS (
                    SELECT task_id
                    FROM runtime_task
                    WHERE status IN ('queued', 'failed_retryable')
                      AND available_at <= %s
                      AND (lease_expires_at IS NULL OR lease_expires_at <= %s)
                    ORDER BY available_at, scheduled_at, task_id
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                )
                UPDATE runtime_task
                SET status = 'leased',
                    lease_owner = %s,
                    lease_expires_at = %s,
                    updated_at = %s
                WHERE task_id = (SELECT task_id FROM candidate)
                RETURNING task_id, status, lease_owner, lease_expires_at, updated_at
                """,
                (now, now, "worker-next", lease_expires, now),
            ).fetchone()
            checks.append(
                {
                    "check_id": "claim_next_ordering_and_lock_contract",
                    "status": (
                        "passed"
                        if claim_next
                        and claim_next["task_id"] == "shadow-task-claim-next"
                        and claim_next["status"] == "leased"
                        else "failed"
                    ),
                }
            )

            invalid_status_rejected = False
            try:
                connection.execute(
                    """
                    INSERT INTO runtime_task (
                        task_id, task_type, task_scope, payload_json, status, attempt_count, max_attempts,
                        scheduled_at, available_at, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        "shadow-task-invalid-status",
                        "pull_collect",
                        "per_source_window",
                        _jsonb(payload),
                        "review_issue",
                        0,
                        3,
                        now,
                        now,
                        now,
                        now,
                    ),
                )
            except Exception:
                invalid_status_rejected = True
            checks.append(
                {
                    "check_id": "negative_status_semantic_control",
                    "status": "passed" if invalid_status_rejected else "failed",
                }
            )

    except Exception as exc:
        safe_message = _redact_text(str(exc), database_url=dsn)
        raise ContractValidationError(f"Real PostgreSQL shadow validation failed: {safe_message}") from exc

    failed_checks = [check for check in checks if check["status"] != "passed"]
    return {
        "phase": "Phase2-2",
        "status": "real_postgresql_shadow_validation_passed" if not failed_checks else "real_postgresql_shadow_validation_failed",
        "shadow_database_url": redacted_dsn,
        "database_version": version_row["version"],
        "database_name": version_row["database_name"],
        "real_db_connection": True,
        "cutover_eligible": False,
        "runtime_cutover_executed": False,
        "production_db_readiness_claimed": False,
        "runtime_cutover_readiness_claimed": False,
        "runtime_db_driver": None,
        "runtime_db_driver_candidate_used": "psycopg3 sync",
        "migration_tool": None,
        "migration_execution": "reviewed_raw_sql_shadow_apply_only",
        "alembic_execution": "not_used_not_required_by_current_repo_command",
        "managed_postgresql_vendor": None,
        "secrets_manager": None,
        "clean_shadow_reset_executed": True,
        "checks": checks,
        "failed_checks": failed_checks,
        "evidence_scope": "local_disposable_shadow_db_only",
    }
