from __future__ import annotations

import unittest
from pathlib import Path

from src.runtime.migrations import migration_plan


REPO_ROOT = Path(__file__).resolve().parents[2]
SQL_TEMPLATE_PATH = REPO_ROOT / "src" / "runtime" / "sql" / "postgresql_task_runtime_phase2_1.sql"


class RuntimeMigrationPlanUnitTests(unittest.TestCase):
    def test_migration_plan_tracks_phase2_2_spine_and_reserved_selections(self) -> None:
        plan = migration_plan()

        self.assertEqual(plan["phase"], "Phase2-2")
        self.assertEqual(plan["status"], "db_runtime_backend_migration_spine_started")
        self.assertEqual(plan["policy"], "forward-only + additive-first")
        self.assertEqual(plan["backend_baseline"]["database_engine"], "PostgreSQL 17")
        self.assertEqual(plan["backend_baseline"]["task_table_location"], "primary relational DB")
        self.assertIn("17_open_decisions_and_freeze_board.md:DEC-007", plan["canonical_basis"])
        self.assertIn("17_open_decisions_and_freeze_board.md:DEC-022", plan["canonical_basis"])
        self.assertIn("17_open_decisions_and_freeze_board.md:DEC-027", plan["canonical_basis"])
        self.assertIn("17_open_decisions_and_freeze_board.md:DEC-029", plan["canonical_basis"])
        self.assertTrue(all(value is None for value in plan["reserved_human_selections"].values()))
        self.assertEqual(plan["artifacts"]["runtime_backend_contract_path"], "src/runtime/backend_contract.py")
        self.assertEqual(plan["artifacts"]["db_driver_readiness_path"], "src/runtime/db_driver_readiness.py")
        self.assertEqual(plan["artifacts"]["db_shadow_backend_path"], "src/runtime/db_shadow.py")
        self.assertEqual(plan["artifacts"]["shared_conformance_suite_path"], "tests/unit/runtime_backend_conformance.py")
        self.assertEqual(plan["artifacts"]["file_backed_conformance_test_path"], "tests/unit/test_runtime.py")
        self.assertEqual(plan["artifacts"]["migration_plan_test_path"], "tests/unit/test_runtime_migrations.py")
        readiness = plan["driver_readiness"]
        self.assertEqual(readiness["adapter_mode"], "shadow_mirror_only")
        self.assertFalse(readiness["real_db_connection"])
        self.assertIn("runtime_db_driver", readiness["pending_human_selection_fields"])
        readiness_codes = {item["code"] for item in readiness["error_categories"]}
        self.assertEqual(
            readiness_codes,
            {
                "claim_conflict",
                "lease_expired",
                "driver_unavailable",
                "driver_timeout",
                "driver_protocol_violation",
            },
        )
        self.assertEqual(plan["driver_conformance_contract"]["adapter_method"], "verify_runtime_tasks")
        self.assertEqual(plan["driver_conformance_contract"]["report_type"], "RuntimeTaskDriverConformanceReport")
        self.assertFalse(plan["driver_conformance_contract"]["cutover_eligible"])
        self.assertFalse(plan["driver_conformance_contract"]["real_db_connection"])
        self.assertEqual(plan["phase2_1_progress"]["driver_readiness_layer_status"], "shadow_adapter_ready_for_driver_swap")
        self.assertTrue(plan["phase2_1_progress"]["adapter_swap_ready_without_state_rewrite"])
        self.assertFalse(plan["phase2_1_progress"]["real_db_connection_executed"])
        self.assertIn(
            "resume_gating_window_and_checkpoint_blocking",
            plan["phase2_1_progress"]["conformance_focus"],
        )
        self.assertEqual(plan["phase2_2_progress"]["runtime_backend_spine_status"], "db_shadow_conformance_ready")
        self.assertEqual(
            plan["phase2_2_progress"]["adapter_interface_status"],
            "replaceable_driver_adapter_contract_extended",
        )
        self.assertFalse(plan["phase2_2_progress"]["real_db_connection_executed"])
        self.assertFalse(plan["phase2_2_progress"]["runtime_cutover_executed"])
        self.assertIn(
            "db_shadow_drift_detection",
            plan["phase2_2_progress"]["conformance_focus"],
        )
        checklist = {item["check_id"]: item for item in plan["phase2_1_acceptance_checklist"]}
        self.assertEqual(checklist["kickoff_status"]["status"], "done")
        self.assertEqual(checklist["shared_backend_contract"]["status"], "done")
        self.assertEqual(checklist["db_shadow_adapter_parity"]["status"], "done")
        self.assertEqual(checklist["postgresql_scaffold_shape"]["status"], "done")
        self.assertEqual(checklist["key_state_flow_coverage"]["status"], "done")
        self.assertEqual(checklist["db_driver_readiness_layer"]["status"], "done")
        self.assertEqual(checklist["human_selections_stay_unfrozen"]["status"], "done")
        self.assertEqual(checklist["cutover_not_executed"]["status"], "pending")
        phase2_2_checklist = {item["check_id"]: item for item in plan["phase2_2_acceptance_checklist"]}
        self.assertEqual(phase2_2_checklist["replaceable_driver_adapter_interface"]["status"], "done")
        self.assertEqual(phase2_2_checklist["db_side_behavior_conformance"]["status"], "done")
        self.assertEqual(phase2_2_checklist["migration_spine_remains_tool_agnostic"]["status"], "done")
        self.assertEqual(phase2_2_checklist["real_db_cutover_not_executed"]["status"], "pending")
        self.assertIn("python3 -m src.cli phase1-g-audit-ready-report", plan["next_command_plan"])
        self.assertIn(
            "A DB-driver readiness layer now separates replaceable adapter concerns and canonical error classification from the runtime state machine.",
            plan["executed_items"],
        )
        self.assertIn(
            "A DB-shadow runtime adapter skeleton now mirrors RuntimeTaskBackend through an injectable fake executor and does not open a real PostgreSQL connection.",
            plan["executed_items"],
        )
        self.assertIn(
            "Real driver-backed claim/lease/heartbeat/CAS reclaim queries against PostgreSQL.",
            plan["not_executed_items"],
        )
        self.assertIn(
            "PostgresTaskBackendShadow now produces a shadow_conformance report for DB row parity without connecting to PostgreSQL.",
            plan["phase2_2_executed_items"],
        )
        self.assertTrue(plan["blocking_items"])

        expected_fields = {
            "task_id",
            "task_type",
            "task_scope",
            "source_id",
            "target_type",
            "target_id",
            "window_start",
            "window_end",
            "payload_json",
            "status",
            "attempt_count",
            "max_attempts",
            "scheduled_at",
            "available_at",
            "started_at",
            "finished_at",
            "lease_owner",
            "lease_expires_at",
            "parent_task_id",
            "last_error_type",
            "last_error_message",
            "created_at",
            "updated_at",
        }
        self.assertEqual({column["name"] for column in plan["task_table_columns"]}, expected_fields)

    def test_sql_template_stays_postgresql_text_based_and_enum_free(self) -> None:
        content = SQL_TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE IF NOT EXISTS runtime_task", content)
        self.assertIn("task_id TEXT PRIMARY KEY", content)
        self.assertIn("payload_json JSONB NOT NULL", content)
        self.assertIn("status TEXT NOT NULL", content)
        self.assertIn("lease_expires_at TIMESTAMPTZ", content)
        self.assertIn("parent_task_id TEXT REFERENCES runtime_task (task_id)", content)
        self.assertIn("runtime_task_status_available_idx", content)
        self.assertNotIn("CREATE TYPE", content)
        self.assertNotIn(" ENUM ", content)


if __name__ == "__main__":
    unittest.main()
