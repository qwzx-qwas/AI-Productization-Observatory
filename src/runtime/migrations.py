"""Tool-agnostic Phase2 migration plan for the database-backed runtime."""

from __future__ import annotations

from src.runtime.db_driver_readiness import default_runtime_task_driver_readiness_snapshot


TASK_TABLE_COLUMNS: tuple[dict[str, object], ...] = (
    {"name": "task_id", "sql_type": "TEXT", "nullable": False, "source_contract_field": "task_id"},
    {"name": "task_type", "sql_type": "TEXT", "nullable": False, "source_contract_field": "task_type"},
    {"name": "task_scope", "sql_type": "TEXT", "nullable": False, "source_contract_field": "task_scope"},
    {"name": "source_id", "sql_type": "TEXT", "nullable": True, "source_contract_field": "source_id"},
    {"name": "target_type", "sql_type": "TEXT", "nullable": True, "source_contract_field": "target_type"},
    {"name": "target_id", "sql_type": "TEXT", "nullable": True, "source_contract_field": "target_id"},
    {"name": "window_start", "sql_type": "TIMESTAMPTZ", "nullable": True, "source_contract_field": "window_start"},
    {"name": "window_end", "sql_type": "TIMESTAMPTZ", "nullable": True, "source_contract_field": "window_end"},
    {"name": "payload_json", "sql_type": "JSONB", "nullable": False, "source_contract_field": "payload_json"},
    {"name": "status", "sql_type": "TEXT", "nullable": False, "source_contract_field": "status"},
    {"name": "attempt_count", "sql_type": "INTEGER", "nullable": False, "source_contract_field": "attempt_count"},
    {"name": "max_attempts", "sql_type": "INTEGER", "nullable": False, "source_contract_field": "max_attempts"},
    {"name": "scheduled_at", "sql_type": "TIMESTAMPTZ", "nullable": False, "source_contract_field": "scheduled_at"},
    {"name": "available_at", "sql_type": "TIMESTAMPTZ", "nullable": False, "source_contract_field": "available_at"},
    {"name": "started_at", "sql_type": "TIMESTAMPTZ", "nullable": True, "source_contract_field": "started_at"},
    {"name": "finished_at", "sql_type": "TIMESTAMPTZ", "nullable": True, "source_contract_field": "finished_at"},
    {"name": "lease_owner", "sql_type": "TEXT", "nullable": True, "source_contract_field": "lease_owner"},
    {
        "name": "lease_expires_at",
        "sql_type": "TIMESTAMPTZ",
        "nullable": True,
        "source_contract_field": "lease_expires_at",
    },
    {"name": "parent_task_id", "sql_type": "TEXT", "nullable": True, "source_contract_field": "parent_task_id"},
    {"name": "last_error_type", "sql_type": "TEXT", "nullable": True, "source_contract_field": "last_error_type"},
    {
        "name": "last_error_message",
        "sql_type": "TEXT",
        "nullable": True,
        "source_contract_field": "last_error_message",
    },
    {"name": "created_at", "sql_type": "TIMESTAMPTZ", "nullable": False, "source_contract_field": "created_at"},
    {"name": "updated_at", "sql_type": "TIMESTAMPTZ", "nullable": False, "source_contract_field": "updated_at"},
)

