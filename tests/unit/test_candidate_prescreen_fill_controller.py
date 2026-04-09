from __future__ import annotations

import json
import shutil
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.config import load_candidate_prescreen_config
from src.candidate_prescreen.fill_controller import (
    AUDIT_LOG_FILE_NAME,
    _process_existing_workspace_candidates,
    run_one_fill_iteration,
    fill_gold_set_staging_until_complete,
    review_candidate_with_llm,
)
from src.candidate_prescreen.fill_controller import LiveDiscoveryCursor
from src.candidate_prescreen.staging import (
    EXPECTED_TOTAL_SLOTS,
    dedupe_staging_semantic_duplicates,
    staging_progress,
    validate_staging_workspace,
)
from src.candidate_prescreen.workflow import run_candidate_prescreen
from src.common.errors import ConfigError, ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from tests.helpers import REPO_ROOT, temp_config


def _success_outcome(normalized_result: dict[str, object]) -> dict[str, object]:
    return {
        "transport_status": "succeeded",
        "provider_response_status": "succeeded",
        "content_status": "succeeded",
        "schema_status": "succeeded",
        "business_status": "succeeded",
        "request_id": "req_test_123",
        "http_status": 200,
        "mapped_error_type": None,
        "failure_code": None,
        "failure_message": None,
        "normalized_result": normalized_result,
    }


def _failed_outcome(*, error_type: str, failure_code: str, failure_message: str) -> dict[str, object]:
    return {
        "transport_status": "succeeded",
        "provider_response_status": "succeeded",
        "content_status": "failed" if failure_code == "provider_empty_completion" else "succeeded",
        "schema_status": "failed" if failure_code != "provider_empty_completion" else "failed",
        "business_status": "failed",
        "request_id": "req_test_123",
        "http_status": 200,
        "mapped_error_type": error_type,
        "failure_code": failure_code,
        "failure_message": failure_message,
        "normalized_result": None,
    }


def _prefill_remaining_slots(staging_dir: Path, *, keep_empty_slots: int) -> None:
    template_sample = None
    template_candidate_ref = None
    template_source_ref = None
    empty_counter = 0
    synthetic_counter = 0
    for staging_path in sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml")):
        payload = load_yaml(staging_path)
        samples = payload["samples"]
        for sample in samples:
            if sample.get("sample_id") and template_sample is None:
                template_sample = dict(sample)
                template_candidate_ref = dict(sample["candidate_prescreen_ref"])
                template_source_ref = dict(sample["source_record_refs"][0])
            if sample.get("sample_id"):
                continue
            empty_counter += 1
            if empty_counter <= keep_empty_slots:
                continue
            synthetic_counter += 1
            slot_index = sample["slot_index"]
            sample_slot_id = sample["sample_slot_id"]
            sample.update(dict(template_sample))
            sample["slot_index"] = slot_index
            sample["sample_slot_id"] = sample_slot_id
            synthetic_sample_id = f"prefill_candidate_{synthetic_counter:03d}"
            sample["sample_id"] = synthetic_sample_id
            sample["candidate_prescreen_ref"] = dict(template_candidate_ref)
            sample["candidate_prescreen_ref"]["candidate_id"] = synthetic_sample_id
            sample["source_record_refs"] = [dict(template_source_ref)]
            sample["source_record_refs"][0]["candidate_id"] = synthetic_sample_id
            sample["source_record_refs"][0]["external_id"] = f"prefill_external_{synthetic_counter:03d}"
            sample["source_record_refs"][0]["canonical_url"] = f"https://example.com/prefill/{synthetic_counter:03d}"
            sample["source_record_refs"][0]["candidate_document_path"] = (
                f"/tmp/prefill_candidate_{synthetic_counter:03d}.yaml"
            )
        dump_yaml(staging_path, payload)


def _copy_clean_staging_dir(staging_dir: Path) -> None:
    shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)
    dedupe_staging_semantic_duplicates(staging_dir)


