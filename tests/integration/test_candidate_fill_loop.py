from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.config import candidate_id
from src.candidate_prescreen.controller import FillControllerOptions, fill_gold_set_staging_until_complete, run_one_fill_iteration
from src.candidate_prescreen.reviewer import CandidateReviewDecision
from src.candidate_prescreen.staging import summarize_staging_progress
from src.candidate_prescreen.workflow import run_candidate_prescreen
from src.cli import validate_gold_set
from src.common.errors import ProcessingError
from src.common.files import dump_json, dump_yaml, load_yaml, utc_now_iso
from tests.helpers import REPO_ROOT, temp_config


class CandidateFillLoopIntegrationTests(unittest.TestCase):
    def test_run_one_fill_iteration_reviews_existing_workspace_candidate_and_handoffs(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)
            review_fixture_path = root / "review_fixture.json"

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                before_progress = summarize_staging_progress(staging_dir, target_file_count=20, per_file_target_slots=15)
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )
                candidate_record = load_yaml(paths[0])
                dump_json(
                    review_fixture_path,
                    {
                        "responses": {
                            candidate_record["candidate_id"]: {
                                "suggested_review_status": "approved_for_staging",
                                "rationale": "The repo shows a clear end-user support product signal with sufficient evidence.",
                                "evidence_sufficiency": "sufficient",
                                "boundary_notes": [],
                            }
                        }
                    },
                )

                event = run_one_fill_iteration(
                    config,
                    options=FillControllerOptions(review_fixture_path=review_fixture_path),
                    iteration=1,
                    cursor={
                        "source_code": "github",
                        "current_window": "2026-03-01..2026-03-08",
                        "next_query_index": 0,
                        "query_slice_ids": ["qf_agent"],
                        "live_runs": 0,
                    },
                )

                self.assertEqual(event["staging_progress_after"]["total_filled"], before_progress.total_filled + 1)
                self.assertEqual(len(event["handoff_results"]), 1)
                self.assertEqual(event["handoff_results"][0]["sample_slot_id"], before_progress.next_empty_slot.sample_slot_id)

                updated_record = load_yaml(paths[0])
                self.assertEqual(updated_record["human_review_status"], "approved_for_staging")
                self.assertEqual(updated_record["staging_handoff"]["status"], "written")

                status, sample_count = validate_gold_set(config)
                self.assertEqual(status, "stub")
                self.assertEqual(sample_count, 0)

    def test_run_one_fill_iteration_falls_back_to_live_discovery_when_workspace_is_empty(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)
            review_fixture_path = root / "review_fixture.json"

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                before_progress = summarize_staging_progress(staging_dir, target_file_count=20, per_file_target_slots=15)
                live_candidate_id = candidate_id("github", "2026-03-01..2026-03-08", "qf_agent", "987654321")
                dump_json(
                    review_fixture_path,
                    {
                        "responses": {
                            live_candidate_id: {
                                "suggested_review_status": "approved_for_staging",
                                "rationale": "The repo summary and excerpt are strong enough for staging.",
                                "evidence_sufficiency": "sufficient",
                                "boundary_notes": [],
                            }
                        }
                    },
                )

                event = run_one_fill_iteration(
                    config,
                    options=FillControllerOptions(
                        initial_window="2026-03-01..2026-03-08",
                        discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                        llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                        review_fixture_path=review_fixture_path,
                    ),
                    iteration=1,
                    cursor={
                        "source_code": "github",
                        "current_window": "2026-03-01..2026-03-08",
                        "next_query_index": 0,
                        "query_slice_ids": ["qf_agent"],
                        "live_runs": 0,
                    },
                )

                self.assertEqual(event["live_fetch"]["query_slice_id"], "qf_agent")
                self.assertEqual(event["staging_progress_after"]["total_filled"], before_progress.total_filled + 1)
                self.assertEqual(len(event["handoff_results"]), 1)

    def test_fill_loop_exits_when_custom_target_is_already_complete(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            staging_dir.mkdir(parents=True, exist_ok=True)

            sample = load_yaml(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging" / "gold_set_300_staging_batch_01_samples_001_015.yaml")["samples"][0]
            sample["sample_id"] = "cand_complete_001"
            sample["current_state"] = "candidate_approved_for_annotation"
            sample["staged_from_candidate_prescreen_at"] = utc_now_iso()
            sample["staged_from_candidate_prescreen_path"] = str(candidate_workspace / "github" / "2026-03-01_2026-03-08" / "cand_complete_001.yaml")
            dump_yaml(
                staging_dir / "gold_set_300_staging_batch_01_samples_001_001.yaml",
                {
                    "document_id": "gold_set_300_staging_batch_01",
                    "document_purpose": "test",
                    "coverage_scope": "test",
                    "status_boundary": "staging-only",
                    "future_formal_target": "gold_set/gold_set_300/",
                    "samples": [sample],
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                result = fill_gold_set_staging_until_complete(
                    config,
                    options=FillControllerOptions(
                        target_total_filled=1,
                        target_file_count=1,
                        target_slots_per_file=1,
                        max_iterations=1,
                    ),
                )

                self.assertEqual(result.iterations, 0)
                self.assertEqual(result.total_filled, 1)
                self.assertTrue(Path(result.audit_log_path).exists())
                progress = summarize_staging_progress(staging_dir, target_file_count=1, per_file_target_slots=1)
                self.assertTrue(progress.is_complete)

    def test_run_one_fill_iteration_continues_after_retryable_reviewer_failure(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                before_progress = summarize_staging_progress(staging_dir, target_file_count=20, per_file_target_slots=15)
                existing_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )
                existing_record = load_yaml(existing_paths[0])
                second_candidate_id = "cand_retry_peer_001"
                second_candidate_path = existing_paths[0].with_name(f"{second_candidate_id}.yaml")
                second_record = dict(existing_record)
                second_record["candidate_id"] = second_candidate_id
                second_record["updated_at"] = utc_now_iso()
                dump_yaml(second_candidate_path, second_record)

                reviewer_side_effects = [
                    ProcessingError("dependency_unavailable", "Reviewer relay request upstream unavailable with HTTP 502"),
                    CandidateReviewDecision(
                        suggested_review_status="approved_for_staging",
                        rationale="The live candidate has sufficient end-user product evidence for staging.",
                        evidence_sufficiency="sufficient",
                        boundary_notes=[],
                        channel_metadata={
                            "prompt_version": "candidate_first_pass_reviewer_v1",
                            "routing_version": "route_candidate_first_pass_reviewer_v1",
                            "relay_client_version": "relay_candidate_first_pass_reviewer_v1",
                            "model": "fixture-reviewer",
                            "transport": "http_json_relay",
                            "request_id": None,
                        },
                    ),
                ]

                with patch(
                    "src.candidate_prescreen.controller.review_candidate_with_llm",
                    side_effect=reviewer_side_effects,
                ):
                    event = run_one_fill_iteration(
                        config,
                        options=FillControllerOptions(initial_window="2026-03-01..2026-03-08"),
                        iteration=1,
                        cursor={
                            "source_code": "github",
                            "current_window": "2026-03-01..2026-03-08",
                            "next_query_index": 0,
                            "query_slice_ids": ["qf_agent"],
                            "live_runs": 0,
                        },
                    )

                self.assertEqual(event["staging_progress_after"]["total_filled"], before_progress.total_filled + 1)
                self.assertEqual(len(event["handoff_results"]), 1)
                self.assertEqual(event["handoff_results"][0]["candidate_id"], second_candidate_id)
                self.assertEqual(event["review_results"][0]["candidate_id"], existing_record["candidate_id"])
                self.assertEqual(
                    event["review_results"][0]["reviewer_failure"]["error_type"],
                    "dependency_unavailable",
                )
                self.assertTrue(event["review_results"][0]["reviewer_failure"]["retryable"])

                updated_existing_record = load_yaml(existing_paths[0])
                self.assertEqual(updated_existing_record["human_review_status"], "pending_first_pass")
                self.assertIsNone(updated_existing_record["human_reviewed_at"])
