"""Shared candidate prescreen review-card helpers.

The candidate prescreen workspace lives outside the formal gold set, but the
LLM output still needs a stable, human-first review-card shape so relay
normalization, YAML writes, and workspace validation do not drift apart.
"""

from __future__ import annotations

import re
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


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _slugify_label(value: Any) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return normalized or text.lower()


def _map_confidence_level(value: Any) -> str | None:
    text = _string_or_none(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in CONFIDENCE_LEVELS:
        return lowered
    if "high" in lowered:
        return "high"
    if "medium" in lowered:
        return "medium"
    if "low" in lowered:
        return "low"
    return None


def _map_recommended_action(value: Any) -> str | None:
    if isinstance(value, dict):
        nested = value.get("recommended_action")
        if nested is not None:
            return _map_recommended_action(nested)
        return None
    text = _string_or_none(value)
    if text is None:
        return None
    if text in RECOMMENDED_ACTIONS:
        return text
    lowered = text.lower()
    if "whitelist" in lowered:
        return "whitelist_candidate"
    if "candidate_pool" in lowered or ("candidate" in lowered and "pool" in lowered):
        return "candidate_pool"
    if "reject" in lowered:
        return "reject"
    if "hold" in lowered or "triage" in lowered or "manual" in lowered:
        return "hold"
    return None


def _infer_source_field(value: Any) -> str:
    text = _string_or_none(value) or ""
    lowered = text.lower()
    if "raw_evidence_excerpt" in lowered:
        return "raw_evidence_excerpt"
    if "summary" in lowered:
        return "summary"
    if "title" in lowered:
        return "title"
    if "canonical_url" in lowered:
        return "canonical_url"
    if "query_family" in lowered:
        return "query_family"
    return "candidate_input"


def _normalize_evidence_anchors(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    anchors: list[dict[str, Any]] = []
    for index, anchor in enumerate(value, start=1):
        if not isinstance(anchor, dict):
            continue
        evidence_text = _string_or_none(anchor.get("evidence_text")) or _string_or_none(anchor.get("quote"))
        why_it_matters = _string_or_none(anchor.get("why_it_matters")) or _string_or_none(anchor.get("rationale"))
        if evidence_text is None or why_it_matters is None:
            continue
        anchor_rank = anchor.get("anchor_rank")
        if not isinstance(anchor_rank, int) or anchor_rank < 1:
            anchor_rank = index
        applies_to = anchor.get("applies_to")
        normalized_anchor = {
            "anchor_rank": anchor_rank,
            "evidence_text": evidence_text,
            "evidence_source_field": _infer_source_field(anchor.get("evidence_source_field") or anchor.get("quote")),
            "why_it_matters": why_it_matters,
        }
        if isinstance(applies_to, list):
            normalized_anchor["applies_to"] = [item for item in applies_to if isinstance(item, str)]
        anchors.append(normalized_anchor)
    anchors.sort(key=lambda anchor: anchor["anchor_rank"])
    for expected_rank, anchor in enumerate(anchors, start=1):
        anchor["anchor_rank"] = expected_rank
    return anchors[:5]


def _ensure_minimum_evidence_anchor(
    anchors: list[dict[str, Any]],
    *,
    fallback_reason: str | None,
    fallback_scope_note: str | None,
) -> list[dict[str, Any]]:
    if anchors:
        return anchors
    evidence_text = fallback_reason or fallback_scope_note
    if evidence_text is None:
        evidence_text = "Provider response omitted explicit evidence anchors; prescreen remains low-confidence and requires human review."
    return [
        {
            "anchor_rank": 1,
            "evidence_text": evidence_text,
            "evidence_source_field": "candidate_input",
            "why_it_matters": "This fallback anchor preserves a minimally explainable first-pass review card when the provider omits structured evidence anchors.",
            "applies_to": ["scope", "recommended_action"],
        }
    ]


def _normalize_source_evidence_summary(
    result: dict[str, Any],
    anchors: list[dict[str, Any]],
    *,
    fallback_reason: str | None,
    fallback_scope_note: str | None,
) -> list[str]:
    summary = result.get("source_evidence_summary")
    if isinstance(summary, list):
        normalized = [item for item in summary if isinstance(item, str) and item.strip()]
        if normalized:
            return normalized
    derived = [anchor["evidence_text"] for anchor in anchors[:3] if isinstance(anchor.get("evidence_text"), str)]
    if derived:
        return derived
    fallback = []
    if fallback_reason:
        fallback.append(fallback_reason)
    if fallback_scope_note and fallback_scope_note not in fallback:
        fallback.append(fallback_scope_note)
    review_focus_points = result.get("review_focus_points")
    if isinstance(review_focus_points, list):
        for item in review_focus_points:
            if isinstance(item, str) and item.strip() and item not in fallback:
                fallback.append(item)
                break
    return fallback


def _normalize_uncertainty_points(result: dict[str, Any], confidence_summary: dict[str, Any], decision_snapshot: Any) -> list[str]:
    uncertainty_points = result.get("uncertainty_points")
    if isinstance(uncertainty_points, list):
        normalized = [item for item in uncertainty_points if isinstance(item, str) and item.strip()]
        if normalized is not None:
            return normalized
    derived: list[str] = []
    if isinstance(confidence_summary.get("uncertainty_reasons"), list):
        derived.extend(item for item in confidence_summary["uncertainty_reasons"] if isinstance(item, str) and item.strip())
    if isinstance(confidence_summary.get("uncertainty_drivers"), list):
        derived.extend(item for item in confidence_summary["uncertainty_drivers"] if isinstance(item, str) and item.strip())
    if isinstance(decision_snapshot, dict) and isinstance(decision_snapshot.get("risk_flags"), list):
        derived.extend(str(item) for item in decision_snapshot["risk_flags"] if isinstance(item, str) and item.strip())
    return derived


def _normalize_confidence_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return empty_confidence_summary()
    normalized = empty_confidence_summary()
    for field_name in ("scope_confidence", "taxonomy_confidence", "persona_confidence"):
        normalized[field_name] = _map_confidence_level(value.get(field_name))
    overall = _map_confidence_level(value.get("overall_confidence"))
    if overall is not None:
        for field_name, current_value in normalized.items():
            if current_value is None:
                normalized[field_name] = overall
    uncertainty_level = _string_or_none(value.get("uncertainty_level"))
    if uncertainty_level == "high":
        normalized["persona_confidence"] = normalized["persona_confidence"] or "low"
        normalized["taxonomy_confidence"] = normalized["taxonomy_confidence"] or "low"
        normalized["scope_confidence"] = normalized["scope_confidence"] or "low"
    for field_name, current_value in normalized.items():
        if current_value is None:
            normalized[field_name] = "low"
    return normalized


def _normalize_handoff_hint(value: Any, *, recommended_action: str | None) -> dict[str, Any]:
    normalized = empty_handoff_readiness_hint()
    if isinstance(value, dict):
        normalized["suggested_action"] = _map_recommended_action(value.get("suggested_action")) or _map_recommended_action(value)
        rationale = _string_or_none(value.get("rationale"))
        if rationale is None:
            why = _string_or_none(value.get("why"))
            risk = _string_or_none(value.get("risk_if_misclassified"))
            if why and risk:
                rationale = f"{why} Risk if misclassified: {risk}"
            else:
                rationale = why or risk
        normalized["rationale"] = rationale
    elif isinstance(value, str):
        normalized["rationale"] = value.strip()
    if normalized["suggested_action"] is None:
        normalized["suggested_action"] = recommended_action
    return normalized


def _normalize_persona_candidates(value: Any, *, anchor_refs: list[int]) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(value, list):
        return [], None
    candidates: list[dict[str, Any]] = []
    primary_persona_code: str | None = None
    for index, candidate in enumerate(value, start=1):
        if not isinstance(candidate, dict):
            continue
        persona_code = _string_or_none(candidate.get("persona_code")) or _slugify_label(candidate.get("persona"))
        rationale = _string_or_none(candidate.get("rationale")) or _string_or_none(candidate.get("fit_rationale"))
        if persona_code is None or rationale is None:
            continue
        rank = candidate.get("confidence_rank")
        if not isinstance(rank, int) or rank < 1:
            rank = index
        refs = candidate.get("supporting_evidence_anchors")
        supporting_refs = [value for value in refs if isinstance(value, int)] if isinstance(refs, list) else anchor_refs[:2]
        normalized_candidate = {
            "persona_code": persona_code,
            "confidence_rank": rank,
            "rationale": rationale,
            "supporting_evidence_anchors": supporting_refs,
        }
        candidates.append(normalized_candidate)
    candidates.sort(key=lambda candidate: candidate["confidence_rank"])
    for expected_rank, candidate in enumerate(candidates, start=1):
        candidate["confidence_rank"] = expected_rank
    if candidates:
        primary_persona_code = candidates[0]["persona_code"]
    return candidates[:3], primary_persona_code


def _normalize_taxonomy_hints(
    value: Any,
    *,
    fallback_reason: str | None,
    primary_persona_code: str | None,
    anchor_refs: list[int],
) -> dict[str, Any]:
    normalized = empty_taxonomy_hints()
    if not isinstance(value, dict):
        return normalized
    primary_category_code = _string_or_none(value.get("primary_category_code"))
    main_candidate = value.get("main_category_candidate")
    if isinstance(main_candidate, dict):
        normalized["main_category_candidate"] = _normalize_candidate(main_candidate)
        primary_category_code = primary_category_code or normalized["main_category_candidate"]["category_code"]
    else:
        main_label = _string_or_none(main_candidate)
        if main_label is not None:
            primary_category_code = primary_category_code or main_label
            normalized["main_category_candidate"] = {
                "category_code": primary_category_code,
                "rationale": fallback_reason or main_label,
                "supporting_evidence_anchors": anchor_refs[:2],
            }
    adjacent_candidate = value.get("adjacent_category_candidate")
    if isinstance(adjacent_candidate, dict):
        normalized["adjacent_category_candidate"] = _normalize_candidate(adjacent_candidate, adjacent=True)
    else:
        adjacent_label = _string_or_none(adjacent_candidate)
        if adjacent_label is not None:
            normalized["adjacent_category_candidate"] = {
                "category_code": adjacent_label,
                "rationale_for_similarity": adjacent_label,
                "supporting_evidence_anchors": anchor_refs[:2],
            }
    normalized["primary_category_code"] = primary_category_code
    normalized["secondary_category_code"] = _string_or_none(value.get("secondary_category_code"))
    normalized["primary_persona_code"] = _string_or_none(value.get("primary_persona_code")) or primary_persona_code
    normalized["delivery_form_code"] = _string_or_none(value.get("delivery_form_code"))
    normalized["adjacent_category_rejected_reason"] = _string_or_none(value.get("adjacent_category_rejected_reason"))
    if normalized["main_category_candidate"]["rationale"] is None and fallback_reason is not None:
        normalized["main_category_candidate"]["rationale"] = fallback_reason
    return normalized


def _normalize_assessment_hints(value: Any, *, confidence_summary: dict[str, Any], recommended_action: str | None) -> dict[str, Any]:
    normalized = {
        "evidence_strength": None,
        "build_evidence_band": None,
        "need_clarity_band": None,
        "unresolved_risk": None,
    }
    if isinstance(value, dict):
        for field_name in normalized:
            normalized[field_name] = _map_confidence_level(value.get(field_name))
    scope_confidence = confidence_summary.get("scope_confidence")
    normalized["evidence_strength"] = normalized["evidence_strength"] or scope_confidence
    normalized["build_evidence_band"] = normalized["build_evidence_band"] or scope_confidence
    if normalized["need_clarity_band"] is None:
        normalized["need_clarity_band"] = "high" if recommended_action == "hold" else confidence_summary.get("taxonomy_confidence")
    if normalized["unresolved_risk"] is None:
        normalized["unresolved_risk"] = "high" if recommended_action == "hold" else confidence_summary.get("persona_confidence")
    return normalized


def normalize_llm_result(result: dict[str, Any]) -> dict[str, Any]:
    decision_snapshot = result.get("decision_snapshot")
    taxonomy_hints = result.get("taxonomy_hints") if isinstance(result.get("taxonomy_hints"), dict) else {}
    confidence_summary = _normalize_confidence_summary(result.get("confidence_summary"))
    anchors = _normalize_evidence_anchors(result.get("evidence_anchors"))
    recommended_action = _map_recommended_action(result.get("recommended_action")) or _map_recommended_action(decision_snapshot)
    scope_boundary_note = _string_or_none(result.get("scope_boundary_note"))
    reason = _string_or_none(result.get("reason"))
    if reason is None and isinstance(decision_snapshot, dict):
        reason = (
            _string_or_none(decision_snapshot.get("rationale"))
            or _string_or_none(decision_snapshot.get("recommendation_reason"))
            or _string_or_none(decision_snapshot.get("why"))
        )
    decision_snapshot_text = _string_or_none(decision_snapshot)
    if decision_snapshot_text is None and isinstance(decision_snapshot, dict):
        snapshot_rationale = _string_or_none(decision_snapshot.get("rationale")) or _string_or_none(
            decision_snapshot.get("recommendation_reason")
        )
        if recommended_action and snapshot_rationale:
            decision_snapshot_text = f"Recommend {recommended_action} because {snapshot_rationale}"
        else:
            decision_snapshot_text = snapshot_rationale or _string_or_none(decision_snapshot.get("prescreen_outcome"))
    source_evidence_summary = _normalize_source_evidence_summary(
        result,
        anchors,
        fallback_reason=reason,
        fallback_scope_note=scope_boundary_note,
    )
    uncertainty_points = _normalize_uncertainty_points(result, result.get("confidence_summary") if isinstance(result.get("confidence_summary"), dict) else {}, decision_snapshot)
    recommend_candidate_pool = result.get("recommend_candidate_pool")
    handoff_hint = _normalize_handoff_hint(result.get("handoff_readiness_hint"), recommended_action=recommended_action)
    reason = reason or handoff_hint.get("rationale") or scope_boundary_note
    if recommended_action is None:
        recommended_action = _map_recommended_action(handoff_hint.get("suggested_action"))
    if recommended_action is None and (
        reason is not None
        or scope_boundary_note is not None
        or anchors
        or (isinstance(result.get("review_focus_points"), list) and result.get("review_focus_points"))
    ):
        recommended_action = "hold"
    if reason is None and source_evidence_summary:
        reason = source_evidence_summary[0]
    anchors = _ensure_minimum_evidence_anchor(
        anchors,
        fallback_reason=reason,
        fallback_scope_note=scope_boundary_note,
    )
    source_evidence_summary = source_evidence_summary or [anchors[0]["evidence_text"]]
    if decision_snapshot_text is None and recommended_action and reason:
        decision_snapshot_text = f"Recommend {recommended_action} because {reason}"
    if decision_snapshot_text is None:
        decision_snapshot_text = reason
    if recommended_action in {"candidate_pool", "whitelist_candidate"}:
        recommend_candidate_pool = True
    elif recommended_action in {"reject", "hold"}:
        recommend_candidate_pool = False
    anchor_refs = [anchor["anchor_rank"] for anchor in anchors]
    persona_candidates, primary_persona_code = _normalize_persona_candidates(result.get("persona_candidates"), anchor_refs=anchor_refs)
    if not persona_candidates:
        persona_candidates = [
            {
                "persona_code": "unknown",
                "confidence_rank": 1,
                "rationale": reason or "Provider response did not supply a reliable primary persona candidate.",
                "supporting_evidence_anchors": anchor_refs[:1],
            }
        ]
        primary_persona_code = "unknown"
    taxonomy_hints_normalized = _normalize_taxonomy_hints(
        taxonomy_hints,
        fallback_reason=reason or decision_snapshot_text,
        primary_persona_code=primary_persona_code,
        anchor_refs=anchor_refs,
    )
    assessment_hints = _normalize_assessment_hints(result.get("assessment_hints"), confidence_summary=confidence_summary, recommended_action=recommended_action)
    handoff_hint["suggested_action"] = handoff_hint.get("suggested_action") or recommended_action
    normalized = {
        "in_observatory_scope": result.get("in_observatory_scope"),
        "reason": reason,
        "decision_snapshot": decision_snapshot_text,
        "scope_boundary_note": scope_boundary_note,
        "source_evidence_summary": source_evidence_summary,
        "evidence_anchors": anchors,
        "review_focus_points": result.get("review_focus_points") if isinstance(result.get("review_focus_points"), list) else [],
        "uncertainty_points": uncertainty_points,
        "recommend_candidate_pool": recommend_candidate_pool,
        "recommended_action": recommended_action,
        "confidence_summary": confidence_summary,
        "handoff_readiness_hint": handoff_hint,
        "persona_candidates": persona_candidates,
        "taxonomy_hints": taxonomy_hints_normalized,
        "assessment_hints": assessment_hints,
    }
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
