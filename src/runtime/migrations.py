"""Tool-agnostic Phase2 migration plan for the database-backed runtime."""

from __future__ import annotations

from src.runtime.db_driver_readiness import (
    default_runtime_task_driver_readiness_snapshot,
    verify_postgresql_runtime_sql_contracts,
    verify_runtime_task_repository_query_shapes,
)
from src.runtime.db_driver_repository_stub import RuntimeTaskDriverRepositoryStub


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
        "check_id": "driver_repository_stub_readiness",
        "status": "done",
        "detail": "A minimal driver repository stub now consumes SQL contract sections through fake-bound statement capture and bind-shape validation only.",
        "artifacts": [
            "src/runtime/db_driver_repository_stub.py",
            "tests/unit/test_runtime_driver_repository_stub.py",
        ],
    },
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
        "detail": "DB-shadow conformance now distinguishes row drift, SQL contract gaps, and repository/query-shape gaps without a live database.",
        "artifacts": [
            "src/runtime/db_driver_readiness.py",
            "src/runtime/db_driver_repository_stub.py",
            "src/runtime/db_shadow.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "repository_result_shape_mapping",
        "status": "done",
        "detail": "The repository stub now validates multiple fake driver-like result rows as losslessly mappable to TaskSnapshot, including mapping-like rows, aware datetimes, null preservation, timestamp timezone guards, status semantics, worker, lease, heartbeat, attempt, and error fields.",
        "artifacts": [
            "src/runtime/db_driver_repository_stub.py",
            "tests/unit/test_runtime_driver_repository_stub.py",
        ],
    },
    {
        "check_id": "sql_claim_heartbeat_cas_contract_validation",
        "status": "done",
        "detail": "The PostgreSQL scaffold now carries non-executed SQL templates for claim/heartbeat/CAS reclaim, and shadow conformance reports validate the required guard clauses.",
        "artifacts": [
            "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
            "src/runtime/db_driver_readiness.py",
            "tests/unit/test_runtime.py",
        ],
    },
    {
        "check_id": "migration_spine_remains_tool_agnostic",
        "status": "done",
        "detail": "The migration spine remains forward-only + additive-first and still does not freeze migration_tool or runtime_db_driver.",
    },
    {
        "check_id": "claim_next_ordering_and_lock_contract",
        "status": "done",
        "detail": "claim_next ordering stays explicit as available_at -> scheduled_at -> task_id, and active leases stay non-claimable while the next eligible task can still be selected.",
        "artifacts": [
            "src/runtime/tasks.py",
            "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
            "tests/unit/runtime_backend_conformance.py",
            "tests/unit/test_runtime_driver_repository_stub.py",
        ],
    },
    {
        "check_id": "reclaim_payload_guard_contract",
        "status": "done",
        "detail": "Expired-lease reclaim stays guarded by payload_json.idempotent_write and payload_json.resume_checkpoint_verified in both runtime behavior coverage and repository query-shape readiness checks.",
        "artifacts": [
            "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
            "tests/unit/runtime_backend_conformance.py",
            "tests/unit/test_runtime_driver_repository_stub.py",
        ],
    },
    {
        "check_id": "real_db_cutover_not_executed",
        "status": "pending",
        "detail": "No live PostgreSQL connection, driver-backed write path, or runtime cutover is performed in Phase2-2.",
    },
)

PHASE2_2_EXECUTED_ITEMS: tuple[str, ...] = (
    "RuntimeTaskDriverAdapter now exposes verify_runtime_tasks as the replaceable DB-side conformance seam.",
    "A minimal RuntimeTaskDriverRepositoryStub now fake-binds SQL contract sections, captures statement selection, and verifies bind/query-shape readiness without connecting to PostgreSQL.",
    "The repository stub now validates fake result-row mapping back into TaskSnapshot across canonical dict, mapping-like, aware datetime, and nullable-preservation variants before any real driver is selected.",
    "The repository stub now carries negative row-shape controls for missing fields, extra fields, rename risk, status semantic drift, timezone drift, and nullability drift.",
    "PostgresTaskBackendShadow now produces a shadow_conformance report that distinguishes row drift, SQL contract gaps, and repository/query-shape gaps without connecting to PostgreSQL.",
    "InMemoryPostgresTaskShadowExecutor verifies task rows against canonical runtime snapshots and reuses the repository stub's query-shape readiness checks.",
    "The PostgreSQL scaffold now includes non-executed SQL claim/heartbeat/CAS reclaim templates, and the conformance report validates their required guard clauses.",
    "Phase2-2 conformance tests now make claim_next ordering/lock semantics and reclaim payload guards explicit across the shared backend matrix and repository stub coverage.",
)

