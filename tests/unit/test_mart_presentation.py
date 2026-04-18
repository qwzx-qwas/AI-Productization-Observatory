from __future__ import annotations

import unittest

from src.marts.presentation import build_dashboard_view, build_product_drill_down, reconcile_dashboard_view
from src.runtime.replay import build_default_mart
from tests.helpers import temp_config


class MartPresentationTests(unittest.TestCase):
    def test_dashboard_view_reads_only_from_mart_contract_outputs(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            dashboard = build_dashboard_view(mart)

            self.assertEqual(dashboard["main_report_dataset"], "fact_product_observation")
            self.assertEqual(dashboard["main_report_semantics"], "effective resolved taxonomy")
            self.assertEqual(dashboard["cards"]["top_jtbd_products_30d"], mart["top_jtbd_products_30d"])
            self.assertEqual(dashboard["cards"]["attention_distribution_30d"], mart["attention_distribution_30d"])
            self.assertEqual(dashboard["cards"]["unresolved_backlog"]["open_item_count"], 1)

    def test_product_drill_down_returns_traceable_main_and_unresolved_paths(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)

            main_result = build_product_drill_down(mart, product_id="prod_001")
            self.assertTrue(main_result["main_report_included"])
            self.assertEqual(main_result["effective_taxonomy_code"], "JTBD_KNOWLEDGE_RESEARCH")
            self.assertEqual(main_result["trace_refs"]["review_issue_ids"], [])
            self.assertEqual(main_result["fact_rows"][0]["taxonomy_primary_code"], "JTBD_KNOWLEDGE_RESEARCH")

            unresolved_result = build_product_drill_down(mart, product_id="prod_003")
            self.assertFalse(unresolved_result["main_report_included"])
            self.assertEqual(unresolved_result["effective_taxonomy_code"], "unresolved")
            self.assertEqual(unresolved_result["trace_refs"]["review_issue_ids"], ["rev_003"])
            self.assertEqual(unresolved_result["unresolved_registry_entry"]["review_issue_id"], "rev_003")

    def test_dashboard_reconciliation_reports_full_pass_rate_for_default_mart(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            reconciliation = reconcile_dashboard_view(mart)

            self.assertTrue(reconciliation["all_passed"])
            self.assertEqual(reconciliation["pass_rate"], 1.0)
            self.assertEqual(reconciliation["dashboard_contract_ref"]["main_report_dataset"], "fact_product_observation")
            self.assertFalse(reconciliation["dashboard_contract_ref"]["runtime_detail_join_allowed"])
            self.assertEqual(
                [check["check_id"] for check in reconciliation["checks"]],
                [
                    "main_report_dataset",
                    "main_report_semantics",
                    "top_jtbd_products_30d",
                    "attention_distribution_30d",
                    "unresolved_backlog_open_item_count",
                    "unresolved_backlog_items",
                ],
            )


if __name__ == "__main__":
    unittest.main()
