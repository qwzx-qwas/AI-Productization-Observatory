from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.workflow import (
    handoff_candidates_to_staging,
    run_candidate_prescreen,
    validate_candidate_workspace,
)
from src.common.errors import ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from src.runtime.raw_store.file_store import FileRawStore
from src.runtime.replay import replay_source_window
from src.runtime.tasks import FileTaskStore
from src.cli import validate_gold_set
from tests.helpers import REPO_ROOT, temp_config


class FixturePipelineIntegrationTests(unittest.TestCase):
    def test_replay_builds_raw_records_and_source_items(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )

            self.assertEqual(len(result["raw_records"]), 2)
            self.assertEqual(len(result["source_items"]), 2)

            first_raw = result["raw_records"][0]
            raw_payload_path = config.raw_store_dir / first_raw["raw_payload_ref"]
            self.assertTrue(raw_payload_path.exists())

            first_item = result["source_items"][0]
            self.assertEqual(first_item["source_id"], "src_product_hunt")
            self.assertEqual(first_item["external_id"], "ph_1001")
            self.assertEqual(first_item["title"], "Desk Research Copilot")
            self.assertEqual(first_item["raw_id"], first_raw["raw_id"])

    def test_expected_fixture_shape_matches_normalized_output(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            expected_path = config.fixtures_dir / "normalizer" / "product_hunt_expected_source_item.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            actual = result["source_items"][0]

            self.assertEqual(actual["source_id"], expected["source_id"])
            self.assertEqual(actual["title"], expected["title"])
            self.assertEqual(actual["canonical_url"], expected["canonical_url"])
            self.assertEqual(actual["current_metrics_json"], expected["current_metrics_json"])

    def test_expected_fixture_bundle_matches_normalized_outputs(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            expected_path = config.fixtures_dir / "normalizer" / "product_hunt_expected_source_items.json"
            expected_items = json.loads(expected_path.read_text(encoding="utf-8"))
            actual_items = {item["external_id"]: item for item in result["source_items"]}

            self.assertEqual({item["external_id"] for item in expected_items}, set(actual_items))
            for expected in expected_items:
                actual = actual_items[expected["external_id"]]
                self.assertEqual(actual["source_id"], expected["source_id"])
                self.assertEqual(actual["title"], expected["title"])
                self.assertEqual(actual["canonical_url"], expected["canonical_url"])
                self.assertEqual(actual["current_metrics_json"], expected["current_metrics_json"])
                self.assertEqual(actual["linked_homepage_url"], expected["linked_homepage_url"])

    def test_raw_store_dedupes_duplicate_payloads_by_source_external_hash(self) -> None:
        with temp_config() as config:
            collector_fixture = json.loads((config.fixtures_dir / "collector" / "product_hunt_window.json").read_text(encoding="utf-8"))
            crawl_run = {
                "crawl_run_id": "crawl-run-1",
                "source_id": collector_fixture["source_id"],
                "window_start": collector_fixture["window_start"],
                "watermark_before": collector_fixture["watermark_before"],
                "request_params": collector_fixture["request_params"],
                "collected_at": "2026-03-08T00:00:00Z",
            }
            duplicate_item = collector_fixture["items"][0]

            raw_store = FileRawStore(config.raw_store_dir)
            records = raw_store.store_items(crawl_run, [duplicate_item, duplicate_item])

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["fetched_at"], "2026-03-08T00:00:00Z")
            self.assertIn("window_start=2026-03-01", records[0]["raw_payload_ref"])

    def test_replay_marks_terminal_failure_on_invalid_normalized_output(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "collector").mkdir(parents=True, exist_ok=True)

            collector_fixture = json.loads((REPO_ROOT / "fixtures" / "collector" / "product_hunt_window.json").read_text(encoding="utf-8"))
            collector_fixture["items"][0]["name"] = ["not", "a", "string"]
            (fixtures_dir / "collector" / "product_hunt_window.json").write_text(
                json.dumps(collector_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            with temp_config(fixtures_dir=fixtures_dir) as config:
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

                self.assertEqual(ctx.exception.error_type, "json_schema_validation_failed")
                store = FileTaskStore(config.task_store_path)
                task = store.all_tasks()[-1]
                self.assertEqual(task["status"], "failed_terminal")
                self.assertEqual(task["last_error_type"], "json_schema_validation_failed")

    def test_replay_marks_terminal_failure_on_unparseable_fixture(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "collector").mkdir(parents=True, exist_ok=True)
            (fixtures_dir / "collector" / "product_hunt_window.json").write_text("{ invalid json\n", encoding="utf-8")

            with temp_config(fixtures_dir=fixtures_dir) as config:
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

                self.assertEqual(ctx.exception.error_type, "parse_failure")
                store = FileTaskStore(config.task_store_path)
                task = store.all_tasks()[-1]
                self.assertEqual(task["status"], "failed_terminal")
                self.assertEqual(task["last_error_type"], "parse_failure")

    def test_replay_marks_retryable_failure_on_raw_store_write_error(self) -> None:
        with temp_config() as config:
            with patch.object(
                FileRawStore,
                "store_items",
                side_effect=ProcessingError("storage_write_failed", "simulated raw store outage"),
            ):
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

            self.assertEqual(ctx.exception.error_type, "storage_write_failed")
            store = FileTaskStore(config.task_store_path)
            task = store.all_tasks()[-1]
            self.assertEqual(task["status"], "failed_retryable")
            self.assertEqual(task["last_error_type"], "storage_write_failed")

    def test_candidate_prescreen_writes_workspace_documents_from_fixtures(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=2,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                self.assertEqual(len(paths), 2)
                self.assertEqual(validate_candidate_workspace(config), 2)

                first_record = load_yaml(paths[0])
                self.assertEqual(first_record["human_review_status"], "pending_first_pass")
                self.assertEqual(first_record["llm_prescreen"]["status"], "succeeded")
                self.assertEqual(first_record["llm_prescreen"]["channel_metadata"]["prompt_version"], "candidate_prescreener_v1")
                self.assertTrue(paths[0].is_relative_to(candidate_workspace))

    def test_candidate_handoff_to_staging_keeps_gold_set_stub_boundary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="product_hunt",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="ph_published_launches",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "product_hunt_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                record = load_yaml(paths[0])
                record["human_review_status"] = "approved_for_staging"
                record["human_review_notes"] = "First-pass human review approved this candidate for staging."
                record["human_reviewed_at"] = utc_now_iso()
                record["whitelist_reason"] = "manual_first_pass_whitelist"
                dump_yaml(paths[0], record)

                results = handoff_candidates_to_staging(config, candidate_ids=[record["candidate_id"]])
                self.assertEqual(len(results), 1)

                staging_payload = load_yaml(Path(results[0][1]))
                samples = staging_payload["samples"]
                matching = [sample for sample in samples if sample["sample_id"] == record["candidate_id"]]
                self.assertEqual(len(matching), 1)
                staged = matching[0]
                self.assertEqual(staged["current_state"], "candidate_approved_for_annotation")
                self.assertEqual(staged["training_pool_source"], "candidate_pool")
                self.assertEqual(staged["whitelist_reason"], "manual_first_pass_whitelist")
                self.assertEqual(staged["review_closed"], None)
                self.assertFalse(staged["local_project_user_annotation"]["provided"])
                self.assertEqual(staged["candidate_prescreen_ref"]["candidate_id"], record["candidate_id"])

                status, sample_count = validate_gold_set(config)
                self.assertEqual(status, "stub")
                self.assertEqual(sample_count, 0)