PHASE2_2_PROGRESS: dict[str, object] = {
    "runtime_backend_spine_status": "db_shadow_and_repository_stub_ready",
    "adapter_interface_status": "replaceable_driver_adapter_contract_extended",
    "db_side_conformance_status": "shadow_row_snapshot_verification_enabled",
    "repository_stub_status": "fake_bound_query_shape_ready",
    "repository_result_shape_status": "fake_result_row_mapping_ready",
    "sql_contract_validation_status": "claim_heartbeat_reclaim_templates_verified",
    "real_db_connection_executed": False,
    "runtime_cutover_executed": False,
    "conformance_focus": [
        "replaceable_driver_adapter_interface",
        "db_shadow_row_snapshot_equivalence",
        "db_shadow_drift_detection",
        "sql_claim_heartbeat_cas_template_validation",
        "repository_query_shape_statement_selection",
        "repository_result_row_mapping_to_task_snapshot",
        "driver_like_row_variant_mapping_to_task_snapshot",
        "row_shape_gap_negative_controls",
        "claim_next_ordering_and_skip_locked_readiness",
        "reclaim_payload_guard_readiness",
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


def _gap_summaries(
    *,
    repository_query_shape_status: str,
    result_row_mapping_status: str,
    sql_contract_status: str,
) -> dict[str, object]:
    query_and_row_shape_status = (
        "verified"
        if repository_query_shape_status == "verified" and result_row_mapping_status == "verified"
        else "gap"
    )
    return {
        "query_shape_row_shape_gap": {
            "status": query_and_row_shape_status,
            "repository_query_shape_status": repository_query_shape_status,
            "result_row_mapping_status": result_row_mapping_status,
            "detail": (
                "Repository statement shape and fake result-row mapping are verified in stub/shadow readiness only."
                if query_and_row_shape_status == "verified"
                else "Repository statement shape or fake result-row mapping still has a readiness gap."
            ),
            "not_cutover_evidence": "This is not a real driver-backed query path and does not prove runtime DB cutover.",
        },
        "semantic_conformance_gap": {
            "status": "stub_validated_real_driver_gap",
            "sql_contract_status": sql_contract_status,
            "detail": "Claim, lease, heartbeat, and CAS reclaim semantics are covered by file-backed/shared conformance, SQL templates, and fake-bound checks, but not by a real PostgreSQL driver execution path.",
            "technical_review_boundary": "Driver timeouts, schema failures, parse failures, and contract failures remain processing_error or contract errors; taxonomy uncertainty and score conflict remain review semantics.",
        },
        "operational_readiness_owner_decision_gap": {
            "status": "owner_decision_required",
            "detail": "Operational readiness is blocked on owner freeze/signoff before selecting concrete runtime dependencies or entering a real PostgreSQL shadow connection phase.",
            "real_db_connection": False,
            "runtime_cutover_executed": False,
            "reserved_human_selections": {
                "migration_tool": None,
                "runtime_db_driver": None,
                "managed_postgresql_vendor": None,
                "secrets_manager": None,
            },
            "reserved_selection_reason": "owner freeze not yet completed",
        },
    }


def _admission_decision_packet_draft() -> dict[str, object]:
    criteria = [
        "expand-backfill-contract migration rhythm",
        "forward-only main path and explicit roll-forward strategy",
        "claim / lease / heartbeat / CAS reclaim semantic validation",
        "technical failure and review semantic split",
        "fixed evidence pair preservation",
    ]
    return {
        "decision_scope": {
            "status": "draft_criteria_only",
            "freezes": "admission / evaluation criteria only",
            "does_not_freeze": [
                "product names",
                "vendor names",
                "driver names",
                "migration tool names",
            ],
            "real_database_connection": False,
            "runtime_cutover": False,
        },
        "frozen_criteria_recommended": criteria,
        "evidence_mapping": [
            {
                "criterion": "expand-backfill-contract migration rhythm",
                "status": "criteria_defined_with_stub_evidence",
                "evidence": [
                    "15_tech_stack_and_runtime.md: forward-only plus additive-first / expand-backfill-contract discipline",
                    "src/runtime/migrations.py: policy and migration_spine_remains_tool_agnostic",
                    "tests.unit.test_runtime_migrations",
                ],
                "gap": "No concrete migration_tool has owner signoff, and no real migration execution has occurred.",
            },
            {
                "criterion": "forward-only main path and explicit roll-forward strategy",
                "status": "criteria_defined_with_stub_evidence",
                "evidence": [
                    "src/runtime/migrations.py: policy = forward-only + additive-first",
                    "17_open_decisions_and_freeze_board.md:DEC-027",
                ],
                "gap": "Future tool selection must prove explicit roll-forward behavior before freeze.",
            },
            {
                "criterion": "claim / lease / heartbeat / CAS reclaim semantic validation",
                "status": "stub_validated_real_driver_gap",
                "evidence": [
                    "tests.unit.test_runtime",
                    "tests.unit.runtime_backend_conformance",
                    "tests.unit.test_runtime_driver_repository_stub",
                    "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
                ],
                "gap": "No real driver-backed PostgreSQL execution path has validated these semantics yet.",
            },
            {
                "criterion": "technical failure and review semantic split",
                "status": "criteria_defined_with_regression_evidence",
                "evidence": [
                    "src/runtime/db_driver_readiness.py: RuntimeTaskDriverErrorClassifier",
                    "tests.unit.test_runtime",
                    "tests.regression.test_replay_and_marts",
                ],
                "gap": "Future driver exceptions must continue mapping to processing_error or contract errors, not review issues.",
            },
            {
                "criterion": "fixed evidence pair preservation",
                "status": "preserve_existing_semantics",
                "evidence": [
                    "docs/phase1_g_acceptance_evidence.md:412",
                    "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json:1439",
                ],
                "gap": "Regenerated evidence must not rewrite the existing Phase1-G go / owner-signoff meaning.",
            },
        ],
        "gaps_and_risks": [
            "The fake harness may still differ from a real driver result object.",
            "Row-shape readiness is not production database readiness.",
            "repository_query_shape_status can be misread as cutover unless paired with real_db_connection=false and cutover_eligible=false.",
            "Vendor, driver, and tool freeze cannot happen before owner signoff.",
            "The fixed evidence pair must keep its existing Phase1-G go / owner-signoff semantics if evidence is regenerated.",
        ],
        "owner_required_decision": [
            "Accept or reject freezing these admission criteria.",
            "Allow later selection of a concrete migration_tool.",
            "Allow later selection of a concrete runtime_db_driver.",
            "Allow a later real PostgreSQL shadow connection phase.",
            "Allow later runtime cutover planning.",
        ],
        "provisional_recommendation_without_freeze": {
            "status": "do_not_freeze",
            "recommendation": "Use the criteria as a draft gate and keep building stub/shadow conformance evidence until owner signoff authorizes concrete dependency selection.",
            "blocker": "runtime_db_driver and migration_tool admission criteria are not fully satisfied by real driver or migration-tool evidence.",
            "safe_next_step": "Extend evidence around stub/shadow row-shape, SQL-contract, and semantic conformance without naming final dependencies or opening a real DB connection.",
            "readiness_claim": "Readiness improved at the fake/stub layer only; runtime cutover is not ready.",
        },
    }


def migration_plan() -> dict[str, object]:
    sql_contract_checks = verify_postgresql_runtime_sql_contracts()
    repository_query_shape_checks = verify_runtime_task_repository_query_shapes()
    repository_stub = RuntimeTaskDriverRepositoryStub()
    result_row_mapping_report = repository_stub.verify_result_row_mapping_readiness()
    result_row_variant_reports = repository_stub.verify_driver_like_result_row_variants()
    result_row_gap_control_reports = repository_stub.verify_result_row_gap_controls()
    sql_contract_status = (
        "verified" if all(check.status == "verified" for check in sql_contract_checks) else "contract_gap"
    )
    repository_query_shape_status = (
        "verified"
        if all(check.status == "verified" for check in repository_query_shape_checks)
        else "repository_gap"
    )
    result_row_mapping_status = (
        "verified"
        if result_row_mapping_report.status == "verified"
        and all(report.status == "verified" for report in result_row_variant_reports)
        else "row_shape_gap"
    )
    row_gap_control_status = (
        "gap_controls_detected"
        if all(report.status == "row_shape_gap" for report in result_row_gap_control_reports)
        else "gap_control_incomplete"
    )
    gap_summaries = _gap_summaries(
        repository_query_shape_status=repository_query_shape_status,
        result_row_mapping_status=result_row_mapping_status,
        sql_contract_status=sql_contract_status,
    )
    return {
        "phase": "Phase2-2",
        "status": "db_runtime_backend_migration_spine_started",
        "policy": "forward-only + additive-first",
        "cli_evidence_surface": {
            "stage": "stub_shadow_readiness_validation_only",
            "real_db_connection": False,
            "runtime_cutover_executed": False,
            "cutover_claim": "not_completed",
            "reserved_selection_reason": "owner freeze not yet completed",
            "warning": "repository_query_shape_status and result_row_mapping_status are readiness checks only, not proof of real PostgreSQL cutover.",
        },
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
            "row_conformance_status_values": ["verified", "drift_detected"],
            "sql_contract_status_values": ["verified", "contract_gap"],
            "repository_query_shape_status_values": ["verified", "repository_gap"],
            "result_row_mapping_status_values": ["verified", "row_shape_gap"],
            "sql_contract_artifact_path": "src/runtime/sql/postgresql_task_runtime_phase2_1.sql",
            "repository_stub_path": "src/runtime/db_driver_repository_stub.py",
            "sql_contract_status": sql_contract_status,
            "sql_contract_check_ids": [check.contract_id for check in sql_contract_checks],
            "repository_query_shape_status": repository_query_shape_status,
            "repository_query_shape_check_ids": [
                check.contract_id for check in repository_query_shape_checks
            ],
            "result_row_mapping_status": result_row_mapping_status,
            "result_row_mapping_checked_fields": list(result_row_mapping_report.expected_fields),
            "result_row_mapping_positive_variants": [
                report.row_variant for report in result_row_variant_reports
            ],
            "result_row_mapping_positive_variant_count": len(result_row_variant_reports),
            "result_row_gap_control_status": row_gap_control_status,
            "result_row_gap_control_variants": [
                report.row_variant for report in result_row_gap_control_reports
            ],
            "cutover_eligible": False,
            "real_db_connection": False,
            "purpose": "DB-side row parity plus repository query-shape and fake result-row mapping readiness verification in shadow mode.",
        },
        "sql_contract_checks": [check.to_dict() for check in sql_contract_checks],
        "repository_query_shape_checks": [
            check.to_dict() for check in repository_query_shape_checks
        ],
        "result_row_mapping_report": result_row_mapping_report.to_dict(),
        "result_row_mapping_variant_reports": [
            report.to_dict() for report in result_row_variant_reports
        ],
        "result_row_gap_control_reports": [
            report.to_dict() for report in result_row_gap_control_reports
        ],
        "gap_summaries": gap_summaries,
        "decision_packet_draft": _admission_decision_packet_draft(),
        "artifacts": {
            "runtime_backend_contract_path": "src/runtime/backend_contract.py",
            "db_driver_readiness_path": "src/runtime/db_driver_readiness.py",
            "db_driver_repository_stub_path": "src/runtime/db_driver_repository_stub.py",
            "db_shadow_backend_path": "src/runtime/db_shadow.py",
            "shared_conformance_suite_path": "tests/unit/runtime_backend_conformance.py",
            "file_backed_conformance_test_path": "tests/unit/test_runtime.py",
            "repository_stub_test_path": "tests/unit/test_runtime_driver_repository_stub.py",
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
            "Use the DB-side conformance report and repository query-shape readiness as the next guardrails before choosing any migration tool.",
            "Keep the file-backed harness as the runnable baseline until DB adapter parity tests close.",
            "Swap the fake executor behind src/runtime/db_shadow.py for a real driver-backed repository only after owner decisions freeze runtime_db_driver and migration_tool.",
        ],
    }
