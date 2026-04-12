"""Rule-first taxonomy classification for the Phase1-D baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.files import load_yaml, utc_now_iso
from src.common.schema import validate_instance

MODULE_NAME = "taxonomy_classifier"
MODEL_OR_RULE_VERSION = "taxonomy_classifier_v1"

_CATEGORY_KEYWORDS = {
    "JTBD_CONTENT": {"write", "copy", "blog", "image", "video", "newsletter", "script"},
    "JTBD_KNOWLEDGE": {"answer", "search", "docs", "knowledge", "research", "q&a", "summarize"},
    "JTBD_PRODUCTIVITY_AUTOMATION": {"automate", "workflow", "route", "agent", "approval", "orchestrate"},
    "JTBD_DEV_TOOLS": {"developer", "engineer", "code", "debug", "test", "repo", "sdk", "api"},
    "JTBD_MARKETING_GROWTH": {"marketing", "seo", "campaign", "ad", "landing page", "growth"},
    "JTBD_SALES_SUPPORT": {"crm", "ticket", "support", "reply", "sales", "customer"},
}


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_product",
        "version_dependency": MODEL_OR_RULE_VERSION,
    }


def classify_product(
    product_profile: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    config_dir: Path,
    schema_dir: Path,
    assigned_at: str | None = None,
    model_or_rule_version: str = MODEL_OR_RULE_VERSION,
) -> list[dict[str, Any]]:
    taxonomy = load_yaml(config_dir / "taxonomy_v0.yaml")
    allowed_codes = {node["code"] for node in taxonomy["nodes"]}
    assigned_timestamp = assigned_at or utc_now_iso()
    scores = _score_categories(product_profile, evidence)
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    top_code, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    unresolved_code = taxonomy["assignment_policy"]["unresolved_code"]
    has_unclear_signal = any(item["evidence_type"] == "unclear_description_signal" for item in evidence)
    broad_claim_text = " ".join(
        [
            product_profile.get("one_sentence_job") or "",
            product_profile.get("summary") or "",
            " ".join(item["snippet"] for item in evidence if item["evidence_type"] == "unclear_description_signal"),
        ]
    ).lower()
    broad_claim_markers = ("general ai assistant", "for everyone", "any writing", "any research task", "all-in-one ai")

    if (
        top_score <= 0
        or top_score == second_score
        or (has_unclear_signal and top_score <= 2)
        or any(marker in broad_claim_text for marker in broad_claim_markers)
    ):
        category_code = unresolved_code
        confidence = 0.45 if top_score > 0 else 0.2
        rationale = "Evidence does not support a uniquely identifiable primary job; route to unresolved."
    else:
        category_code = top_code if top_code in allowed_codes else unresolved_code
        confidence = min(0.95, 0.5 + (top_score / 10))
        rationale = f"Primary evidence most strongly supports {category_code}."

    assignment = {
        "target_type": "product",
        "target_id": product_profile["product_id"],
        "taxonomy_version": taxonomy["version"],
        "label_level": 1,
        "label_role": "primary",
        "category_code": category_code,
        "confidence": round(confidence, 2),
        "rationale": rationale,
        "assigned_by": MODULE_NAME,
        "model_or_rule_version": model_or_rule_version,
        "assigned_at": assigned_timestamp,
        "is_override": None,
        "override_review_issue_id": None,
        "result_status": "active",
        "effective_from": assigned_timestamp,
        "supersedes_assignment_id": None,
        "evidence_refs_json": [_evidence_ref(item) for item in evidence[:3]],
    }
    validate_instance(assignment, schema_dir / "taxonomy_assignment.schema.json")
    return [assignment]


def _score_categories(product_profile: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, int]:
    corpus = " ".join(
        [
            product_profile.get("one_sentence_job") or "",
            product_profile.get("summary") or "",
            " ".join(item["snippet"] for item in evidence),
        ]
    ).lower()
    scores: dict[str, int] = {category: 0 for category in _CATEGORY_KEYWORDS}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in corpus:
                scores[category] += 2 if keyword in (product_profile.get("one_sentence_job") or "").lower() else 1
    if product_profile.get("primary_persona_code") == "developer":
        scores["JTBD_DEV_TOOLS"] += 2
    if product_profile.get("primary_persona_code") == "marketer":
        scores["JTBD_MARKETING_GROWTH"] += 2
    if product_profile.get("primary_persona_code") in {"sales_rep", "support_agent"}:
        scores["JTBD_SALES_SUPPORT"] += 2
    return scores


def _evidence_ref(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": evidence["source_item_id"],
        "evidence_type": evidence["evidence_type"],
        "source_url": evidence["source_url"],
    }
