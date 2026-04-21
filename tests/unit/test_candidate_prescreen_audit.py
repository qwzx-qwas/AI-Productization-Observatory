from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.candidate_prescreen.audit import build_phase1_g_audit_ready_report, write_phase1_g_audit_ready_report
from src.candidate_prescreen.workflow import run_candidate_prescreen
from src.common.files import dump_json, dump_yaml, load_json, load_yaml
from src.runtime.replay import build_default_mart
from tests.helpers import REPO_ROOT, temp_config


class CandidatePrescreenAuditUnitTests(unittest.TestCase):
    def test_phase1_g_audit_ready_report_summarizes_workspace_and_boundaries(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            from shutil import copytree

            copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )
                record = load_yaml(paths[0])
                record["human_review_status"] = "approved_for_staging"
                record["human_review_note_template_key"] = "approved"
                record["human_review_notes"] = "clear end-user product signal; evidence sufficient for staging"
                dump_yaml(paths[0], record)

                mart = build_default_mart(config)
                report = build_phase1_g_audit_ready_report(config, mart=mart)

                self.assertEqual(report["gate_status"]["github_live_candidate_discovery"], "implemented")
                self.assertEqual(report["gate_status"]["product_hunt_live_boundary"], "implemented")
                self.assertEqual(report["gate_status"]["manual_audit_judgment"], "pending_manual_audit_judgment")
                self.assertEqual(report["gate_status"]["owner_review_package"], "ready_for_owner_review")
                self.assertEqual(report["release_judgment"]["judgment"], "conditional-go")
                self.assertTrue(report["release_judgment"]["owner_required_signoff"])
                self.assertEqual(report["workspace_summary"]["candidate_document_count"], 1)
                github_summary = next(
                    summary for summary in report["workspace_summary"]["sources"] if summary["source_code"] == "github"
                )
                product_hunt_summary = next(
                    summary for summary in report["workspace_summary"]["sources"] if summary["source_code"] == "product_hunt"
                )
                self.assertTrue(github_summary["discovery_capabilities"]["live_enabled_in_current_phase"])
                self.assertFalse(product_hunt_summary["discovery_capabilities"]["live_enabled_in_current_phase"])
                unresolved_items = {
                    item["item_id"]: item for item in report["release_judgment"]["unresolved_audit_summary"]
                }
                self.assertEqual(unresolved_items["github_live_path"]["status"], "implemented")
                self.assertEqual(unresolved_items["product_hunt_deferred_boundary"]["status"], "implemented")
                self.assertTrue(unresolved_items["phase1_exit_checklist_product_hunt_live_cycle"]["blocks_release"])
                self.assertEqual(
                    report["manual_audit_preparation"]["screening_status_queues"]["approved_for_staging"]["sample_count"],
                    1,
                )
                self.assertTrue(report["dashboard_reconciliation"]["all_passed"])

    def test_phase1_g_audit_ready_report_writer_persists_json_artifact(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            output_path = candidate_workspace / "phase1_g_audit_ready_report.json"

            from shutil import copytree

            copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                mart = build_default_mart(config)
                report = write_phase1_g_audit_ready_report(config, mart=mart, output_path=output_path)

                written = load_json(output_path)
                self.assertEqual(written["report_type"], "phase1_g_audit_ready_report")
                self.assertEqual(written["gate_status"], report["gate_status"])


if __name__ == "__main__":
    unittest.main()
