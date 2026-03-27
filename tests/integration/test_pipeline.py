from __future__ import annotations

import json
import unittest

from src.runtime.replay import replay_source_window
from tests.helpers import temp_config


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
