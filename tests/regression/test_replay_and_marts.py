from __future__ import annotations

import unittest

from src.common.errors import BlockedReplayError
from src.runtime.models import default_payload
from src.runtime.replay import build_default_mart, replay_source_window
from src.runtime.tasks import FileTaskStore
from tests.helpers import temp_config


class ReplayAndMartRegressionTests(unittest.TestCase):
    def test_same_window_replay_creates_new_task_with_parent(self) -> None:
        with temp_config() as config:
            first = replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)
            second = replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)

            store = FileTaskStore(config.task_store_path)
            tasks = store.all_tasks()
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[1]["parent_task_id"], first["task_id"])
            self.assertEqual(second["task_id"], tasks[1]["task_id"])

    def test_blocked_replay_stays_blocked(self) -> None:
        with temp_config() as config:
            store = FileTaskStore(config.task_store_path)
            blocked = store.enqueue(
                task_type="pull_collect",
                task_scope="per_source_window",
                source_id="src_product_hunt",
                target_type=None,
                target_id=None,
                window_start="2026-03-01",
                window_end="2026-03-08",
                payload_json=default_payload("product_hunt", "2026-03-01", "2026-03-08"),
                max_attempts=0,
                status="blocked",
            )
            store.block(blocked.task_id, "seed blocked replay")

            with self.assertRaises(BlockedReplayError):
                replay_source_window(source_code="product_hunt", window="2026-03-01..2026-03-08", config=config)

            tasks = store.all_tasks()
            self.assertEqual(tasks[-1]["status"], "blocked")

    def test_mart_builder_filters_unresolved_from_main_stats(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            categories = {row["category_code"]: row["product_count"] for row in mart["top_jtbd_products_30d"]}
            self.assertEqual(categories["research_ops"], 2)
            self.assertEqual(categories["qa_automation"], 1)
            self.assertNotIn("unresolved", categories)

            attention_rows = {(row["category_code"], row["attention_band"]): row["product_count"] for row in mart["attention_distribution_30d"]}
            self.assertEqual(attention_rows[("research_ops", "high")], 1)
            self.assertEqual(attention_rows[("research_ops", "medium")], 1)
