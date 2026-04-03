"""Structured LLM-assisted first-pass review for candidate staging.

The controller owns the durable loop and disk writes. This module only turns a
single candidate review card into one constrained review decision that can be
mapped onto the existing human_review_status fields.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.candidate_prescreen.relay import RelayConfig, clean_raw_evidence_excerpt, post_json_to_relay
from src.common.errors import ProcessingError
from src.common.files import load_json

DEFAULT_REVIEW_PROMPT_VERSION = "candidate_first_pass_reviewer_v1"
DEFAULT_REVIEW_ROUTING_VERSION = "route_candidate_first_pass_reviewer_v1"
DEFAULT_REVIEW_CLIENT_VERSION = "relay_candidate_first_pass_reviewer_v1"
DEFAULT_REVIEW_TRANSPORT = "http_json_relay"
REVIEW_PAYLOAD_BUILDER_VERSION = "candidate_first_pass_review_payload_v1"
ALLOWED_REVIEW_STATUSES = {
    "approved_for_staging",
    "on_hold",
    "rejected_after_human_review",
    "pending_first_pass",
}
ALLOWED_EVIDENCE_SUFFICIENCY = {"sufficient", "borderline", "insufficient"}


@dataclass(frozen=True)
class CandidateReviewDecision:
    suggested_review_status: str
    rationale: str
    evidence_sufficiency: str
    boundary_notes: list[str]
    channel_metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def review_runtime_defaults() -> dict[str, str]:
    return {
        "prompt_version": os.environ.get("APO_CANDIDATE_REVIEW_PROMPT_VERSION", DEFAULT_REVIEW_PROMPT_VERSION),
        "routing_version": os.environ.get("APO_CANDIDATE_REVIEW_ROUTING_VERSION", DEFAULT_REVIEW_ROUTING_VERSION),
        "relay_client_version": os.environ.get("APO_CANDIDATE_REVIEW_CLIENT_VERSION", DEFAULT_REVIEW_CLIENT_VERSION),
        "relay_transport": os.environ.get("APO_CANDIDATE_REVIEW_TRANSPORT", DEFAULT_REVIEW_TRANSPORT),
    }


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _candidate_review_prompt_contract() -> dict[str, Any]:
    return {
        "role": "candidate_first_pass_reviewer",
        "objective": "Return one constrained first-pass review decision for staging eligibility.",
        "operating_rules": [
            "Return exactly one JSON object with no markdown fences or extra prose.",
            "Only use suggested_review_status values from: approved_for_staging, on_hold, rejected_after_human_review, pending_first_pass.",
            "approved_for_staging only when there is a clear end-user product signal and sufficient evidence for staging.",
            "on_hold only when the internal-tooling boundary is genuinely unclear.",
            "rejected_after_human_review only when the candidate is outside observatory scope.",
            "pending_first_pass when evidence is too thin to safely approve, hold, or reject.",
            "Do not claim that any file write, handoff, or formal gold-set update already happened.",
            "Do not invent evidence beyond the provided summary, excerpt, and prescreen review card.",
        ],
        "required_outputs": [
            "suggested_review_status",
            "rationale",
            "evidence_sufficiency",
            "boundary_notes",
        ],
        "shape_constraints": {
            "boundary_notes": "0 to 3 concise strings",
            "rationale": "one concise sentence grounded in provided evidence",
            "evidence_sufficiency": "one of sufficient, borderline, insufficient",
        },
    }


def _build_review_input(candidate_record: dict[str, Any]) -> dict[str, Any]:
    llm_prescreen = candidate_record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        llm_prescreen = {}
    return {
        "candidate_id": _normalize_text(candidate_record.get("candidate_id")),
        "source": _normalize_text(candidate_record.get("source")),
        "source_window": _normalize_text(candidate_record.get("source_window")),
        "external_id": _normalize_text(candidate_record.get("external_id")),
        "canonical_url": _normalize_text(candidate_record.get("canonical_url")),
        "title": _normalize_text(candidate_record.get("title")),
        "summary": _normalize_text(candidate_record.get("summary")),
        "raw_evidence_excerpt": clean_raw_evidence_excerpt(candidate_record.get("raw_evidence_excerpt")),
        "query_family": _normalize_text(candidate_record.get("query_family")),
        "query_slice_id": _normalize_text(candidate_record.get("query_slice_id")),
        "selection_rule_version": _normalize_text(candidate_record.get("selection_rule_version")),
        "current_human_review_status": _normalize_text(candidate_record.get("human_review_status")),
        "llm_prescreen": {
            "status": llm_prescreen.get("status"),
            "decision_snapshot": _normalize_text(llm_prescreen.get("decision_snapshot")),
            "scope_boundary_note": _normalize_text(llm_prescreen.get("scope_boundary_note")),
            "reason": _normalize_text(llm_prescreen.get("reason")),
            "review_focus_points": [
                item.strip()
                for item in llm_prescreen.get("review_focus_points", [])
                if isinstance(item, str) and item.strip()
            ],
            "uncertainty_points": [
                item.strip()
                for item in llm_prescreen.get("uncertainty_points", [])
                if isinstance(item, str) and item.strip()
            ],
        },
    }


def _normalize_status(value: Any, *, evidence_sufficiency: str) -> str:
    text = _normalize_text(value).lower()
    if text in ALLOWED_REVIEW_STATUSES:
        return text
    if "approved" in text or "approve" in text:
        return "approved_for_staging"
    if "reject" in text or "outside observatory" in text or "out of scope" in text:
        return "rejected_after_human_review"
    if "hold" in text or "boundary" in text or "internal tooling" in text:
        return "on_hold"
    if "pending" in text or evidence_sufficiency == "insufficient":
        return "pending_first_pass"
    return "pending_first_pass"


def _normalize_evidence_sufficiency(value: Any) -> str:
    text = _normalize_text(value).lower()
    if text in ALLOWED_EVIDENCE_SUFFICIENCY:
        return text
    if "sufficient" in text or "strong" in text or "clear" in text:
        return "sufficient"
    if "border" in text or "mixed" in text or "partial" in text:
        return "borderline"
    return "insufficient"


def _normalize_boundary_notes(value: Any) -> list[str]:
    if isinstance(value, list):
        notes = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    elif isinstance(value, str) and value.strip():
        notes = [value.strip()]
    else:
        notes = []
    return notes[:3]


def _normalize_review_result(result: dict[str, Any], *, channel_metadata: dict[str, Any]) -> CandidateReviewDecision:
    evidence_sufficiency = _normalize_evidence_sufficiency(result.get("evidence_sufficiency"))
    rationale = _normalize_text(result.get("rationale"))
    boundary_notes = _normalize_boundary_notes(result.get("boundary_notes"))
    if not rationale:
        rationale = boundary_notes[0] if boundary_notes else "Insufficient structured rationale returned by reviewer."
    return CandidateReviewDecision(
        suggested_review_status=_normalize_status(
            result.get("suggested_review_status") or result.get("human_review_status"),
            evidence_sufficiency=evidence_sufficiency,
        ),
        rationale=rationale,
        evidence_sufficiency=evidence_sufficiency,
        boundary_notes=boundary_notes,
        channel_metadata=channel_metadata,
    )


def _openai_request_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return normalized


def _extract_result_object(body: dict[str, Any], *, api_style: str) -> dict[str, Any]:
    if api_style == "openai_compatible":
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProcessingError("schema_drift", "OpenAI-compatible response is missing choices[]")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ProcessingError("schema_drift", "OpenAI-compatible choices[0] must be an object")
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ProcessingError("schema_drift", "OpenAI-compatible choices[0].message must be an object")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProcessingError("schema_drift", "OpenAI-compatible response must provide message.content text")
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ProcessingError("parse_failure", "OpenAI-compatible response content must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ProcessingError("schema_drift", "OpenAI-compatible response content must decode to an object")
        return parsed

    result = None
    if isinstance(body.get("result"), dict):
        result = body["result"]
    elif isinstance(body.get("output"), dict):
        result = body["output"]
    if not isinstance(result, dict):
        raise ProcessingError("schema_drift", "Relay response must provide a result object")
    return result


def _build_openai_payload(
    *,
    model: str,
    prompt_version: str,
    routing_version: str,
    review_input: dict[str, Any],
    message_content_style: str,
) -> dict[str, Any]:
    contract = _candidate_review_prompt_contract()
    system_lines = [
        "You are the AI Productization Observatory candidate first-pass reviewer.",
        "Return exactly one JSON object with no markdown fences or extra prose.",
        f"Objective: {contract['objective']}",
        "Operating rules:",
    ]
    system_lines.extend(f"- {rule}" for rule in contract["operating_rules"])
    system_lines.append(f"Required outputs: {', '.join(contract['required_outputs'])}")
    system_lines.append("Shape constraints:")
    for key, value in contract["shape_constraints"].items():
        system_lines.append(f"- {key}: {value}")
    user_payload = {
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "payload_builder_version": REVIEW_PAYLOAD_BUILDER_VERSION,
        "candidate_review_input": review_input,
    }
    if message_content_style == "parts_list":
        system_content: str | list[dict[str, str]] = [{"type": "text", "text": "\n".join(system_lines)}]
        user_content: str | list[dict[str, str]] = [{"type": "text", "text": json.dumps(user_payload, ensure_ascii=True)}]
    else:
        system_content = "\n".join(system_lines)
        user_content = json.dumps(user_payload, ensure_ascii=True)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }


def _build_relay_payload(
    *,
    model: str,
    prompt_version: str,
    routing_version: str,
    review_input: dict[str, Any],
) -> dict[str, Any]:
    return {
        "task": "candidate_first_pass_review",
        "model": model,
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "payload_builder_version": REVIEW_PAYLOAD_BUILDER_VERSION,
        "input": review_input,
        "prompt_contract": _candidate_review_prompt_contract(),
    }


def review_candidate_with_llm(
    candidate_record: dict[str, Any],
    *,
    fixture_path: Path | None,
    timeout_seconds: int,
    max_retries: int,
) -> CandidateReviewDecision:
    review_input = _build_review_input(candidate_record)
    runtime_defaults = review_runtime_defaults()
    fixture_key = review_input["candidate_id"]
    if fixture_path is not None:
        fixture = load_json(fixture_path)
        responses = fixture.get("responses") if isinstance(fixture, dict) else None
        if not isinstance(responses, dict) or fixture_key not in responses:
            raise ProcessingError("parse_failure", f"Review fixture is missing response for {fixture_key}")
        response = responses[fixture_key]
        if not isinstance(response, dict):
            raise ProcessingError("parse_failure", f"Review fixture response for {fixture_key} must be an object")
        return _normalize_review_result(
            response,
            channel_metadata={
                "prompt_version": fixture.get("prompt_version", runtime_defaults["prompt_version"]),
                "routing_version": fixture.get("routing_version", runtime_defaults["routing_version"]),
                "relay_client_version": fixture.get("relay_client_version", runtime_defaults["relay_client_version"]),
                "model": fixture.get("model", "fixture-reviewer"),
                "transport": runtime_defaults["relay_transport"],
                "request_id": None,
            },
        )

    relay_config = RelayConfig.from_env(timeout_seconds, runtime_defaults["relay_client_version"])
    if relay_config.api_style == "openai_compatible":
        request_url = _openai_request_url(relay_config.base_url)
        payload = _build_openai_payload(
            model=relay_config.model,
            prompt_version=runtime_defaults["prompt_version"],
            routing_version=runtime_defaults["routing_version"],
            review_input=review_input,
            message_content_style=relay_config.message_content_style,
        )
    else:
        request_url = relay_config.base_url
        payload = _build_relay_payload(
            model=relay_config.model,
            prompt_version=runtime_defaults["prompt_version"],
            routing_version=runtime_defaults["routing_version"],
            review_input=review_input,
        )

    last_error: ProcessingError | None = None
    for _attempt in range(max_retries + 1):
        try:
            body, request_id = post_json_to_relay(
                request_url=request_url,
                payload=payload,
                relay_config=relay_config,
                request_label="Reviewer relay request",
            )
        except ProcessingError as exc:
            last_error = exc
            continue

        result = _extract_result_object(body, api_style=relay_config.api_style)
        return _normalize_review_result(
            result,
            channel_metadata={
                "prompt_version": runtime_defaults["prompt_version"],
                "routing_version": runtime_defaults["routing_version"],
                "relay_client_version": relay_config.client_version,
                "model": relay_config.model,
                "transport": runtime_defaults["relay_transport"],
                "request_id": request_id,
            },
        )

    if last_error is None:
        raise ProcessingError("dependency_unavailable", "Reviewer relay failed before any response was received")
    raise last_error
