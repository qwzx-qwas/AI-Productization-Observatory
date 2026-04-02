from __future__ import annotations

import unittest

from src.candidate_prescreen.review_card import normalize_llm_result, validate_candidate_review_card


class CandidatePrescreenReviewCardUnitTests(unittest.TestCase):
    def test_normalize_llm_result_maps_provider_drift_into_canonical_review_card(self) -> None:
        provider_result = {
            "decision_snapshot": {
                "recommended_action": "manual_triage_required",
                "prescreen_outcome": "insufficient_evidence_for_candidate_pool_promotion",
                "rationale": "Repository metadata is present, but there is no summary, README excerpt, or feature evidence to confirm scope.",
                "risk_flags": ["empty_summary", "empty_raw_evidence_excerpt"],
            },
            "scope_boundary_note": "Current signal supports only a lightweight metadata-based hypothesis.",
            "evidence_anchors": [
                {
                    "anchor_rank": 1,
                    "quote": "\"title\": \"agent\"",
                    "why_it_matters": "The title suggests possible agent tooling, but it is too generic to classify confidently.",
                },
                {
                    "anchor_rank": 2,
                    "quote": "\"summary\": \"\" and \"raw_evidence_excerpt\": \"\"",
                    "why_it_matters": "Critical descriptive fields are empty, creating high uncertainty and requiring human verification.",
                },
            ],
            "review_focus_points": [
                "Open README and verify whether this is a user-facing AI application/product versus a reusable library or experiment.",
                "Confirm concrete AI functionality from code/docs, not just repository naming.",
            ],
            "confidence_summary": {
                "overall_confidence": "low",
                "uncertainty_level": "high",
                "uncertainty_reasons": [
                    "No descriptive content provided in payload.",
                    "Classification currently relies on weak lexical hints.",
                ],
            },
            "handoff_readiness_hint": "High-value next step: inspect README and topics before any pool promotion.",
            "persona_candidates": [
                {
                    "confidence_rank": 1,
                    "persona": "AI agent framework maintainer",
                    "fit_rationale": "Repo name suggests possible agent-oriented implementation, likely developer-facing.",
                    "confidence": "low",
                }
            ],
            "taxonomy_hints": {
                "main_category_candidate": "AI Agent Tooling/Framework (developer-facing)",
                "adjacent_category_candidate": "General Software Repository (non-AI-specific)",
                "adjacent_category_rejected_reason": "Repository naming provides a weak AI-related hint.",
            },
        }

        normalized = normalize_llm_result(provider_result)
        self.assertEqual(normalized["recommended_action"], "hold")
        self.assertFalse(normalized["recommend_candidate_pool"])
        self.assertEqual(normalized["handoff_readiness_hint"]["suggested_action"], "hold")
        self.assertEqual(normalized["confidence_summary"]["scope_confidence"], "low")
        self.assertEqual(normalized["taxonomy_hints"]["primary_persona_code"], "ai_agent_framework_maintainer")
        self.assertEqual(normalized["taxonomy_hints"]["main_category_candidate"]["category_code"], "AI Agent Tooling/Framework (developer-facing)")

        record = {
            "human_review_status": "pending_first_pass",
            "human_review_note_template_key": None,
            "human_review_notes": None,
            "llm_prescreen": {
                "status": "succeeded",
                **normalized,
            },
        }
        validate_candidate_review_card(
            record,
            note_templates={
                "approved": "clear end-user product signal; evidence sufficient for staging",
                "hold": "boundary with internal tooling unclear",
                "rejected": "outside observatory scope",
            },
        )

    def test_normalize_llm_result_backfills_source_evidence_summary_when_provider_omits_it(self) -> None:
        provider_result = {
            "decision_snapshot": {
                "recommended_action": "hold_for_human_triage",
                "recommendation_reason": "Metadata-only signal is too thin for automatic promotion.",
            },
            "scope_boundary_note": "No README or excerpt evidence was available in the payload.",
            "review_focus_points": [
                "Inspect the README before deciding whether this is a product or a framework."
            ],
            "confidence_summary": {
                "overall_confidence": "low"
            },
            "handoff_readiness_hint": "Needs quick human review before pool promotion.",
            "taxonomy_hints": {
                "main_category_candidate": "Tentative category",
                "adjacent_category_candidate": "Adjacent category",
                "adjacent_category_rejected_reason": "Not enough evidence yet.",
            },
        }

        normalized = normalize_llm_result(provider_result)
        self.assertEqual(normalized["recommended_action"], "hold")
        self.assertGreaterEqual(len(normalized["source_evidence_summary"]), 1)

    def test_normalize_llm_result_defaults_unknown_recommended_action_to_hold(self) -> None:
        provider_result = {
            "decision_snapshot": {
                "recommended_action": "needs_manual_review",
                "recommendation_reason": "The payload is too sparse for automatic promotion.",
            },
            "scope_boundary_note": "Only minimal metadata is available.",
            "evidence_anchors": [
                {
                    "anchor_rank": 1,
                    "quote": "\"title\": \"agent\"",
                    "why_it_matters": "The title alone is not enough to classify the repo.",
                }
            ],
            "review_focus_points": [
                "Read the README before making any pool decision."
            ],
            "confidence_summary": {
                "overall_confidence": "low"
            },
            "handoff_readiness_hint": "Needs human review.",
            "taxonomy_hints": {
                "main_category_candidate": "Tentative category",
                "adjacent_category_candidate": "Adjacent category",
                "adjacent_category_rejected_reason": "Not enough evidence yet.",
            },
        }

        normalized = normalize_llm_result(provider_result)
        self.assertEqual(normalized["recommended_action"], "hold")
        self.assertEqual(normalized["handoff_readiness_hint"]["suggested_action"], "hold")

    def test_normalize_llm_result_backfills_evidence_anchors_when_provider_omits_them(self) -> None:
        provider_result = {
            "decision_snapshot": {
                "recommended_action": "hold_for_human_triage",
                "recommendation_reason": "No structured evidence was supplied by the provider.",
            },
            "scope_boundary_note": "The payload is sparse and requires human review.",
            "review_focus_points": [
                "Inspect repository documentation before classification."
            ],
            "confidence_summary": {
                "overall_confidence": "low"
            },
            "handoff_readiness_hint": "Needs human review.",
            "taxonomy_hints": {
                "main_category_candidate": "Tentative category",
                "adjacent_category_candidate": "Adjacent category",
                "adjacent_category_rejected_reason": "Not enough evidence yet.",
            },
        }

        normalized = normalize_llm_result(provider_result)
        self.assertGreaterEqual(len(normalized["evidence_anchors"]), 1)
