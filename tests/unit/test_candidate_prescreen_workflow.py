from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.config import build_analysis_run_key, build_sample_key
from src.candidate_prescreen.relay import PAYLOAD_BUILDER_VERSION, build_relay_candidate_input
from src.candidate_prescreen.workflow import archive_duplicate_candidate_records, archive_future_window_candidate_records, run_candidate_prescreen
from src.candidate_prescreen.review_card import normalize_llm_result
from src.common.errors import ContractValidationError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from tests.helpers import temp_config


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


class CandidatePrescreenWorkflowUnitTests(unittest.TestCase):
    def test_build_sample_key_is_stable_across_windows_and_query_slices(self) -> None:
        first = build_sample_key("src_github", "https://GitHub.com/example/product/?b=2&a=1#readme")
        second = build_sample_key("src_github", "https://github.com/example/product/?a=1&b=2")

        self.assertEqual(first, second)

    def test_build_analysis_run_key_is_stable_for_the_same_cleaned_input(self) -> None:
        sample_key = build_sample_key("src_github", "https://github.com/example/product")
        cleaned_candidate_input = build_relay_candidate_input(
            {
                "source": "github",
                "source_window": "2026-03-01..2026-03-08",
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Example Product",
                "summary": "AI assistant for support teams.",
                "raw_evidence_excerpt": "Useful product evidence.",
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "time_field": "pushed_at",
            }
        )

        first = build_analysis_run_key(
            sample_key=sample_key,
            cleaned_candidate_input=cleaned_candidate_input,
            prompt_version="candidate_prescreener_v1",
            routing_version="route_candidate_prescreener_v1",
            relay_client_version="relay_candidate_prescreener_v1",
            payload_builder_version=PAYLOAD_BUILDER_VERSION,
        )
        second = build_analysis_run_key(
            sample_key=sample_key,
            cleaned_candidate_input=cleaned_candidate_input,
            prompt_version="candidate_prescreener_v1",
            routing_version="route_candidate_prescreener_v1",
            relay_client_version="relay_candidate_prescreener_v1",
            payload_builder_version=PAYLOAD_BUILDER_VERSION,
        )

        self.assertEqual(first, second)

    def test_run_candidate_prescreen_dedupes_by_normalized_url_across_external_ids(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            first_fixture = root / "fixtures" / "candidate_window_1.json"
            second_fixture = root / "fixtures" / "candidate_window_2.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            first_item = {
                "external_id": "123",
                "canonical_url": "https://GitHub.com/example/product/?b=2&a=1#readme",
                "title": "Example Product",
                "summary": "AI assistant for sales teams and meeting follow-up workflows.",
                "raw_evidence_excerpt": "Assistant workspace for sales call prep, notes, and follow-up tasks.",
                "author_name": "example",
                "linked_homepage_url": "https://example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-08T00:00:00Z",
                "topics": ["agent"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            second_item = dict(first_item)
            second_item["external_id"] = "456"
            second_item["canonical_url"] = "https://github.com/example/product/?a=1&b=2"
            second_item["summary"] = "Updated summary should not create a second candidate doc."
            _write_json(
                first_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [first_item],
                },
            )
            _write_json(
                second_fixture,
                {
                    "source": "github",
                    "window": "2026-03-08..2026-03-15",
                    "query_slice_id": "qf_agent",
                    "items": [second_item],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:123": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                first_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=first_fixture,
                    llm_fixture_path=llm_fixture,
                )
                second_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-08..2026-03-15",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=second_fixture,
                    llm_fixture_path=llm_fixture,
                )

            candidate_docs = sorted(candidate_workspace.rglob("*.yaml"))
            self.assertEqual(len(first_paths), 1)
            self.assertEqual(second_paths, [])
            self.assertEqual(candidate_docs, first_paths)
            record = load_yaml(candidate_docs[0])
            self.assertEqual(record["external_id"], "123")
            self.assertEqual(record["canonical_url"], "https://github.com/example/product?a=1&b=2")

    def test_run_candidate_prescreen_reuses_existing_semantic_candidate_across_windows(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            first_fixture = root / "fixtures" / "candidate_window_1.json"
            second_fixture = root / "fixtures" / "candidate_window_2.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            candidate_item = {
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Example Product",
                "summary": "AI assistant for sales teams and meeting follow-up workflows.",
                "raw_evidence_excerpt": "Assistant workspace for sales call prep, notes, and follow-up tasks.",
                "author_name": "example",
                "linked_homepage_url": "https://example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-08T00:00:00Z",
                "topics": ["agent"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            _write_json(
                first_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [candidate_item],
                },
            )
            updated_item = dict(candidate_item)
            updated_item["summary"] = "AI assistant for sales teams with updated workflow automation."
            updated_item["raw_evidence_excerpt"] = "Assistant workspace for sales call prep, notes, and automated follow-up tasks."
            updated_item["pushed_at"] = "2026-03-15T00:00:00Z"
            _write_json(
                second_fixture,
                {
                    "source": "github",
                    "window": "2026-03-08..2026-03-15",
                    "query_slice_id": "qf_agent",
                    "items": [updated_item],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:123": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                first_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=first_fixture,
                    llm_fixture_path=llm_fixture,
                )
                second_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-08..2026-03-15",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=second_fixture,
                    llm_fixture_path=llm_fixture,
                )

            candidate_docs = sorted(candidate_workspace.rglob("*.yaml"))
            self.assertEqual(len(first_paths), 1)
            self.assertEqual(second_paths, [])
            self.assertEqual(candidate_docs, first_paths)

            record = load_yaml(candidate_docs[0])
            self.assertEqual(record["external_id"], "123")
            self.assertEqual(record["source_window"], "2026-03-01..2026-03-08")
            self.assertEqual(record["summary"], "AI assistant for sales teams and meeting follow-up workflows.")
            self.assertEqual(record["raw_evidence_excerpt"], "Assistant workspace for sales call prep, notes, and follow-up tasks.")

    def test_run_candidate_prescreen_blocks_product_hunt_live_discovery_in_current_phase(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            candidate_workspace = Path(tmp_dir) / "candidate_workspace"

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                with self.assertRaisesRegex(
                    ContractValidationError,
                    "Current-phase live candidate discovery is not enabled for product_hunt",
                ):
                    run_candidate_prescreen(
                        config,
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        query_slice_id="ph_published_launches",
                        limit=1,
                        discovery_fixture_path=None,
                        llm_fixture_path=None,
                    )

    def test_run_candidate_prescreen_rejects_invalid_url_before_writing_candidate_doc(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            discovery_fixture = root / "fixtures" / "candidate_window.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            _write_json(
                discovery_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [
                        {
                            "external_id": "100",
                            "canonical_url": "   ",
                            "title": "Broken URL Candidate",
                            "summary": "Should be rejected before any candidate doc is written.",
                            "raw_evidence_excerpt": "Workspace with empty URL should never enter the writable path.",
                            "author_name": "example",
                            "linked_homepage_url": None,
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-03-08T00:00:00Z",
                            "topics": ["agent"],
                            "language": "Python",
                            "current_metrics_json": {"star_count": 10},
                        },
                        {
                            "external_id": "101",
                            "canonical_url": "https://github.com/example/valid-product",
                            "title": "Valid Product",
                            "summary": "AI assistant for support teams.",
                            "raw_evidence_excerpt": "Support workspace with valid URL should continue through the workflow.",
                            "author_name": "example",
                            "linked_homepage_url": "https://example.com",
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-03-08T00:00:00Z",
                            "topics": ["agent"],
                            "language": "Python",
                            "current_metrics_json": {"star_count": 10},
                        },
                    ],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:101": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                with self.assertLogs("candidate_prescreen_workflow", level="INFO") as captured:
                    written_paths = run_candidate_prescreen(
                        config,
                        source_code="github",
                        window="2026-03-01..2026-03-08",
                        query_slice_id="qf_agent",
                        limit=2,
                        discovery_fixture_path=discovery_fixture,
                        llm_fixture_path=llm_fixture,
                    )

            self.assertEqual(len(written_paths), 1)
            record = load_yaml(written_paths[0])
            self.assertEqual(record["external_id"], "101")
            joined_logs = "\n".join(captured.output)
            self.assertIn("candidate_rejected", joined_logs)
            self.assertIn("invalid_canonical_url", joined_logs)

    def test_archive_duplicate_candidate_records_moves_non_preferred_duplicates_out_of_active_workspace(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:123": fixture_response,
                    },
                },
            )
            first_fixture = root / "fixtures" / "candidate_window_1.json"
            base_item = {
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Example Product",
                "summary": "AI assistant for sales teams and meeting follow-up workflows.",
                "raw_evidence_excerpt": "Assistant workspace for sales call prep, notes, and follow-up tasks.",
                "author_name": "example",
                "linked_homepage_url": "https://example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-08T00:00:00Z",
                "topics": ["agent"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            _write_json(
                first_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [base_item],
                },
            )
            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                first_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=first_fixture,
                    llm_fixture_path=llm_fixture,
                )
                first_record = load_yaml(first_paths[0])
                second_path = candidate_workspace / "github" / "2026-03-08_2026-03-15" / "cand_github_qf_ai_assistant_manualdup.yaml"
                second_record = dict(first_record)
                second_record["candidate_id"] = "cand_github_qf_ai_assistant_manualdup"
                second_record["candidate_batch_id"] = "candidate_batch_github_qf_ai_assistant_2026-03-08_2026-03-15"
                second_record["source_window"] = "2026-03-08..2026-03-15"
                second_record["query_slice_id"] = "qf_ai_assistant"
                second_record["summary"] = "second summary"
                second_record["raw_evidence_excerpt"] = "second evidence"
                second_record["llm_prescreen"]["status"] = "failed"
                second_record["llm_prescreen"]["error_type"] = "network_error"
                second_record["llm_prescreen"]["error_message"] = "temporary"
                second_record["updated_at"] = "2026-03-15T00:00:00Z"
                second_path.parent.mkdir(parents=True, exist_ok=True)
                dump_yaml(second_path, second_record)

                summary = archive_duplicate_candidate_records(config)

            active_docs = sorted(candidate_workspace.rglob("*.yaml"))
            archived_docs = sorted((candidate_workspace / ".duplicate_archive").rglob("*.yaml"))
            self.assertEqual(summary["archived_record_count"], 1)
            self.assertEqual(summary["skipped_group_count"], 0)
            self.assertEqual(len(archived_docs), 1)
            self.assertEqual(len([path for path in active_docs if ".duplicate_archive" not in str(path)]), 1)
            active_record = load_yaml(first_paths[0])
            self.assertEqual(active_record["candidate_id"], first_record["candidate_id"])

    def test_archive_future_window_candidate_records_moves_far_future_windows_out_of_active_workspace(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:123": fixture_response,
                    },
                },
            )
            future_fixture = root / "fixtures" / "candidate_future_window.json"
            _write_json(
                future_fixture,
                {
                    "source": "github",
                    "window": "2026-04-03..2026-07-03",
                    "query_slice_id": "qf_agent",
                    "items": [
                        {
                            "external_id": "123",
                            "canonical_url": "https://github.com/example/product",
                            "title": "Example Product",
                            "summary": "AI agent workspace for legal teams handling intake and document workflows.",
                            "raw_evidence_excerpt": "Agent workspace for legal intake, document review, and team follow-up.",
                            "author_name": "example",
                            "linked_homepage_url": "https://example.com",
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-04-03T00:00:00Z",
                            "topics": ["agent"],
                            "language": "Python",
                            "current_metrics_json": {"star_count": 10},
                        }
                    ],
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-04-03..2026-07-03",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=future_fixture,
                    llm_fixture_path=llm_fixture,
                )
                summary = archive_future_window_candidate_records(
                    config,
                    today=date(2026, 4, 6),
                    grace_days=7,
                )

            self.assertEqual(len(paths), 1)
            self.assertEqual(summary["archived_record_count"], 1)
            active_docs = [p for p in candidate_workspace.rglob("*.yaml") if ".invalid_window_archive" not in str(p)]
            archived_docs = sorted((candidate_workspace / ".invalid_window_archive").rglob("*.yaml"))
            self.assertEqual(active_docs, [])
            self.assertEqual(len(archived_docs), 1)

    def test_run_candidate_prescreen_filters_out_github_template_and_sdk_noise_before_llm(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            discovery_fixture = root / "fixtures" / "candidate_window.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            _write_json(
                discovery_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [
                        {
                            "external_id": "100",
                            "canonical_url": "https://github.com/example/chatbot-template",
                            "title": "chatbot-template",
                            "summary": "A hackable chatbot template and starter kit for Next.js apps.",
                            "raw_evidence_excerpt": "Template starter for developers building chatbot demos.",
                            "author_name": "example",
                            "linked_homepage_url": None,
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-03-08T00:00:00Z",
                            "topics": ["chatbot", "template"],
                            "language": "TypeScript",
                            "current_metrics_json": {"star_count": 10},
                        },
                        {
                            "external_id": "101",
                            "canonical_url": "https://github.com/example/repoagent-sdk",
                            "title": "repoagent-sdk",
                            "summary": "Open-source agent framework and orchestration SDK for developers.",
                            "raw_evidence_excerpt": "SDK for agent orchestration and framework integrations.",
                            "author_name": "example",
                            "linked_homepage_url": None,
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-03-08T00:00:00Z",
                            "topics": ["agent", "sdk"],
                            "language": "Python",
                            "current_metrics_json": {"star_count": 10},
                        },
                        {
                            "external_id": "102",
                            "canonical_url": "https://github.com/example/legalcase-agent",
                            "title": "legalcase-agent",
                            "summary": "Matter intake and document summarization agent for small legal teams.",
                            "raw_evidence_excerpt": "Agent workspace for legal intake, document review, and team follow-up.",
                            "author_name": "example",
                            "linked_homepage_url": "https://legalcase.example.com",
                            "linked_repo_url": None,
                            "published_at": None,
                            "pushed_at": "2026-03-08T00:00:00Z",
                            "topics": ["agent", "legal"],
                            "language": "Python",
                            "current_metrics_json": {"star_count": 10},
                        },
                    ],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:102": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                written_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=3,
                    discovery_fixture_path=discovery_fixture,
                    llm_fixture_path=llm_fixture,
                )

            self.assertEqual(len(written_paths), 1)
            record = load_yaml(written_paths[0])
            self.assertEqual(record["external_id"], "102")

    def test_run_candidate_prescreen_continues_past_duplicate_candidate_after_gate(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            first_fixture = root / "fixtures" / "existing_window.json"
            second_fixture = root / "fixtures" / "new_window.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            existing_item = {
                "external_id": "200",
                "canonical_url": "https://github.com/example/agentdesk",
                "title": "agentdesk",
                "summary": "AI support agent workspace for customer operations teams.",
                "raw_evidence_excerpt": "Agent workspace for support teams handling customer operations and follow-up.",
                "author_name": "example",
                "linked_homepage_url": "https://agentdesk.example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-29T00:00:00Z",
                "topics": ["agent", "support"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            new_item = {
                "external_id": "201",
                "canonical_url": "https://github.com/example/fieldcopilot",
                "title": "fieldcopilot",
                "summary": "Field service copilot with AI agents for dispatch, visit notes, and follow-up actions.",
                "raw_evidence_excerpt": "Copilot workspace for field service teams managing dispatch, notes, and follow-up work.",
                "author_name": "example",
                "linked_homepage_url": "https://fieldcopilot.example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-04-06T00:00:00Z",
                "topics": ["copilot", "operations"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            _write_json(
                first_fixture,
                {
                    "source": "github",
                    "window": "2026-03-29..2026-04-02",
                    "query_slice_id": "qf_agent",
                    "items": [existing_item],
                },
            )
            _write_json(
                second_fixture,
                {
                    "source": "github",
                    "window": "2026-03-31..2026-04-06",
                    "query_slice_id": "qf_agent",
                    "items": [existing_item, new_item],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:200": fixture_response,
                        "github:201": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                first_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-29..2026-04-02",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=first_fixture,
                    llm_fixture_path=llm_fixture,
                )
                second_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-31..2026-04-06",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=second_fixture,
                    llm_fixture_path=llm_fixture,
                )

            self.assertEqual(len(first_paths), 1)
            self.assertEqual(len(second_paths), 1)
            second_record = load_yaml(second_paths[0])
            self.assertEqual(second_record["external_id"], "201")

    def test_run_candidate_prescreen_keeps_discovery_interval_separate_from_relay_interval(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            llm_result = normalize_llm_result(fixture_response)
            llm_result["channel_metadata"] = {
                "prompt_version": "candidate_prescreener_v1",
                "routing_version": "route_candidate_prescreener_v1",
                "relay_client_version": "relay_candidate_prescreener_v1",
                "model": "fixture-relay",
                "transport": "http_json_relay",
                "request_id": None,
            }
            fixture_item = {
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Example Product",
                "summary": "AI assistant for sales teams and meeting follow-up workflows.",
                "raw_evidence_excerpt": "Assistant workspace for sales call prep, notes, and follow-up tasks.",
                "author_name": "example",
                "linked_homepage_url": "https://example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-08T00:00:00Z",
                "topics": ["assistant"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                with patch("src.candidate_prescreen.workflow.discover_candidates", return_value=[fixture_item]) as discover_mock, patch(
                    "src.candidate_prescreen.workflow.screen_candidate",
                    return_value={
                        "transport_status": "succeeded",
                        "provider_response_status": "succeeded",
                        "content_status": "succeeded",
                        "schema_status": "succeeded",
                        "business_status": "succeeded",
                        "request_id": None,
                        "http_status": 200,
                        "mapped_error_type": None,
                        "failure_code": None,
                        "failure_message": None,
                        "normalized_result": llm_result,
                    },
                ) as screen_mock:
                    run_candidate_prescreen(
                        config,
                        source_code="github",
                        window="2026-03-01..2026-03-08",
                        query_slice_id="qf_agent",
                        limit=1,
                        discovery_fixture_path=None,
                        llm_fixture_path=None,
                        discovery_request_interval_seconds=0,
                        request_interval_seconds=60,
                    )

            self.assertEqual(discover_mock.call_args.kwargs["request_interval_seconds"], 0)
            self.assertEqual(screen_mock.call_args.kwargs["request_interval_seconds"], 60)

    def test_run_candidate_prescreen_skips_retryable_duplicate_analysis_within_cooldown(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            discovery_fixture = root / "fixtures" / "candidate_window.json"
            llm_fixture = root / "fixtures" / "llm_fixture.json"
            repo_llm_fixture = json.loads(
                (Path(__file__).resolve().parents[2] / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture_response = next(iter(repo_llm_fixture["responses"].values()))
            fixture_item = {
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Example Product",
                "summary": "AI assistant for sales teams and meeting follow-up workflows.",
                "raw_evidence_excerpt": "Assistant workspace for sales call prep, notes, and follow-up tasks.",
                "author_name": "example",
                "linked_homepage_url": "https://example.com",
                "linked_repo_url": None,
                "published_at": None,
                "pushed_at": "2026-03-08T00:00:00Z",
                "topics": ["assistant"],
                "language": "Python",
                "current_metrics_json": {"star_count": 10},
            }
            _write_json(
                discovery_fixture,
                {
                    "source": "github",
                    "window": "2026-03-01..2026-03-08",
                    "query_slice_id": "qf_agent",
                    "items": [fixture_item],
                },
            )
            _write_json(
                llm_fixture,
                {
                    "prompt_version": "candidate_prescreener_v1",
                    "routing_version": "route_candidate_prescreener_v1",
                    "relay_client_version": "relay_candidate_prescreener_v1",
                    "model": "fixture-relay",
                    "responses": {
                        "github:123": fixture_response,
                    },
                },
            )

            with temp_config(candidate_workspace_dir=candidate_workspace) as config:
                first_paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=discovery_fixture,
                    llm_fixture_path=llm_fixture,
                )
                record = load_yaml(first_paths[0])
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = "network_error"
                record["llm_prescreen"]["error_message"] = "temporary relay outage"
                record["human_review_status"] = "pending_first_pass"
                record["human_review_note_template_key"] = None
                record["human_review_notes"] = None
                record["human_reviewed_at"] = None
                record["updated_at"] = utc_now_iso()
                dump_yaml(first_paths[0], record)

                with patch("src.candidate_prescreen.workflow.screen_candidate") as screen_mock:
                    second_paths = run_candidate_prescreen(
                        config,
                        source_code="github",
                        window="2026-03-01..2026-03-08",
                        query_slice_id="qf_agent",
                        limit=1,
                        discovery_fixture_path=discovery_fixture,
                        llm_fixture_path=llm_fixture,
                        retry_sleep_seconds=30,
                    )

            screen_mock.assert_not_called()
            self.assertEqual(second_paths, [])
