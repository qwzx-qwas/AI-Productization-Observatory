from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.common.errors import ProcessingError
from src.runtime.raw_store.file_store import FileRawStore
from src.runtime.replay import replay_source_window
from src.runtime.tasks import FileTaskStore
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
