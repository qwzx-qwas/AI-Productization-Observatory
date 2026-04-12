"""Rule-based product profiling constrained by frozen vocabularies."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.files import load_yaml, utc_now_iso
from src.common.schema import validate_instance

MODULE_NAME = "product_profiler"
PROFILE_VERSION = "product_profiler_v1"


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_product",
        "version_dependency": PROFILE_VERSION,
    }


def build_product_profile(
    product: dict[str, Any],
    source_item: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    config_dir: Path,
    schema_dir: Path,
    profile_version: str = PROFILE_VERSION,
    extracted_at: str | None = None,
) -> dict[str, Any]:
    persona_codes = set(load_yaml(config_dir / "persona_v0.yaml")["codes"])
    delivery_form_codes = set(load_yaml(config_dir / "delivery_form_v0.yaml")["codes"])

    one_sentence_job = _derive_job(source_item, evidence)
    primary_persona_code = _derive_persona(source_item, evidence)
    delivery_form_code = _derive_delivery_form(source_item, evidence)

    if primary_persona_code not in persona_codes:
        primary_persona_code = "unknown"
    if delivery_form_code not in delivery_form_codes:
        delivery_form_code = "unknown"

    profile = {
        "product_id": product["product_id"],
        "profile_version": profile_version,
        "one_sentence_job": one_sentence_job,
        "primary_persona_code": primary_persona_code,
        "delivery_form_code": delivery_form_code,
        "summary": source_item.get("current_summary") or source_item.get("raw_text_excerpt"),
        "evidence_refs_json": [_evidence_ref(item) for item in evidence],
        "extracted_at": extracted_at or utc_now_iso(),
        "extracted_by": PROFILE_VERSION,
    }
    validate_instance(profile, schema_dir / "product_profile.schema.json")
    return profile


def _derive_job(source_item: dict[str, Any], evidence: list[dict[str, Any]]) -> str | None:
    for item in evidence:
        if item["evidence_type"] == "job_statement":
            return item["snippet"]
    return source_item.get("current_summary") or source_item.get("title")


def _derive_persona(source_item: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            source_item.get("title") or "",
            source_item.get("current_summary") or "",
            source_item.get("raw_text_excerpt") or "",
            " ".join(item["snippet"] for item in evidence if item["evidence_type"] == "target_user_claim"),
        ]
    ).lower()
    keyword_map = {
        "developer": "developer",
        "engineer": "developer",
        "marketer": "marketer",
        "sales": "sales_rep",
        "support": "support_agent",
        "researcher": "researcher",
        "founder": "founder",
        "analyst": "analyst",
        "designer": "designer",
    }
    for keyword, persona_code in keyword_map.items():
        if keyword in text:
            return persona_code
    return "unknown"


def _derive_delivery_form(source_item: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    text = " ".join(
        [
            source_item.get("title") or "",
            source_item.get("current_summary") or "",
            source_item.get("raw_text_excerpt") or "",
            " ".join(item["snippet"] for item in evidence if item["evidence_type"] == "delivery_form_signal"),
        ]
    ).lower()
    if "web app" in text or "website" in text:
        return "web_app"
    if "browser extension" in text:
        return "browser_extension"
    if "mobile app" in text:
        return "mobile_app"
    if "desktop app" in text:
        return "desktop_app"
    if "api" in text or "sdk" in text:
        return "api_sdk"
    if "copilot" in text or "plugin" in text:
        return "copilot_plugin"
    if "workflow agent" in text or "automation" in text:
        return "workflow_agent"
    if "dashboard" in text or "workspace" in text:
        return "dashboard_workspace"
    if "cli" in text or "command line" in text:
        return "cli_tool"
    if "chat assistant" in text or "assistant" in text:
        return "chat_assistant"
    if source_item.get("linked_homepage_url"):
        return "web_app"
    return "unknown"


def _evidence_ref(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_item_id": evidence["source_item_id"],
        "evidence_type": evidence["evidence_type"],
        "source_url": evidence["source_url"],
    }
