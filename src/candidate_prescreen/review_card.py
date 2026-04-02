"""Shared candidate prescreen review-card helpers.

The candidate prescreen workspace lives outside the formal gold set, but the
LLM output still needs a stable, human-first review-card shape so relay
normalization, YAML writes, and workspace validation do not drift apart.
"""

from __future__ import annotations

from typing import Any

from src.common.errors import ContractValidationError

RECOMMENDED_ACTIONS = {"reject", "hold", "candidate_pool", "whitelist_candidate"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}
HUMAN_REVIEW_STATUS_TO_TEMPLATE_KEY = {
    "approved_for_staging": "approved",
    "on_hold": "hold",
    "rejected_after_human_review": "rejected",
}


def _empty_category_candidate() -> dict[str, Any]:
    return {
        "category_code": None,
        "rationale": None,
        "supporting_evidence_anchors": [],
    }


def _empty_adjacent_category_candidate() -> dict[str, Any]:
    return {
        "category_code": None,
        "rationale_for_similarity": None,
        "supporting_evidence_anchors": [],
    }


def empty_taxonomy_hints() -> dict[str, Any]:
    return {
        "primary_category_code": None,
        "secondary_category_code": None,
        "primary_persona_code": None,
        "delivery_form_code": None,
        "main_category_candidate": _empty_category_candidate(),
        "adjacent_category_candidate": _empty_adjacent_category_candidate(),
        "adjacent_category_rejected_reason": None,
    }


def empty_confidence_summary() -> dict[str, Any]:
    return {
        "scope_confidence": None,
        "taxonomy_confidence": None,
        "persona_confidence": None,
    }


def empty_handoff_readiness_hint() -> dict[str, Any]:
    return {
        "suggested_action": None,
        "rationale": None,
    }


def empty_llm_prescreen(
    *,
    prompt_version: str,
    routing_version: str,
    relay_client_version: str,
    relay_transport: str,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "in_observatory_scope": None,
        "reason": None,
        "decision_snapshot": None,
        "scope_boundary_note": None,
        "source_evidence_summary": [],
        "evidence_anchors": [],
        "review_focus_points": [],
        "uncertainty_points": [],
        "recommend_candidate_pool": None,
        "recommended_action": None,
        "confidence_summary": empty_confidence_summary(),
        "handoff_readiness_hint": empty_handoff_readiness_hint(),
        "persona_candidates": [],
        "taxonomy_hints": empty_taxonomy_hints(),
        "assessment_hints": {
            "evidence_strength": None,
            "build_evidence_band": None,
            "need_clarity_band": None,
            "unresolved_risk": None,
        },
        "channel_metadata": {
            "prompt_version": prompt_version,
            "routing_version": routing_version,
            "relay_client_version": relay_client_version,
            "model": None,
            "transport": relay_transport,
            "request_id": None,
        },
        "error_type": None,
        "error_message": None,
    }


def _normalize_candidate(candidate: Any, *, adjacent: bool = False) -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return _empty_adjacent_category_candidate() if adjacent else _empty_category_candidate()
    normalized = _empty_adjacent_category_candidate() if adjacent else _empty_category_candidate()
    category_code = candidate.get("category_code")
    if isinstance(category_code, str) or category_code is None:
        normalized["category_code"] = category_code
    rationale_key = "rationale_for_similarity" if adjacent else "rationale"
    rationale_value = candidate.get(rationale_key)
    if isinstance(rationale_value, str) or rationale_value is None:
        normalized[rationale_key] = rationale_value
    anchors = candidate.get("supporting_evidence_anchors")
    if isinstance(anchors, list):
        normalized["supporting_evidence_anchors"] = [value for value in anchors if isinstance(value, int)]
    return normalized


