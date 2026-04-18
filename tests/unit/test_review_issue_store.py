from __future__ import annotations

import unittest

from src.review.store import FileReviewIssueStore, default_review_issue_store_path, open_taxonomy_review_record, resolve_taxonomy_review_record
from tests.helpers import REPO_ROOT, temp_config


def _sample_record() -> dict[str, object]:
    return {
        "product_id": "prod_store",
        "source_id": "src_product_hunt",
        "source_item_id": "srcitem_store_v1",
        "source_url": "https://example.com/prod_store",
        "taxonomy_assignments": [
            {
                "target_type": "product",
                "target_id": "prod_store",
                "taxonomy_version": "v0",
                "label_level": 1,
                "label_role": "primary",
                "category_code": "JTBD_KNOWLEDGE",
                "confidence": 0.68,
                "rationale": "Auto result leans knowledge.",
                "assigned_by": "taxonomy_classifier",
                "model_or_rule_version": "taxonomy_classifier_v1",
                "assigned_at": "2026-03-10T10:00:00Z",
                "is_override": False,
                "override_review_issue_id": None,
                "result_status": "active",
                "effective_from": "2026-03-10T10:00:00Z",
                "supersedes_assignment_id": None,
                "evidence_refs_json": [
                    {
                        "source_item_id": "srcitem_store_v1",
                        "evidence_type": "job_statement",
                        "source_url": "https://example.com/prod_store",
                    }
                ],
            }
        ],
        "review_issues": [],
        "drill_down_refs": {
            "product_id": "prod_store",
            "source_item_id": "srcitem_store_v1",
            "review_issue_ids": [],
        },
    }


class ReviewIssueStoreTests(unittest.TestCase):
    def test_open_taxonomy_review_persists_issue_and_updates_record(self) -> None:
        with temp_config() as config:
            store = FileReviewIssueStore(default_review_issue_store_path(config.task_store_path))
            opened = open_taxonomy_review_record(
                _sample_record(),
                store=store,
                target_summary="Open taxonomy review for ambiguous scope",
                upstream_downstream_links=[{"product_id": "prod_store", "source_item_id": "srcitem_store_v1"}],
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
                issue_type="taxonomy_conflict",
                priority_code="P1",
                created_at="2026-03-12T09:00:00Z",
            )

            issues = store.all_issues()
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["status"], "open")
            self.assertEqual(opened["review_queue_view"]["queue_bucket"], "taxonomy_conflict")
            self.assertEqual(
                opened["record"]["drill_down_refs"]["review_issue_ids"],
                [opened["review_issue"]["review_issue_id"]],
            )

            open_queue = store.queue_entries(config_dir=REPO_ROOT / "configs", open_only=True)
            self.assertEqual([entry["review_issue_id"] for entry in open_queue], [opened["review_issue"]["review_issue_id"]])

    def test_resolve_taxonomy_review_persists_writeback_and_clears_open_queue(self) -> None:
        with temp_config() as config:
            store = FileReviewIssueStore(default_review_issue_store_path(config.task_store_path))
            opened = open_taxonomy_review_record(
                _sample_record(),
                store=store,
                target_summary="Open taxonomy review for unresolved writeback",
                upstream_downstream_links=[{"product_id": "prod_store", "source_item_id": "srcitem_store_v1"}],
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
                issue_type="taxonomy_conflict",
                priority_code="P1",
                created_at="2026-03-12T09:00:00Z",
            )

            resolved = resolve_taxonomy_review_record(
                opened["record"],
                store=store,
                review_issue_id=opened["review_issue"]["review_issue_id"],
                target_summary="Resolve taxonomy review to unresolved",
                upstream_downstream_links=[{"product_id": "prod_store", "source_item_id": "srcitem_store_v1"}],
                resolution_action="mark_unresolved",
                resolution_notes="Human review confirms the effective taxonomy should be unresolved.",
                reviewer="local_project_user",
                reviewed_at="2026-03-13T10:00:00Z",
                config_dir=REPO_ROOT / "configs",
                schema_dir=REPO_ROOT / "schemas",
            )

            stored_issue = store.get(opened["review_issue"]["review_issue_id"])
            self.assertEqual(stored_issue["status"], "resolved")
            self.assertEqual(resolved["record"]["effective_taxonomy"]["category_code"], "unresolved")
            self.assertTrue(resolved["record"]["unresolved_registry_entry"]["is_effective_unresolved"])
            self.assertEqual(store.queue_entries(config_dir=REPO_ROOT / "configs", open_only=True), [])


if __name__ == "__main__":
    unittest.main()
