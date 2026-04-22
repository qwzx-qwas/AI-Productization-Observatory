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
                self.assertEqual(report["gate_status"]["product_hunt_phase1_exit_gate"], "deferred_not_current_gate")
                self.assertEqual(report["gate_status"]["machine_pre_audit"], "audit-ready")
                self.assertEqual(report["gate_status"]["human_sampled_verdict"], "pending")
                self.assertEqual(report["gate_status"]["owner_review_package"], "owner-review-ready")
                self.assertEqual(report["release_judgment"]["judgment"], "conditional-go")
                self.assertTrue(report["release_judgment"]["owner_required_signoff"])
                self.assertIn("audit-ready / owner-review-ready / conditional-go", report["report_title"])
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
                self.assertEqual(unresolved_items["product_hunt_phase1_exit_gate"]["status"], "deferred_not_current_gate")
                self.assertFalse(unresolved_items["product_hunt_phase1_exit_gate"]["blocks_machine_judgment"])
                self.assertEqual(
                    report["audit_workflow"]["taxonomy_audit"]["machine_pre_audit"]["status"],
                    "passed",
                )
                self.assertEqual(
                    report["audit_workflow"]["taxonomy_audit"]["human_sampled_verdict"]["status"],
                    "pending",
                )
                self.assertEqual(
                    report["audit_workflow"]["screening_status_queues"]["approved_for_staging"]["sample_count"],
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

    def test_phase1_g_audit_ready_report_preserves_manual_writebacks(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            output_path = candidate_workspace / "phase1_g_audit_ready_report.json"

            from shutil import copytree

            copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                manual_report = {
                    "audit_workflow": {
                        "merge_spot_check": {
                            "human_sampled_verdict": {
                                "status": "completed",
                                "review_verdict": "accept",
                                "sampled_count": 0,
                                "sampled_method": "targeted_merge_risk_review",
                                "reviewer_notes": "Accept: no merge-risk cases were materialized in this baseline, so the empty merge sample set is acceptable for this release package.",
                            },
                            "owner_signoff": {
                                "status": "approved",
                                "signoff_by": "project_owner",
                                "signoff_at": "2026-04-21T12:00:00Z",
                                "signoff_notes": "Owner approved the merge spot-check baseline for this release package.",
                            },
                        },
                        "taxonomy_audit": {
                            "human_sampled_verdict": {
                                "status": "completed",
                                "review_verdict": "accept",
                                "sampled_count": 3,
                                "sampled_method": "stratified_top_category_sampling",
                                "reviewer_notes": "Accept: the sampled taxonomy labels remain within the current audit boundary.",
                            },
                            "owner_signoff": {
                                "status": "approved",
                                "signoff_by": "project_owner",
                                "signoff_at": "2026-04-21T12:01:00Z",
                                "signoff_notes": "Owner approved taxonomy audit outcomes.",
                            },
                        },
                        "score_audit": {
                            "human_sampled_verdict": {
                                "status": "completed",
                                "review_verdict": "accept",
                                "sampled_count": 2,
                                "sampled_method": "targeted_high_signal_score_sampling",
                                "reviewer_notes": "Accept: the sampled score outcomes remain within the current audit boundary.",
                            },
                            "owner_signoff": {
                                "status": "approved",
                                "signoff_by": "project_owner",
                                "signoff_at": "2026-04-21T12:02:00Z",
                                "signoff_notes": "Owner approved score audit outcomes.",
                            },
                        },
                        "attention_audit": {
                            "human_sampled_verdict": {
                                "status": "completed",
                                "review_verdict": "accept",
                                "sampled_count": 2,
                                "sampled_method": "stratified_attention_band_sampling",
                                "reviewer_notes": "Accept: the sampled attention audit outcomes remain within the current audit boundary.",
                            },
                            "owner_signoff": {
                                "status": "approved",
                                "signoff_by": "project_owner",
                                "signoff_at": "2026-04-21T12:03:00Z",
                                "signoff_notes": "Owner approved attention audit outcomes.",
                            },
                        },
                        "unresolved_audit": {
                            "human_sampled_verdict": {
                                "status": "completed",
                                "review_verdict": "accept",
                                "sampled_count": 1,
                                "sampled_method": "full_unresolved_registry_review",
                                "reviewer_notes": "Accept: the sampled unresolved audit outcomes remain within the current audit boundary.",
                            },
                            "owner_signoff": {
                                "status": "approved",
                                "signoff_by": "project_owner",
                                "signoff_at": "2026-04-21T12:04:00Z",
                                "signoff_notes": "Owner approved unresolved audit outcomes.",
                            },
                        },
                    },
                    "release_owner_signoff": {
                        "status": "approved",
                        "signoff_by": "project_owner",
                        "signoff_at": "2026-04-21T12:05:00Z",
                        "signoff_notes": "Owner approved the final Phase1-G merge/release decision.",
                    },
                }
                dump_json(output_path, manual_report)

                mart = build_default_mart(config)
                report = build_phase1_g_audit_ready_report(config, mart=mart)

                self.assertEqual(report["audit_workflow"]["taxonomy_audit"]["human_sampled_verdict"]["status"], "completed")
                self.assertEqual(report["audit_workflow"]["taxonomy_audit"]["human_sampled_verdict"]["review_verdict"], "accept")
                self.assertEqual(report["audit_workflow"]["taxonomy_audit"]["owner_signoff"]["status"], "approved")
                self.assertEqual(report["gate_status"]["human_sampled_verdict"], "completed")
                self.assertEqual(report["gate_status"]["owner_signoff"], "approved")
                self.assertEqual(report["release_owner_signoff"]["status"], "approved")
                self.assertEqual(report["release_judgment"]["judgment"], "go")
                self.assertIn("Phase1-G audit-ready / owner-review-ready / go", report["report_title"])


if __name__ == "__main__":
    unittest.main()