def normalize_llm_result(result: dict[str, Any]) -> dict[str, Any]:
    taxonomy_hints = result.get("taxonomy_hints") if isinstance(result.get("taxonomy_hints"), dict) else {}
    confidence_summary = result.get("confidence_summary") if isinstance(result.get("confidence_summary"), dict) else {}
    handoff_hint = result.get("handoff_readiness_hint") if isinstance(result.get("handoff_readiness_hint"), dict) else {}
    normalized = {
        "in_observatory_scope": result.get("in_observatory_scope"),
        "reason": result.get("reason"),
        "decision_snapshot": result.get("decision_snapshot"),
        "scope_boundary_note": result.get("scope_boundary_note"),
        "source_evidence_summary": result.get("source_evidence_summary") if isinstance(result.get("source_evidence_summary"), list) else [],
        "evidence_anchors": result.get("evidence_anchors") if isinstance(result.get("evidence_anchors"), list) else [],
        "review_focus_points": result.get("review_focus_points") if isinstance(result.get("review_focus_points"), list) else [],
        "uncertainty_points": result.get("uncertainty_points") if isinstance(result.get("uncertainty_points"), list) else [],
        "recommend_candidate_pool": result.get("recommend_candidate_pool"),
        "recommended_action": result.get("recommended_action"),
        "confidence_summary": empty_confidence_summary(),
        "handoff_readiness_hint": empty_handoff_readiness_hint(),
        "persona_candidates": result.get("persona_candidates") if isinstance(result.get("persona_candidates"), list) else [],
        "taxonomy_hints": empty_taxonomy_hints(),
        "assessment_hints": result.get("assessment_hints") if isinstance(result.get("assessment_hints"), dict) else {},
    }
    for field_name in ("scope_confidence", "taxonomy_confidence", "persona_confidence"):
        field_value = confidence_summary.get(field_name)
        if isinstance(field_value, str) or field_value is None:
            normalized["confidence_summary"][field_name] = field_value
    for field_name in ("suggested_action", "rationale"):
        field_value = handoff_hint.get(field_name)
        if isinstance(field_value, str) or field_value is None:
            normalized["handoff_readiness_hint"][field_name] = field_value
    for field_name in ("primary_category_code", "secondary_category_code", "primary_persona_code", "delivery_form_code", "adjacent_category_rejected_reason"):
        field_value = taxonomy_hints.get(field_name)
        if isinstance(field_value, str) or field_value is None:
            normalized["taxonomy_hints"][field_name] = field_value
    normalized["taxonomy_hints"]["main_category_candidate"] = _normalize_candidate(taxonomy_hints.get("main_category_candidate"))
    normalized["taxonomy_hints"]["adjacent_category_candidate"] = _normalize_candidate(
        taxonomy_hints.get("adjacent_category_candidate"),
        adjacent=True,
    )
    return normalized