PHASE2_1_ACCEPTANCE_CHECKLIST: tuple[dict[str, object], ...] = (
    {
        "check_id": "kickoff_status",
        "status": "done",
        "detail": "Phase2-1 archived kickoff evidence keeps status = db_runtime_backend_kickoff_started; current plan advances to Phase2-2.",
    },
    {
        "check_id": "shared_backend_contract",
        "status": "done",
        "detail": "File-backed harness and future DB adapter align to the same RuntimeTaskBackend contract.",
        "artifacts": [
            "src/runtime/backend_contract.py",
            "src/runtime/db_shadow.py",
            "tests/unit/runtime_backend_conformance.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "db_shadow_adapter_parity",
        "status": "done",
        "detail": "A DB-shadow adapter now mirrors RuntimeTaskBackend behavior through an injectable fake executor without a live PostgreSQL connection.",
        "artifacts": [
            "src/runtime/db_shadow.py",
            "tests/unit/runtime_backend_conformance.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "postgresql_scaffold_shape",
        "status": "done",
        "detail": "Task table scaffold keeps text primary keys, JSONB payload_json, and text status codes.",
        "artifact": "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
    },
    {
        "check_id": "migration_semantics",
        "status": "done",
        "detail": "Migration plan remains forward-only + additive-first.",
    },
    {
        "check_id": "key_state_flow_coverage",
        "status": "done",
        "detail": "Shared conformance now covers claim conflicts and idempotency, lease renew/expiry heartbeat boundaries, blocked replay protection, and resume gating for both file-backed and DB-shadow adapters.",
        "artifacts": [
            "tests/unit/runtime_backend_conformance.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "db_driver_readiness_layer",
        "status": "done",
        "detail": "A replaceable DB-driver readiness seam now defines adapter expectations and canonical error classification so future driver work can stay below the runtime state machine.",
        "artifacts": [
            "src/runtime/db_driver_readiness.py",
            "src/runtime/db_shadow.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "human_selections_stay_unfrozen",
        "status": "done",
        "detail": "migration_tool, runtime_db_driver, managed_postgresql_vendor, and secrets_manager stay null.",
    },
    {
        "check_id": "cutover_not_executed",
        "status": "pending",
        "detail": "No live PostgreSQL connection, DB cutover, or runtime backend switch is performed in Phase2-1.",
    },
)

PHASE2_1_EXECUTED_ITEMS: tuple[str, ...] = (
    "Kickoff plan remains executable through python3 -m src.cli migrate --plan.",
    "Shared runtime backend contract is defined for the local harness and future DB adapter.",
    "A DB-driver readiness layer now separates replaceable adapter concerns and canonical error classification from the runtime state machine.",
    "A DB-shadow runtime adapter skeleton now mirrors RuntimeTaskBackend through an injectable fake executor and does not open a real PostgreSQL connection.",
    "Shared conformance assertions now run against both the file-backed harness and the DB-shadow adapter.",
    "Claim conflict/idempotency, lease renew/expiry heartbeat boundaries, blocked replay protection, and resume-gating behavior are covered by the shared conformance suite.",
    "PostgreSQL task-table scaffold remains tool-agnostic and enum-free.",
)

PHASE2_1_NOT_EXECUTED_ITEMS: tuple[str, ...] = (
    "Real PostgreSQL connection or DB task table write path.",
    "Real driver-backed claim/lease/heartbeat/CAS reclaim queries against PostgreSQL.",
    "Runtime backend cutover from the file-backed harness to PostgreSQL.",
    "Service API, frontend serviceization, or secrets-manager vendor integration.",
)

PHASE2_1_BLOCKERS: tuple[str, ...] = (
    "No blocking freeze-board conflicts currently block the Phase2-2 shadow-mode migration spine.",
    "Final dependency naming still stays behind owner decisions for migration_tool, runtime_db_driver, managed_postgresql_vendor, and secrets_manager.",
)

PHASE2_2_ACCEPTANCE_CHECKLIST: tuple[dict[str, object], ...] = (
    {
        "check_id": "replaceable_driver_adapter_interface",
        "status": "done",
        "detail": "RuntimeTaskDriverAdapter now includes DB-side row conformance verification without naming a concrete driver.",
        "artifacts": [
            "src/runtime/db_driver_readiness.py",
            "src/runtime/db_shadow.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "db_side_behavior_conformance",
        "status": "done",
        "detail": "DB-shadow rows are compared against canonical runtime task snapshots after mirror sync, and drift can be reported without resyncing.",
        "artifacts": [
            "src/runtime/db_driver_readiness.py",
            "src/runtime/db_shadow.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "migration_spine_remains_tool_agnostic",
        "status": "done",
        "detail": "The migration spine remains forward-only + additive-first and still does not freeze migration_tool or runtime_db_driver.",
    },
    {
        "check_id": "real_db_cutover_not_executed",
        "status": "pending",
        "detail": "No live PostgreSQL connection, driver-backed write path, or runtime cutover is performed in Phase2-2.",
    },
)

PHASE2_2_EXECUTED_ITEMS: tuple[str, ...] = (
    "RuntimeTaskDriverAdapter now exposes verify_runtime_tasks as the replaceable DB-side conformance seam.",
    "PostgresTaskBackendShadow now produces a shadow_conformance report for DB row parity without connecting to PostgreSQL.",
    "InMemoryPostgresTaskShadowExecutor verifies task rows against canonical runtime snapshots and reports row drift.",
    "Phase2-2 conformance tests cover both verified parity and deliberate DB-shadow drift detection.",
)

PHASE2_2_PROGRESS: dict[str, object] = {
    "runtime_backend_spine_status": "db_shadow_conformance_ready",
    "adapter_interface_status": "replaceable_driver_adapter_contract_extended",
    "db_side_conformance_status": "shadow_row_snapshot_verification_enabled",
    "real_db_connection_executed": False,
    "runtime_cutover_executed": False,
    "conformance_focus": [
        "replaceable_driver_adapter_interface",
        "db_shadow_row_snapshot_equivalence",
        "db_shadow_drift_detection",
        "technical_error_boundaries_stay_processing_error_or_contract_error",
    ],
}

PHASE2_1_NEXT_COMMAND_PLAN: tuple[str, ...] = (
    "python3 -m src.cli migrate --plan",
    "python3 -m unittest -v tests.unit.test_runtime_migrations",
    "python3 -m unittest -v tests.unit.test_runtime tests.regression.test_replay_and_marts",
    "python3 -m src.cli validate-configs",
    "python3 -m src.cli validate-schemas",
    "python3 -m src.cli phase1-g-audit-ready-report",
    "python3 -m unittest -v tests.contract.test_contracts.Phase1GAcceptanceEvidenceContractTests",
    "python3 -m unittest -v tests.contract.test_contracts.FreezeBoardSignoffContractTests",
    "python3 -m unittest discover -s tests -t .",
)


def migration_plan() -> dict[str, object]:
    return {
        "phase": "Phase2-2",
        "status": "db_runtime_backend_migration_spine_started",
        "policy": "forward-only + additive-first",
        "canonical_basis": [
            "15_tech_stack_and_runtime.md",
            "18_runtime_task_and_replay_contracts.md",
            "17_open_decisions_and_freeze_board.md:DEC-007",
            "17_open_decisions_and_freeze_board.md:DEC-022",
            "17_open_decisions_and_freeze_board.md:DEC-027",
            "17_open_decisions_and_freeze_board.md:DEC-029",
            "phase2_prompt.md",
        ],
        "backend_baseline": {
            "database_engine": "PostgreSQL 17",
            "task_table_location": "primary relational DB",
            "file_backed_harness_role": "local_only parity and rollback harness only",
            "controlled_vocab_db_expression": "text codes from versioned config artifacts",
        },
        "must_hold_contracts": [
            "GitHub live / Product Hunt deferred boundary stays unchanged.",
            "Task table remains part of the primary relational DB.",
            "Lease timeout stays 30s and heartbeat stays about every 10s.",
            "Replay and blocked semantics stay aligned with the existing runtime contract.",
            "Task schema keeps text primary keys, JSONB payload_json, and text status codes instead of DB enums.",
            "The scaffold must stay tool-agnostic while migration_tool and runtime_db_driver remain owner-selected future dependencies, not frozen runtime facts.",
        ],
        "reserved_human_selections": {
            "migration_tool": None,
            "runtime_db_driver": None,
            "managed_postgresql_vendor": None,
            "secrets_manager": None,
        },
        "driver_readiness": default_runtime_task_driver_readiness_snapshot().to_dict(),
        "driver_conformance_contract": {
            "adapter_method": "verify_runtime_tasks",
            "report_type": "RuntimeTaskDriverConformanceReport",
            "status_values": ["verified", "drift_detected"],
            "cutover_eligible": False,
            "real_db_connection": False,
            "purpose": "DB-side row snapshot parity verification in shadow mode.",
        },
        "artifacts": {
            "runtime_backend_contract_path": "src/runtime/backend_contract.py",
            "db_driver_readiness_path": "src/runtime/db_driver_readiness.py",
            "db_shadow_backend_path": "src/runtime/db_shadow.py",
            "shared_conformance_suite_path": "tests/unit/runtime_backend_conformance.py",
            "file_backed_conformance_test_path": "tests/unit/test_runtime.py",
            "sql_template_path": "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
            "migration_plan_test_path": "tests/unit/test_runtime_migrations.py",
        },
        "phase2_1_progress": {
            "driver_readiness_layer_status": "shadow_adapter_ready_for_driver_swap",
            "state_semantics_owner": "file_backed_runtime_contract",
            "adapter_swap_ready_without_state_rewrite": True,
            "real_db_connection_executed": False,
            "conformance_focus": [
                "claim_conflict_and_idempotency",
                "lease_renew_boundary",
                "heartbeat_expiry_guard",
                "blocked_replay_cannot_promote_success",
                "resume_gating_window_and_checkpoint_blocking",
            ],
        },
        "phase2_2_progress": dict(PHASE2_2_PROGRESS),
        "phase2_1_acceptance_checklist": list(PHASE2_1_ACCEPTANCE_CHECKLIST),
        "phase2_2_acceptance_checklist": list(PHASE2_2_ACCEPTANCE_CHECKLIST),
        "executed_items": list(PHASE2_1_EXECUTED_ITEMS),
        "phase2_2_executed_items": list(PHASE2_2_EXECUTED_ITEMS),
        "not_executed_items": list(PHASE2_1_NOT_EXECUTED_ITEMS),
        "blocking_items": list(PHASE2_1_BLOCKERS),
        "task_table_columns": list(TASK_TABLE_COLUMNS),
        "next_command_plan": list(PHASE2_1_NEXT_COMMAND_PLAN),
        "next_steps": [
            "Use the DB-side conformance report as the next guardrail before choosing any migration tool.",
            "Keep the file-backed harness as the runnable baseline until DB adapter parity tests close.",
            "Swap the fake executor behind src/runtime/db_shadow.py for a real driver-backed repository only after owner decisions freeze runtime_db_driver and migration_tool.",
        ],
    }