class CandidatePrescreenFillControllerUnitTests(unittest.TestCase):
    def test_staging_progress_reports_current_workspace_shape(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)

            progress = staging_progress(staging_dir)

            self.assertEqual(progress["total_slots"], EXPECTED_TOTAL_SLOTS)
            self.assertEqual(len(progress["documents"]), 20)
            self.assertFalse(progress["is_complete"])
            self.assertGreater(progress["total_filled"], 0)
            self.assertLess(progress["total_filled"], EXPECTED_TOTAL_SLOTS)
            self.assertIsNotNone(progress["next_open_slot"])

    def test_validate_staging_workspace_accepts_complete_prefilled_shape(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            _prefill_remaining_slots(staging_dir, keep_empty_slots=0)

            progress = validate_staging_workspace(staging_dir)

            self.assertTrue(progress["is_complete"])
            self.assertEqual(progress["total_filled"], EXPECTED_TOTAL_SLOTS)
            self.assertIsNone(progress["next_open_slot"])

    def test_review_candidate_with_llm_falls_back_to_existing_prescreen(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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

                with patch(
                    "src.candidate_prescreen.fill_controller.screen_candidate",
                    side_effect=ProcessingError("provider_timeout", "simulated relay timeout"),
                ):
                    review_result = review_candidate_with_llm(
                        config,
                        record,
                        llm_fixture_path=None,
                        request_interval_seconds=0,
                        retry_sleep_seconds=0,
                    )

                self.assertEqual(review_result["review_source"], "existing_llm_prescreen")
                self.assertEqual(review_result["suggested_review_status"], "approved_for_staging")

    def test_review_candidate_with_llm_reuses_existing_prescreen_before_relay_retry(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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

                with patch("src.candidate_prescreen.fill_controller.screen_candidate") as screen_candidate_mock:
                    review_result = review_candidate_with_llm(
                        config,
                        record,
                        llm_fixture_path=None,
                        request_interval_seconds=0,
                        retry_sleep_seconds=0,
                    )

                screen_candidate_mock.assert_not_called()
                self.assertEqual(review_result["review_source"], "existing_llm_prescreen")
                self.assertEqual(review_result["suggested_review_status"], "approved_for_staging")

    def test_process_existing_workspace_candidates_persists_fresh_success_snapshot_before_review_derivation(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "previous relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                dump_yaml(paths[0], record)

                successful_card = dict(record["llm_prescreen"])
                successful_card.update(
                    {
                        "in_observatory_scope": True,
                        "reason": "Fresh relay rerun recovered a consumable review card.",
                        "decision_snapshot": "Recommend candidate_pool because the workflow evidence is clear.",
                        "scope_boundary_note": "The rerun confirms an end-user AI product workflow.",
                        "source_evidence_summary": ["Recovered product evidence from the rerun."],
                        "evidence_anchors": [
                            {
                                "anchor_rank": 1,
                                "evidence_text": "Recovered product evidence from the rerun.",
                                "evidence_source_field": "raw_evidence_excerpt",
                                "why_it_matters": "Shows a consumable first-pass review signal.",
                            }
                        ],
                        "review_focus_points": [
                            "Confirm README still matches the shipped workflow.",
                            "Verify the candidate remains support-oriented.",
                        ],
                        "uncertainty_points": [],
                        "recommend_candidate_pool": True,
                        "recommended_action": "candidate_pool",
                        "confidence_summary": {
                            "scope_confidence": "high",
                            "taxonomy_confidence": "medium",
                            "persona_confidence": "medium",
                        },
                        "handoff_readiness_hint": {
                            "suggested_action": "candidate_pool",
                            "rationale": "The recovered output is consumable.",
                        },
                        "persona_candidates": [
                            {
                                "persona_code": "support_agent",
                                "confidence_rank": 1,
                                "rationale": "Targets support workflows.",
                                "supporting_evidence_anchors": [1],
                            }
                        ],
                        "taxonomy_hints": {
                            "primary_category_code": "JTBD_SALES_SUPPORT",
                            "secondary_category_code": None,
                            "primary_persona_code": "support_agent",
                            "delivery_form_code": None,
                            "main_category_candidate": {
                                "category_code": "JTBD_SALES_SUPPORT",
                                "rationale": "Support workflow evidence dominates.",
                                "supporting_evidence_anchors": [1],
                            },
                            "adjacent_category_candidate": {
                                "category_code": "JTBD_KNOWLEDGE_ASSISTANCE",
                                "rationale_for_similarity": "Some assistant behavior overlaps with knowledge assistance.",
                                "supporting_evidence_anchors": [1],
                            },
                            "adjacent_category_rejected_reason": "Support execution is still the stronger fit.",
                        },
                        "assessment_hints": {
                            "evidence_strength": "high",
                            "build_evidence_band": "high",
                            "need_clarity_band": "low",
                            "unresolved_risk": "low",
                        },
                        "channel_metadata": {
                            "prompt_version": "candidate_prescreener_v1",
                            "routing_version": "route_candidate_prescreener_v1",
                            "relay_client_version": "relay_candidate_prescreener_v1",
                            "model": "fixture-relay",
                            "transport": "http_json_relay",
                            "request_id": "req_test_123",
                        },
                        "error_type": None,
                        "error_message": None,
                    }
                )

                with patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    return_value={"request_url": "https://relay.example.test"},
                ), patch(
                    "src.candidate_prescreen.fill_controller.screen_candidate",
                    return_value=_success_outcome(successful_card),
                ):
                    review_results, handoff_result = _process_existing_workspace_candidates(
                        config,
                        llm_fixture_path=None,
                        note_templates=note_templates,
                        request_interval_seconds=0,
                        retry_sleep_seconds=0,
                    )

                refreshed = load_yaml(paths[0])
                self.assertEqual(refreshed["llm_prescreen"]["status"], "succeeded")
                self.assertEqual(refreshed["llm_prescreen"]["reason"], "Fresh relay rerun recovered a consumable review card.")
                self.assertEqual(review_results[0]["review_source"], "fresh_llm_review")

    def test_process_existing_workspace_candidates_keeps_provider_empty_completion_failed(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "previous relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                dump_yaml(paths[0], record)

                with patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    return_value={"request_url": "https://relay.example.test"},
                ), patch(
                    "src.candidate_prescreen.fill_controller.screen_candidate",
                    return_value=_failed_outcome(
                        error_type="dependency_unavailable",
                        failure_code="provider_empty_completion",
                        failure_message="Relay returned an empty completion.",
                    ),
                ):
                    review_results, handoff_result = _process_existing_workspace_candidates(
                        config,
                        llm_fixture_path=None,
                        note_templates=note_templates,
                        request_interval_seconds=0,
                        retry_sleep_seconds=0,
                    )

                refreshed = load_yaml(paths[0])
                self.assertIsNone(handoff_result)
                self.assertEqual(refreshed["llm_prescreen"]["status"], "failed")
                self.assertEqual(refreshed["llm_prescreen"]["error_type"], "dependency_unavailable")
                self.assertEqual(review_results[0]["failure_code"], "provider_empty_completion")

    def test_run_one_fill_iteration_blocks_on_fresh_parse_failure_outcome(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "previous relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                dump_yaml(paths[0], record)

                workflow_config = load_candidate_prescreen_config(config.config_dir)
                cursor = LiveDiscoveryCursor.from_workflow(
                    workflow_config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                )
                with patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    return_value={"request_url": "https://relay.example.test"},
                ), patch(
                    "src.candidate_prescreen.fill_controller.screen_candidate",
                    return_value=_failed_outcome(
                        error_type="parse_failure",
                        failure_code="parse_failure",
                        failure_message="Relay returned invalid JSON.",
                    ),
                ), patch("src.candidate_prescreen.fill_controller.run_candidate_prescreen") as run_candidate_prescreen_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                        discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                        llm_fixture_path=None,
                    )

                run_candidate_prescreen_mock.assert_not_called()
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "parse_failure")
                self.assertEqual(summary["live_discovery"]["failure"]["failed_step"], "existing_workspace_llm_review")

    def test_run_one_fill_iteration_blocks_on_fresh_output_schema_validation_failure(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "previous relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                dump_yaml(paths[0], record)

                workflow_config = load_candidate_prescreen_config(config.config_dir)
                cursor = LiveDiscoveryCursor.from_workflow(
                    workflow_config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                )
                with patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    return_value={"request_url": "https://relay.example.test"},
                ), patch(
                    "src.candidate_prescreen.fill_controller.screen_candidate",
                    return_value=_failed_outcome(
                        error_type="json_schema_validation_failed",
                        failure_code="output_schema_validation_failed",
                        failure_message="Normalized review card is not consumable.",
                    ),
                ), patch("src.candidate_prescreen.fill_controller.run_candidate_prescreen") as run_candidate_prescreen_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                        discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                        llm_fixture_path=None,
                    )

                run_candidate_prescreen_mock.assert_not_called()
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "json_schema_validation_failed")
                self.assertEqual(summary["live_discovery"]["failure"]["failed_step"], "existing_workspace_llm_review")

    def test_review_candidate_with_llm_fails_fast_when_relay_preflight_fails(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "previous outage"
                dump_yaml(paths[0], record)

                with patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    side_effect=ConfigError("relay config invalid"),
                ), patch("src.candidate_prescreen.fill_controller.screen_candidate") as screen_candidate_mock:
                    with self.assertRaises(ProcessingError) as ctx:
                        review_candidate_with_llm(
                            config,
                            record,
                            llm_fixture_path=None,
                            request_interval_seconds=0,
                            retry_sleep_seconds=30,
                        )

                screen_candidate_mock.assert_not_called()
                self.assertEqual(ctx.exception.error_type, "relay_preflight_failed")

    def test_fill_controller_waits_after_retryable_failure_and_records_audit(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                initial_progress = {
                    "total_filled": 44,
                    "total_slots": EXPECTED_TOTAL_SLOTS,
                    "total_empty": EXPECTED_TOTAL_SLOTS - 44,
                    "is_complete": False,
                    "next_open_slot": {"sample_slot_id": "GS300-045"},
                    "documents": [],
                }
                after_retry = dict(initial_progress)
                after_success = dict(initial_progress)
                after_success["total_filled"] = EXPECTED_TOTAL_SLOTS
                after_success["total_empty"] = 0
                after_success["is_complete"] = True
                after_success["next_open_slot"] = None

                retryable_summary = {
                    "iteration_completed_at": "2026-04-03T00:00:00Z",
                    "progress_before": {"total_filled": 44},
                    "progress_after": {"total_filled": 44},
                    "workspace_candidate_source": [],
                    "review_results": [
                        {
                            "candidate_id": "cand_retryable",
                            "review_status": "pending_first_pass",
                            "reason": "relay timed out",
                            "review_source": "llm_review_processing_error",
                            "error_type": "provider_timeout",
                        }
                    ],
                    "handoff": None,
                    "live_discovery": None,
                    "validation": {
                        "candidate_workspace_document_count": 1,
                        "staging_total_filled": 44,
                    },
                }
                success_summary = {
                    "iteration_completed_at": "2026-04-03T00:01:00Z",
                    "progress_before": {"total_filled": 44},
                    "progress_after": {"total_filled": EXPECTED_TOTAL_SLOTS},
                    "workspace_candidate_source": [],
                    "review_results": [],
                    "handoff": {"status": "written", "candidate_id": "cand_success"},
                    "live_discovery": None,
                    "validation": {
                        "candidate_workspace_document_count": 1,
                        "staging_total_filled": EXPECTED_TOTAL_SLOTS,
                    },
                }
                slept: list[float] = []
                with patch(
                    "src.candidate_prescreen.fill_controller.validate_staging_workspace",
                    return_value=initial_progress,
                ), patch(
                    "src.candidate_prescreen.fill_controller.staging_progress",
                    side_effect=[after_retry, after_success],
                ), patch(
                    "src.candidate_prescreen.fill_controller.run_one_fill_iteration",
                    side_effect=[retryable_summary, success_summary],
                ):
                    summary = fill_gold_set_staging_until_complete(
                        config,
                        source_code="github",
                        initial_window="2026-03-29..2026-04-02",
                        query_slice_id="qf_agent",
                        provider_request_interval_seconds=60,
                        retry_sleep_seconds=9,
                        sleep_fn=slept.append,
                    )

                self.assertEqual(summary["status"], "completed")
                self.assertEqual(slept, [9])
                audit_log_text = Path(summary["audit_log_path"]).read_text(encoding="utf-8")
                self.assertIn("\"event\": \"wait\"", audit_log_text)
                self.assertIn("\"wait_kind\": \"failure_backoff\"", audit_log_text)
                self.assertIn("\"wait_seconds\": 9", audit_log_text)

    def test_fill_controller_blocks_on_terminal_live_failure(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                initial_progress = {
                    "total_filled": 44,
                    "total_slots": EXPECTED_TOTAL_SLOTS,
                    "total_empty": EXPECTED_TOTAL_SLOTS - 44,
                    "is_complete": False,
                    "next_open_slot": {"sample_slot_id": "GS300-045"},
                    "documents": [],
                }
                terminal_summary = {
                    "iteration_completed_at": "2026-04-03T00:00:00Z",
                    "progress_before": {"total_filled": 44},
                    "progress_after": {"total_filled": 44},
                    "workspace_candidate_source": [],
                    "review_results": [],
                    "handoff": None,
                    "live_discovery": {
                        "failure": {
                            "failed_step": "run_candidate_prescreen",
                            "error_type": "schema_drift",
                            "reason": "upstream response contract drifted",
                            "safe_to_retry": False,
                        }
                    },
                    "validation": {
                        "candidate_workspace_document_count": 0,
                        "staging_total_filled": 44,
                    },
                }
                with patch(
                    "src.candidate_prescreen.fill_controller.validate_staging_workspace",
                    return_value=initial_progress,
                ), patch(
                    "src.candidate_prescreen.fill_controller.staging_progress",
                    return_value=initial_progress,
                ), patch(
                    "src.candidate_prescreen.fill_controller.run_one_fill_iteration",
                    return_value=terminal_summary,
                ):
                    summary = fill_gold_set_staging_until_complete(
                        config,
                        source_code="github",
                        initial_window="2026-03-29..2026-04-02",
                        query_slice_id="qf_agent",
                        provider_request_interval_seconds=60,
                        retry_sleep_seconds=9,
                    )

                self.assertEqual(summary["status"], "blocked")
                self.assertEqual(summary["blocked_error_type"], "schema_drift")

    def test_existing_workspace_retryable_failure_enters_cooldown_before_next_review_attempt(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "temporary relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                record["staging_handoff"] = {
                    "status": "not_started",
                    "staging_document_path": None,
                    "sample_slot_id": None,
                    "sample_id": None,
                    "blocking_items": [],
                    "last_attempted_at": None,
                }
                record["updated_at"] = utc_now_iso()
                dump_yaml(paths[0], record)

                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])

                with patch("src.candidate_prescreen.fill_controller.review_candidate_with_llm") as review_candidate_mock:
                    review_results, handoff_result = _process_existing_workspace_candidates(
                        config,
                        llm_fixture_path=None,
                        note_templates=note_templates,
                        request_interval_seconds=60,
                        retry_sleep_seconds=30,
                    )

                review_candidate_mock.assert_not_called()
                self.assertIsNone(handoff_result)
                self.assertEqual(len(review_results), 1)
                self.assertEqual(review_results[0]["review_source"], "retry_cooldown")
                self.assertNotIn("error_type", review_results[0])

    def test_existing_workspace_semantic_duplicate_handoff_is_blocked_without_crashing(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                workflow_config = load_candidate_prescreen_config(config.config_dir)
                note_templates = dict(workflow_config["workspace"]["human_review_note_templates"])
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
                for staging_path in sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml")):
                    payload = load_yaml(staging_path)
                    source_sample = next((sample for sample in payload["samples"] if sample.get("sample_id")), None)
                    if source_sample is None:
                        continue
                    source_ref = source_sample["source_record_refs"][0]
                    record["source"] = "github"
                    record["source_id"] = source_ref["source_id"]
                    record["source_window"] = "2026-04-01..2026-04-06"
                    record["external_id"] = source_ref["external_id"]
                    record["canonical_url"] = source_ref["canonical_url"]
                    record["human_review_status"] = "approved_for_staging"
                    record["human_review_note_template_key"] = "approved"
                    record["human_review_notes"] = note_templates["approved"]
                    record["human_reviewed_at"] = utc_now_iso()
                    record["staging_handoff"] = {
                        "status": "not_started",
                        "staging_document_path": None,
                        "sample_slot_id": None,
                        "sample_id": None,
                        "blocking_items": [],
                        "last_attempted_at": None,
                    }
                    dump_yaml(paths[0], record)
                    break

                review_results, handoff_result = _process_existing_workspace_candidates(
                    config,
                    llm_fixture_path=None,
                    note_templates=note_templates,
                    request_interval_seconds=0,
                    retry_sleep_seconds=0,
                )

                self.assertEqual(review_results, [])
                self.assertIsNone(handoff_result)
                refreshed = load_yaml(paths[0])
                self.assertEqual(refreshed["staging_handoff"]["status"], "blocked")
                self.assertIn(
                    "Semantic duplicate source URL already present in staging",
                    refreshed["staging_handoff"]["blocking_items"][0],
                )

    def test_fill_controller_marks_previous_unfinished_run_when_new_run_starts(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                audit_log_path = config.candidate_workspace_dir / AUDIT_LOG_FILE_NAME
                audit_log_path.parent.mkdir(parents=True, exist_ok=True)
                audit_log_path.write_text(
                    json.dumps(
                        {
                            "event": "initialize",
                            "run_id": "fill_run_stale",
                            "recorded_at": "2026-04-03T00:00:00Z",
                        },
                        ensure_ascii=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                complete_progress = {
                    "total_filled": EXPECTED_TOTAL_SLOTS,
                    "total_slots": EXPECTED_TOTAL_SLOTS,
                    "total_empty": 0,
                    "is_complete": True,
                    "next_open_slot": None,
                    "documents": [],
                }

                with patch("src.candidate_prescreen.fill_controller.validate_staging_workspace", return_value=complete_progress):
                    summary = fill_gold_set_staging_until_complete(
                        config,
                        source_code="github",
                        initial_window="2026-03-29..2026-04-02",
                        query_slice_id="qf_agent",
                    )

                self.assertEqual(summary["status"], "completed")
                audit_log_text = audit_log_path.read_text(encoding="utf-8")
                self.assertIn("\"event\": \"interrupted_assumed\"", audit_log_text)
                self.assertIn("\"run_id\": \"fill_run_stale\"", audit_log_text)

    def test_run_one_fill_iteration_stops_when_cursor_moves_into_future_window(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                cursor = LiveDiscoveryCursor(
                    source_code="github",
                    query_slice_ids=["qf_agent"],
                    window_start=date(2026, 4, 7),
                    window_end=date(2026, 4, 13),
                )
                with patch(
                    "src.candidate_prescreen.fill_controller._process_existing_workspace_candidates",
                    return_value=([], None),
                ), patch(
                    "src.candidate_prescreen.fill_controller._current_date",
                    return_value=date(2026, 4, 6),
                ), patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                ) as relay_preflight_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                    )

                relay_preflight_mock.assert_not_called()
                self.assertEqual(summary["handoff"], None)
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "future_window_exhausted")

    def test_run_one_fill_iteration_stops_when_window_end_exceeds_today(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                cursor = LiveDiscoveryCursor(
                    source_code="github",
                    query_slice_ids=["qf_agent"],
                    window_start=date(2026, 4, 7),
                    window_end=date(2026, 4, 13),
                )
                with patch(
                    "src.candidate_prescreen.fill_controller._process_existing_workspace_candidates",
                    return_value=([], None),
                ), patch(
                    "src.candidate_prescreen.fill_controller._current_date",
                    return_value=date(2026, 4, 7),
                ), patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                ) as relay_preflight_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                    )

                relay_preflight_mock.assert_not_called()
                self.assertEqual(summary["handoff"], None)
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "future_window_exhausted")
                self.assertIn("2026-04-07..2026-04-13", summary["live_discovery"]["failure"]["reason"])

    def test_run_one_fill_iteration_blocks_on_existing_terminal_prescreen_failure(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

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
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "schema_drift"
                record["llm_prescreen"]["error_message"] = "preexisting review contract failure"
                dump_yaml(paths[0], record)

                workflow_config = load_candidate_prescreen_config(config.config_dir)
                cursor = LiveDiscoveryCursor.from_workflow(
                    workflow_config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                )
                with patch("src.candidate_prescreen.fill_controller.run_candidate_prescreen") as run_candidate_prescreen_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                        discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                        llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                    )

                run_candidate_prescreen_mock.assert_not_called()
                self.assertIsNone(summary["handoff"])
                self.assertEqual(summary["review_results"][0]["error_type"], "schema_drift")
                self.assertEqual(summary["review_results"][0]["review_source"], "terminal_prescreen_failure")
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "schema_drift")
                self.assertEqual(summary["live_discovery"]["failure"]["failed_step"], "existing_workspace_llm_review")

    def test_run_one_fill_iteration_marks_relay_preflight_failure_before_live_discovery(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            _copy_clean_staging_dir(staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                cursor = LiveDiscoveryCursor(
                    source_code="github",
                    query_slice_ids=["qf_agent"],
                    window_start=date(2026, 3, 31),
                    window_end=date(2026, 4, 6),
                )
                with patch(
                    "src.candidate_prescreen.fill_controller._process_existing_workspace_candidates",
                    return_value=([], None),
                ), patch(
                    "src.candidate_prescreen.fill_controller._current_date",
                    return_value=date(2026, 4, 6),
                ), patch(
                    "src.candidate_prescreen.fill_controller.relay_preflight",
                    side_effect=ConfigError("relay config invalid"),
                ), patch(
                    "src.candidate_prescreen.fill_controller.run_candidate_prescreen",
                ) as run_candidate_prescreen_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                    )

                run_candidate_prescreen_mock.assert_not_called()
                self.assertEqual(summary["handoff"], None)
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "relay_preflight_failed")