def _require_mapping(value: Any, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{description} must be an object")
    return value


def _require_non_empty_string(value: Any, description: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{description} must be a non-empty string")
    return value


def _require_string_list(value: Any, description: str, *, min_items: int = 0, max_items: int | None = None) -> list[str]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{description} must be a list")
    if len(value) < min_items:
        raise ContractValidationError(f"{description} must contain at least {min_items} items")
    if max_items is not None and len(value) > max_items:
        raise ContractValidationError(f"{description} must contain at most {max_items} items")
    normalized: list[str] = []
    for index, item in enumerate(value, start=1):
        normalized.append(_require_non_empty_string(item, f"{description}[{index}]"))
    return normalized


def _require_anchor_refs(value: Any, description: str, *, valid_ranks: set[int]) -> list[int]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{description} must be a list")
    refs: list[int] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, int):
            raise ContractValidationError(f"{description}[{index}] must be an integer anchor rank")
        if item not in valid_ranks:
            raise ContractValidationError(f"{description}[{index}] references missing evidence anchor rank {item}")
        refs.append(item)
    return refs


def _validate_evidence_anchors(value: Any) -> set[int]:
    if not isinstance(value, list):
        raise ContractValidationError("llm_prescreen.evidence_anchors must be a list")
    if len(value) < 1 or len(value) > 5:
        raise ContractValidationError("llm_prescreen.evidence_anchors must contain 1 to 5 anchors when prescreen succeeds")
    expected_rank = 1
    valid_ranks: set[int] = set()
    for anchor in value:
        anchor_mapping = _require_mapping(anchor, "llm_prescreen.evidence_anchors[]")
        anchor_rank = anchor_mapping.get("anchor_rank")
        if not isinstance(anchor_rank, int) or anchor_rank != expected_rank:
            raise ContractValidationError("llm_prescreen.evidence_anchors anchor_rank values must be 1..N in order")
        valid_ranks.add(anchor_rank)
        expected_rank += 1
        _require_non_empty_string(anchor_mapping.get("evidence_text"), f"llm_prescreen.evidence_anchors[{anchor_rank}].evidence_text")
        _require_non_empty_string(
            anchor_mapping.get("evidence_source_field"),
            f"llm_prescreen.evidence_anchors[{anchor_rank}].evidence_source_field",
        )
        _require_non_empty_string(anchor_mapping.get("why_it_matters"), f"llm_prescreen.evidence_anchors[{anchor_rank}].why_it_matters")
    return valid_ranks


def _validate_confidence_summary(value: Any) -> None:
    summary = _require_mapping(value, "llm_prescreen.confidence_summary")
    for field_name in ("scope_confidence", "taxonomy_confidence", "persona_confidence"):
        field_value = summary.get(field_name)
        if field_value not in CONFIDENCE_LEVELS:
            raise ContractValidationError(f"llm_prescreen.confidence_summary.{field_name} must be one of low|medium|high")


def _validate_taxonomy_hints(value: Any, *, valid_ranks: set[int]) -> None:
    hints = _require_mapping(value, "llm_prescreen.taxonomy_hints")
    primary_category_code = _require_non_empty_string(
        hints.get("primary_category_code"),
        "llm_prescreen.taxonomy_hints.primary_category_code",
    )
    main_candidate = _require_mapping(hints.get("main_category_candidate"), "llm_prescreen.taxonomy_hints.main_category_candidate")
    main_category_code = _require_non_empty_string(
        main_candidate.get("category_code"),
        "llm_prescreen.taxonomy_hints.main_category_candidate.category_code",
    )
    if main_category_code != primary_category_code:
        raise ContractValidationError("main_category_candidate.category_code must match taxonomy_hints.primary_category_code")
    _require_non_empty_string(main_candidate.get("rationale"), "llm_prescreen.taxonomy_hints.main_category_candidate.rationale")
    _require_anchor_refs(
        main_candidate.get("supporting_evidence_anchors"),
        "llm_prescreen.taxonomy_hints.main_category_candidate.supporting_evidence_anchors",
        valid_ranks=valid_ranks,
    )

    adjacent_candidate = _require_mapping(
        hints.get("adjacent_category_candidate"),
        "llm_prescreen.taxonomy_hints.adjacent_category_candidate",
    )
    adjacent_category_code = _require_non_empty_string(
        adjacent_candidate.get("category_code"),
        "llm_prescreen.taxonomy_hints.adjacent_category_candidate.category_code",
    )
    if adjacent_category_code == primary_category_code:
        raise ContractValidationError("adjacent_category_candidate.category_code must differ from primary_category_code")
    _require_non_empty_string(
        adjacent_candidate.get("rationale_for_similarity"),
        "llm_prescreen.taxonomy_hints.adjacent_category_candidate.rationale_for_similarity",
    )
    _require_anchor_refs(
        adjacent_candidate.get("supporting_evidence_anchors"),
        "llm_prescreen.taxonomy_hints.adjacent_category_candidate.supporting_evidence_anchors",
        valid_ranks=valid_ranks,
    )
    _require_non_empty_string(
        hints.get("adjacent_category_rejected_reason"),
        "llm_prescreen.taxonomy_hints.adjacent_category_rejected_reason",
    )


def _validate_persona_candidates(value: Any, *, primary_persona_code: Any, valid_ranks: set[int]) -> None:
    if not isinstance(value, list):
        raise ContractValidationError("llm_prescreen.persona_candidates must be a list")
    if len(value) < 1 or len(value) > 3:
        raise ContractValidationError("llm_prescreen.persona_candidates must contain 1 to 3 ranked candidates when prescreen succeeds")
    expected_rank = 1
    first_persona_code: str | None = None
    for candidate in value:
        candidate_mapping = _require_mapping(candidate, "llm_prescreen.persona_candidates[]")
        rank = candidate_mapping.get("confidence_rank")
        if not isinstance(rank, int) or rank != expected_rank:
            raise ContractValidationError("llm_prescreen.persona_candidates confidence_rank values must be 1..N in order")
        expected_rank += 1
        persona_code = _require_non_empty_string(candidate_mapping.get("persona_code"), f"llm_prescreen.persona_candidates[{rank}].persona_code")
        if first_persona_code is None:
            first_persona_code = persona_code
        _require_non_empty_string(candidate_mapping.get("rationale"), f"llm_prescreen.persona_candidates[{rank}].rationale")
        _require_anchor_refs(
            candidate_mapping.get("supporting_evidence_anchors"),
            f"llm_prescreen.persona_candidates[{rank}].supporting_evidence_anchors",
            valid_ranks=valid_ranks,
        )
    if primary_persona_code != first_persona_code:
        raise ContractValidationError("taxonomy_hints.primary_persona_code must match the rank-1 persona candidate")


def _validate_human_review_notes(record: dict[str, Any], *, note_templates: dict[str, str]) -> None:
    status = record.get("human_review_status")
    note_key = record.get("human_review_note_template_key")
    note_text = record.get("human_review_notes")
    if status == "pending_first_pass":
        if note_key is not None or note_text is not None:
            raise ContractValidationError(
                "pending_first_pass candidates must keep human_review_note_template_key and human_review_notes as null"
            )
        return
    expected_key = HUMAN_REVIEW_STATUS_TO_TEMPLATE_KEY.get(status)
    if expected_key is None:
        raise ContractValidationError(f"Unsupported human_review_status for candidate prescreen: {status}")
    if note_key != expected_key:
        raise ContractValidationError(f"human_review_note_template_key must be {expected_key} when human_review_status = {status}")
    template_prefix = note_templates.get(expected_key)
    if not template_prefix:
        raise ContractValidationError(f"Missing human review note template for key {expected_key}")
    note = _require_non_empty_string(note_text, "human_review_notes")
    if note != template_prefix and not note.startswith(f"{template_prefix}; "):
        raise ContractValidationError(
            "human_review_notes must equal the standard template or start with it followed by '; ' for extra detail"
        )


def validate_candidate_review_card(record: dict[str, Any], *, note_templates: dict[str, str]) -> None:
    _validate_human_review_notes(record, note_templates=note_templates)
    llm_prescreen = _require_mapping(record.get("llm_prescreen"), "llm_prescreen")
    if llm_prescreen.get("status") != "succeeded":
        return

    _require_non_empty_string(llm_prescreen.get("reason"), "llm_prescreen.reason")
    _require_non_empty_string(llm_prescreen.get("decision_snapshot"), "llm_prescreen.decision_snapshot")
    _require_non_empty_string(llm_prescreen.get("scope_boundary_note"), "llm_prescreen.scope_boundary_note")
    _require_string_list(llm_prescreen.get("source_evidence_summary"), "llm_prescreen.source_evidence_summary", min_items=1)
    valid_anchor_ranks = _validate_evidence_anchors(llm_prescreen.get("evidence_anchors"))
    _require_string_list(llm_prescreen.get("review_focus_points"), "llm_prescreen.review_focus_points", min_items=2, max_items=4)
    _require_string_list(llm_prescreen.get("uncertainty_points"), "llm_prescreen.uncertainty_points")
    recommended_action = llm_prescreen.get("recommended_action")
    if recommended_action not in RECOMMENDED_ACTIONS:
        raise ContractValidationError("llm_prescreen.recommended_action must be one of reject|hold|candidate_pool|whitelist_candidate")
    recommend_candidate_pool = llm_prescreen.get("recommend_candidate_pool")
    if recommended_action in {"candidate_pool", "whitelist_candidate"} and recommend_candidate_pool is not True:
        raise ContractValidationError("recommend_candidate_pool must be true when recommended_action routes into the candidate pool")
    if recommended_action in {"reject", "hold"} and recommend_candidate_pool is not False:
        raise ContractValidationError("recommend_candidate_pool must be false when recommended_action is reject or hold")

    _validate_confidence_summary(llm_prescreen.get("confidence_summary"))
    handoff_hint = _require_mapping(llm_prescreen.get("handoff_readiness_hint"), "llm_prescreen.handoff_readiness_hint")
    if handoff_hint.get("suggested_action") != recommended_action:
        raise ContractValidationError("handoff_readiness_hint.suggested_action must match llm_prescreen.recommended_action")
    _require_non_empty_string(handoff_hint.get("rationale"), "llm_prescreen.handoff_readiness_hint.rationale")

    taxonomy_hints = _require_mapping(llm_prescreen.get("taxonomy_hints"), "llm_prescreen.taxonomy_hints")
    primary_persona_code = _require_non_empty_string(
        taxonomy_hints.get("primary_persona_code"),
        "llm_prescreen.taxonomy_hints.primary_persona_code",
    )
    _validate_persona_candidates(
        llm_prescreen.get("persona_candidates"),
        primary_persona_code=primary_persona_code,
        valid_ranks=valid_anchor_ranks,
    )
    _validate_taxonomy_hints(taxonomy_hints, valid_ranks=valid_anchor_ranks)
