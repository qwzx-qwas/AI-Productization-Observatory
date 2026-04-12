from __future__ import annotations

import unittest

from src.common.errors import ContractValidationError
from src.review.review_packet_builder import (
    apply_taxonomy_review_resolution,
    build_taxonomy_review_issue,
    resolve_taxonomy_review_issue,
    select_effective_taxonomy_assignment,
)
from tests.helpers import REPO_ROOT


class ReviewPacketBuilderTests(unittest.TestCase):
    def test_build_taxonomy_review_issue_from_unresolved_assignment(self) -> None:
        current_assignment = {
            "target_type": "product",
            "target_id": "prod_ambiguous",
            "taxonomy_version": "v0",
            "label_level": 1,
            "label_role": "primary",
            "category_code": "unresolved",
            "confidence": 0.41,
            "rationale": "Primary job is not uniquely identifiable.",
            "result_status": "active",
        }
        related_evidence = [
            {
                "source_item_id": "src_item_1",
                "evidence_type": "unclear_description_signal",
                "source_url": "https://example.com/ambiguous",
            }
        ]
        links = [{"product_id": "prod_ambiguous", "source_item_id": "src_item_1"}]

        built = build_taxonomy_review_issue(
            current_assignment,
            related_evidence,
            target_summary="Ambiguous product taxonomy",
            upstream_downstream_links=links,
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
        )

        self.assertEqual(built["review_packet"]["issue_type"], "taxonomy_conflict")
        self.assertEqual(built["review_packet"]["recommended_action"], "mark_unresolved")
        self.assertEqual(built["review_issue"]["priority_code"], "P1")
        self.assertEqual(built["review_queue_view"]["queue_bucket"], "taxonomy_conflict")

    def test_mark_unresolved_resolution_writes_new_taxonomy_version(self) -> None:
        current_assignment = {
            "target_type": "product",
            "target_id": "prod_001",
            "taxonomy_version": "v0",
            "label_level": 1,
            "label_role": "primary",
            "category_code": "JTBD_KNOWLEDGE",
            "confidence": 0.72,
            "rationale": "Auto result leans knowledge.",
            "assigned_by": "taxonomy_classifier",
            "model_or_rule_version": "taxonomy_classifier_v1",
            "assigned_at": "2026-03-10T10:00:00Z",
            "result_status": "active",
            "effective_from": "2026-03-10T10:00:00Z",
            "evidence_refs_json": [
                {
                    "source_item_id": "src_item_1",
                    "evidence_type": "job_statement",
                    "source_url": "https://example.com/knowledge",
                }
            ],
        }
        built = build_taxonomy_review_issue(
            current_assignment,
            current_assignment["evidence_refs_json"],
            target_summary="Ambiguous research workflow product",
            upstream_downstream_links=[{"product_id": "prod_001"}],
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            issue_type="taxonomy_conflict",
            priority_code="P1",
        )

        resolved = resolve_taxonomy_review_issue(
            built["review_issue"],
            current_assignment,
            resolution_action="mark_unresolved",
            resolution_notes="Review confirms the primary taxonomy should remain unresolved.",
            reviewer="local_project_user",
            reviewed_at="2026-03-12T09:00:00Z",
            config_dir=REPO_ROOT / "configs",
        )

        writeback = resolved["taxonomy_assignment"]
        self.assertEqual(resolved["review_issue"]["status"], "resolved")
        self.assertEqual(resolved["review_issue"]["resolution_payload_json"]["unresolved_mode"], "writeback_unresolved")
        self.assertEqual(writeback["category_code"], "unresolved")
        self.assertTrue(writeback["is_override"])
        self.assertEqual(writeback["override_review_issue_id"], built["review_issue"]["review_issue_id"])
        self.assertEqual(writeback["supersedes_assignment_id"][:4], "tax_")

    def test_mark_unresolved_can_close_as_review_only_without_writeback(self) -> None:
        current_assignment = {
            "target_type": "product",
            "target_id": "prod_review_only",
            "taxonomy_version": "v0",
            "label_level": 1,
            "label_role": "primary",
            "category_code": "JTBD_KNOWLEDGE",
            "confidence": 0.72,
            "rationale": "Auto result leans knowledge.",
            "assigned_by": "taxonomy_classifier",
            "model_or_rule_version": "taxonomy_classifier_v1",
            "assigned_at": "2026-03-10T10:00:00Z",
            "result_status": "active",
            "effective_from": "2026-03-10T10:00:00Z",
            "evidence_refs_json": [
                {
                    "source_item_id": "src_item_review_only",
                    "evidence_type": "job_statement",
                    "source_url": "https://example.com/review-only",
                }
            ],
        }
        built = build_taxonomy_review_issue(
            current_assignment,
            current_assignment["evidence_refs_json"],
            target_summary="Review-only unresolved sample",
            upstream_downstream_links=[{"product_id": "prod_review_only"}],
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            issue_type="taxonomy_conflict",
            priority_code="P2",
        )

        resolved = resolve_taxonomy_review_issue(
            built["review_issue"],
            current_assignment,
            resolution_action="mark_unresolved",
            resolution_notes="Backlog remains unresolved, but the current auto result stays in place.",
            reviewer="local_project_user",
            reviewed_at="2026-03-12T09:00:00Z",
            unresolved_mode="review_only_unresolved",
            config_dir=REPO_ROOT / "configs",
        )

        self.assertEqual(resolved["review_issue"]["status"], "resolved")
        self.assertEqual(resolved["review_issue"]["resolution_payload_json"]["unresolved_mode"], "review_only_unresolved")
        self.assertIsNone(resolved["taxonomy_assignment"])

    def test_p0_override_requires_approver(self) -> None:
        current_assignment = {
            "target_type": "product",
            "target_id": "prod_p0",
            "taxonomy_version": "v0",
            "label_level": 1,
            "label_role": "primary",
            "category_code": "JTBD_KNOWLEDGE",
            "confidence": 0.8,
            "rationale": "Auto result leans knowledge.",
            "assigned_at": "2026-03-10T10:00:00Z",
            "result_status": "active",
            "effective_from": "2026-03-10T10:00:00Z",
            "evidence_refs_json": [
                {
                    "source_item_id": "src_item_p0",
                    "evidence_type": "job_statement",
                    "source_url": "https://example.com/p0",
                }
            ],
        }
        built = build_taxonomy_review_issue(
            current_assignment,
            current_assignment["evidence_refs_json"],
            target_summary="High-impact taxonomy override",
            upstream_downstream_links=[{"product_id": "prod_p0"}],
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            issue_type="taxonomy_conflict",
            priority_code="P0",
        )

        with self.assertRaises(ContractValidationError):
            resolve_taxonomy_review_issue(
                built["review_issue"],
                current_assignment,
                resolution_action="override_auto_result",
                resolution_notes="Human review wants a new taxonomy.",
                reviewer="reviewer_a",
                reviewed_at="2026-03-12T09:00:00Z",
                override_category_code="JTBD_PRODUCTIVITY_AUTOMATION",
                config_dir=REPO_ROOT / "configs",
            )

    def test_select_effective_taxonomy_prefers_active_override(self) -> None:
        assignments = [
            {
                "target_type": "product",
                "target_id": "prod_1",
                "taxonomy_version": "v0",
                "label_level": 1,
                "label_role": "primary",
                "category_code": "JTBD_KNOWLEDGE",
                "assigned_at": "2026-03-10T10:00:00Z",
                "effective_from": "2026-03-10T10:00:00Z",
                "is_override": False,
                "result_status": "active",
            },
            {
                "target_type": "product",
                "target_id": "prod_1",
                "taxonomy_version": "v0",
                "label_level": 1,
                "label_role": "primary",
                "category_code": "unresolved",
                "assigned_at": "2026-03-11T10:00:00Z",
                "effective_from": "2026-03-11T10:00:00Z",
                "is_override": True,
                "result_status": "active",
            },
        ]

        effective = select_effective_taxonomy_assignment(assignments)
        self.assertEqual(effective["category_code"], "unresolved")

    def test_apply_taxonomy_review_resolution_updates_effective_record_state(self) -> None:
        record = {
            "product_id": "prod_apply",
            "source_id": "src_product_hunt",
            "source_item_id": "srcitem_apply_v1",
            "source_url": "https://example.com/prod_apply",
            "taxonomy_assignments": [
                {
                    "target_type": "product",
                    "target_id": "prod_apply",
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
                            "source_item_id": "srcitem_apply_v1",
                            "evidence_type": "job_statement",
                            "source_url": "https://example.com/prod_apply",
                        }
                    ],
                }
            ],
            "review_issues": [],
            "drill_down_refs": {
                "product_id": "prod_apply",
                "source_item_id": "srcitem_apply_v1",
                "review_issue_ids": [],
            },
        }

        applied = apply_taxonomy_review_resolution(
            record,
            target_summary="Apply helper sample",
            upstream_downstream_links=[{"product_id": "prod_apply", "source_item_id": "srcitem_apply_v1"}],
            resolution_action="mark_unresolved",
            resolution_notes="Human review keeps this sample unresolved.",
            reviewer="local_project_user",
            reviewed_at="2026-03-12T09:00:00Z",
            config_dir=REPO_ROOT / "configs",
            schema_dir=REPO_ROOT / "schemas",
            issue_type="taxonomy_conflict",
            priority_code="P1",
        )

        updated = applied["record"]
        self.assertEqual(updated["effective_taxonomy"]["category_code"], "unresolved")
        self.assertEqual(updated["drill_down_refs"]["review_issue_ids"], [applied["review_issue"]["review_issue_id"]])
        self.assertTrue(updated["unresolved_registry_entry"]["is_effective_unresolved"])
        self.assertEqual(len(updated["taxonomy_assignments"]), 2)


if __name__ == "__main__":
    unittest.main()
