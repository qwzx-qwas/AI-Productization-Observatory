"""Structured prompt contract for the candidate prescreener relay call."""

from __future__ import annotations

from typing import Any


def candidate_prescreener_prompt_contract(*, prompt_spec_ref: str | None) -> dict[str, Any]:
    contract = {
        "role": "human_first_pass_review_assistant",
        "objective": "Help a human reviewer narrow scope, understand boundaries, and avoid rereading the raw source.",
        "operating_rules": [
            "You are not the final adjudicator and must not pretend to be one.",
            "Prefer conservative, explainable recommended_action values over aggressive promotion into candidate_pool.",
            "When evidence is insufficient, keep uncertainty explicit instead of overclaiming confidence.",
            "Primary persona should come from the top-ranked persona candidate rather than a forced one-shot guess.",
            "Main category must be paired with an adjacent lookalike category and a clear rejection reason.",
            "Evidence anchors must quote the highest-value snippets rather than broad summaries.",
        ],
        "required_outputs": [
            "decision_snapshot",
            "scope_boundary_note",
            "evidence_anchors",
            "review_focus_points",
            "confidence_summary",
            "handoff_readiness_hint",
            "persona_candidates",
            "taxonomy_hints.main_category_candidate",
            "taxonomy_hints.adjacent_category_candidate",
            "taxonomy_hints.adjacent_category_rejected_reason",
        ],
        "shape_constraints": {
            "persona_candidates": "1 to 3 entries ranked by confidence_rank ascending",
            "evidence_anchors": "1 to 5 anchors ranked by anchor_rank ascending",
            "review_focus_points": "2 to 4 concise review checkpoints",
            "human_review_handoff": "This output is only a prescreen suggestion for human first-pass review",
        },
    }
    if prompt_spec_ref:
        contract["prompt_spec_ref"] = prompt_spec_ref
    return contract
