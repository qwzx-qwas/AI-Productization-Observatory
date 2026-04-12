"""Rule-first evidence extraction for the Phase1-D baseline."""

from __future__ import annotations

from typing import Any

from src.common.errors import ContractValidationError
from src.common.files import utc_now_iso

MODULE_NAME = "evidence_extractor"
PARSER_OR_MODEL_VERSION = "evidence_extractor_v1"

_EVIDENCE_SCHEMA = {
    "required": {
        "source_item_id",
        "evidence_type",
        "snippet",
        "source_url",
        "parser_or_model_version",
        "extracted_at",
    }
}


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_phase1_d_baseline",
        "run_unit": "per_source_item",
        "version_dependency": PARSER_OR_MODEL_VERSION,
    }


def extract_evidence(
    source_item: dict[str, Any],
    *,
    product_id: str | None = None,
    parser_or_model_version: str = PARSER_OR_MODEL_VERSION,
    extracted_at: str | None = None,
) -> list[dict[str, Any]]:
    timestamp = extracted_at or utc_now_iso()
    source_item_id = source_item.get("source_item_id") or source_item["external_id"]
    source_url = source_item.get("canonical_url") or source_item.get("linked_homepage_url") or source_item.get("linked_repo_url")
    if not source_url:
        raise ContractValidationError("Evidence extraction requires a traceable source_url")

    evidence: list[dict[str, Any]] = []
    text_chunks = _text_chunks(source_item)

    for chunk in text_chunks:
        lower = chunk.lower()
        evidence.extend(
            item
            for item in (
                _build_evidence(source_item_id, product_id, "build_tool_claim", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(token in lower for token in ("built with", "powered by", "using gpt", "using claude", "llm workflow"))
                else None,
                _build_evidence(source_item_id, product_id, "prompt_demo", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(token in lower for token in ("prompt", "workflow", "demo"))
                else None,
                _build_evidence(source_item_id, product_id, "build_speed_claim", chunk, source_url, "medium", parser_or_model_version, timestamp)
                if any(token in lower for token in ("weekend", "days to build", "ship fast", "launched in"))
                else None,
                _build_evidence(source_item_id, product_id, "pricing_page", chunk, source_url, "high", parser_or_model_version, timestamp)
                if "pricing" in lower
                else None,
                _build_evidence(source_item_id, product_id, "paid_plan_claim", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(token in lower for token in ("paid", "subscription", "pro plan", "$"))
                else None,
                _build_evidence(source_item_id, product_id, "testimonial", chunk, source_url, "medium", parser_or_model_version, timestamp)
                if any(token in lower for token in ("loved by", "used by", "trusted by", "customers"))
                else None,
                _build_evidence(source_item_id, product_id, "target_user_claim", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(
                    token in lower
                    for token in (
                        "developer",
                        "engineer",
                        "marketer",
                        "support team",
                        "sales team",
                        "researcher",
                        "founder",
                        "analyst",
                    )
                )
                else None,
                _build_evidence(source_item_id, product_id, "delivery_form_signal", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(
                    token in lower
                    for token in (
                        "web app",
                        "chat assistant",
                        "browser extension",
                        "api",
                        "sdk",
                        "copilot",
                        "dashboard",
                        "workflow agent",
                        "cli",
                    )
                )
                else None,
                _build_evidence(source_item_id, product_id, "job_statement", chunk, source_url, "high", parser_or_model_version, timestamp)
                if any(
                    token in lower
                    for token in (
                        "help",
                        "answer",
                        "search",
                        "draft",
                        "write",
                        "automate",
                        "route",
                        "generate",
                        "summarize",
                        "debug",
                        "test",
                    )
                )
                else None,
                _build_evidence(source_item_id, product_id, "unclear_description_signal", chunk, source_url, "low", parser_or_model_version, timestamp)
                if any(token in lower for token in ("ai assistant for everyone", "general ai assistant", "all-in-one ai"))
                else None,
            )
            if item is not None
        )

    if not evidence and source_item.get("current_summary"):
        evidence.append(
            _build_evidence(
                source_item_id,
                product_id,
                "unclear_description_signal",
                source_item["current_summary"],
                source_url,
                "low",
                parser_or_model_version,
                timestamp,
            )
        )

    deduped = _dedupe_evidence(evidence)
    for item in deduped:
        _validate_evidence(item)
    return deduped


def _text_chunks(source_item: dict[str, Any]) -> list[str]:
    chunks = [
        source_item.get("title"),
        source_item.get("current_summary"),
        source_item.get("raw_text_excerpt"),
    ]
    if source_item.get("linked_homepage_url"):
        chunks.append(f"Homepage: {source_item['linked_homepage_url']}")
    if source_item.get("linked_repo_url"):
        chunks.append(f"Repo: {source_item['linked_repo_url']}")
    return [chunk.strip() for chunk in chunks if isinstance(chunk, str) and chunk.strip()]


def _build_evidence(
    source_item_id: str,
    product_id: str | None,
    evidence_type: str,
    snippet: str,
    source_url: str,
    evidence_strength: str,
    parser_or_model_version: str,
    extracted_at: str,
) -> dict[str, Any]:
    return {
        "source_item_id": source_item_id,
        "product_id": product_id,
        "evidence_type": evidence_type,
        "snippet": snippet[:500],
        "source_url": source_url,
        "evidence_strength": evidence_strength,
        "parser_or_model_version": parser_or_model_version,
        "extracted_at": extracted_at,
    }


def _dedupe_evidence(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in evidence:
        key = (item["evidence_type"], item["snippet"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _validate_evidence(evidence: dict[str, Any]) -> None:
    missing = [field for field in _EVIDENCE_SCHEMA["required"] if field not in evidence]
    if missing:
        raise ContractValidationError(f"Evidence missing required fields: {', '.join(sorted(missing))}")
    if not evidence["snippet"] or not evidence["source_url"]:
        raise ContractValidationError("Evidence requires non-empty snippet and source_url")
