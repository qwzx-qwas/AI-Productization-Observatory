"""Relay-LLM adapter for candidate prescreening."""

from __future__ import annotations

import html
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from socket import timeout as SocketTimeout
from typing import Any

from src.candidate_prescreen.review_card import normalize_llm_result
from src.common.config import require_environment_variable
from src.common.errors import ConfigError, ProcessingError
from src.common.files import load_json

PAYLOAD_BUILDER_VERSION = "candidate_prescreen_payload_v1"
README_EXCERPT_MAX_CHARS = 8000
RELAY_API_STYLE_OPTIONS = {"relay_json", "openai_compatible"}
RELAY_AUTH_STYLE_OPTIONS = {"bearer", "raw"}
RELAY_MESSAGE_CONTENT_STYLE_OPTIONS = {"string", "parts_list"}
_BADGE_MARKERS = (
    "img.shields.io",
    "shields.io",
    "readme-typing-svg",
    "visitor badge",
    "badge.svg",
)


@dataclass(frozen=True)
class RelayConfig:
    base_url: str
    token: str
    model: str
    timeout_seconds: int
    client_version: str
    api_style: str
    auth_style: str
    message_content_style: str

    @classmethod
    def from_env(cls, default_timeout_seconds: int, default_client_version: str) -> "RelayConfig":
        base_url = require_environment_variable("APO_LLM_RELAY_BASE_URL")
        token = require_environment_variable("APO_LLM_RELAY_TOKEN")
        model = require_environment_variable("APO_LLM_RELAY_MODEL")
        timeout_value = os.environ.get("APO_LLM_RELAY_TIMEOUT_SECONDS")
        timeout_seconds = default_timeout_seconds
        if timeout_value:
            try:
                timeout_seconds = int(timeout_value)
            except ValueError as exc:
                raise ConfigError("APO_LLM_RELAY_TIMEOUT_SECONDS must be an integer") from exc
        client_version = os.environ.get("APO_LLM_RELAY_CLIENT_VERSION", default_client_version)
        api_style = os.environ.get("APO_LLM_RELAY_API_STYLE", "relay_json")
        if api_style not in RELAY_API_STYLE_OPTIONS:
            supported = ", ".join(sorted(RELAY_API_STYLE_OPTIONS))
            raise ConfigError(f"APO_LLM_RELAY_API_STYLE must be one of: {supported}")
        auth_style = os.environ.get("APO_LLM_RELAY_AUTH_STYLE", "bearer")
        if auth_style not in RELAY_AUTH_STYLE_OPTIONS:
            supported = ", ".join(sorted(RELAY_AUTH_STYLE_OPTIONS))
            raise ConfigError(f"APO_LLM_RELAY_AUTH_STYLE must be one of: {supported}")
        message_content_style = os.environ.get("APO_LLM_RELAY_MESSAGE_CONTENT_STYLE", "string")
        if message_content_style not in RELAY_MESSAGE_CONTENT_STYLE_OPTIONS:
            supported = ", ".join(sorted(RELAY_MESSAGE_CONTENT_STYLE_OPTIONS))
            raise ConfigError(f"APO_LLM_RELAY_MESSAGE_CONTENT_STYLE must be one of: {supported}")
        return cls(
            base_url=base_url,
            token=token,
            model=model,
            timeout_seconds=timeout_seconds,
            client_version=client_version,
            api_style=api_style,
            auth_style=auth_style,
            message_content_style=message_content_style,
        )


def _normalize_prompt_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _clean_excerpt_line(raw_line: str) -> str:
    line = html.unescape(raw_line.strip())
    lower_line = line.lower()
    if not line:
        return ""
    if line.startswith("<!--") or line.endswith("-->"):
        return ""
    if any(marker in lower_line for marker in _BADGE_MARKERS):
        return ""
    if line.startswith("![") or line.startswith("[!["):
        return ""
    line = re.sub(r"<[^>]+>", " ", line)
    line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", line)
    line = re.sub(r"\s+", " ", line).strip()
    if not line:
        return ""
    if re.fullmatch(r"https?://\S+", line):
        return ""
    return line


def _clean_raw_evidence_excerpt(value: Any) -> str:
    text = _normalize_prompt_text(value)
    if not text:
        return ""
    paragraphs: list[str] = []
    current_lines: list[str] = []
    in_code_block = False
    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if current_lines:
                paragraph = " ".join(current_lines).strip()
                if paragraph:
                    paragraphs.append(paragraph)
                current_lines = []
            continue
        if in_code_block:
            continue
        cleaned_line = _clean_excerpt_line(raw_line)
        if not cleaned_line:
            if current_lines:
                paragraph = " ".join(current_lines).strip()
                if paragraph:
                    paragraphs.append(paragraph)
                current_lines = []
            continue
        if cleaned_line.startswith("#"):
            cleaned_line = cleaned_line.lstrip("#").strip()
        current_lines.append(cleaned_line)
    if current_lines:
        paragraph = " ".join(current_lines).strip()
        if paragraph:
            paragraphs.append(paragraph)
    deduped: list[str] = []
    for paragraph in paragraphs:
        if not deduped or deduped[-1] != paragraph:
            deduped.append(paragraph)
    if not deduped:
        fallback = re.sub(r"\s+", " ", text)
        return fallback[:README_EXCERPT_MAX_CHARS].strip()
    excerpt_parts: list[str] = []
    current_length = 0
    for paragraph in deduped:
        candidate_length = len(paragraph) if not excerpt_parts else current_length + 2 + len(paragraph)
        if candidate_length > README_EXCERPT_MAX_CHARS:
            break
        excerpt_parts.append(paragraph)
        current_length = candidate_length
    if excerpt_parts:
        return "\n\n".join(excerpt_parts)
    return deduped[0][:README_EXCERPT_MAX_CHARS].strip()


def _build_relay_input(candidate_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": _normalize_prompt_text(candidate_input.get("source")),
        "source_window": _normalize_prompt_text(candidate_input.get("source_window")),
        "external_id": _normalize_prompt_text(candidate_input.get("external_id")),
        "canonical_url": _normalize_prompt_text(candidate_input.get("canonical_url")),
        "title": _normalize_prompt_text(candidate_input.get("title")),
        "summary": _normalize_prompt_text(candidate_input.get("summary")),
        "raw_evidence_excerpt": _clean_raw_evidence_excerpt(candidate_input.get("raw_evidence_excerpt")),
        "query_family": _normalize_prompt_text(candidate_input.get("query_family")),
        "query_slice_id": _normalize_prompt_text(candidate_input.get("query_slice_id")),
        "selection_rule_version": _normalize_prompt_text(candidate_input.get("selection_rule_version")),
        "time_field": _normalize_prompt_text(candidate_input.get("time_field")),
    }


def _openai_request_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return normalized


def _build_openai_compatible_payload(
    *,
    model: str,
    prompt_version: str,
    routing_version: str,
    candidate_input: dict[str, Any],
    prompt_contract: dict[str, Any] | None,
    message_content_style: str,
) -> dict[str, Any]:
    system_parts = [
        "You are the Candidate Prescreener for AI Productization Observatory.",
        "Return exactly one JSON object with no markdown fences or extra prose.",
        "Your output is a human-first prescreen review card rather than a final adjudication.",
    ]
    if isinstance(prompt_contract, dict) and prompt_contract:
        objective = prompt_contract.get("objective")
        if isinstance(objective, str) and objective.strip():
            system_parts.append(f"Objective: {objective.strip()}")
        operating_rules = prompt_contract.get("operating_rules")
        if isinstance(operating_rules, list) and operating_rules:
            system_parts.append("Operating rules:")
            for rule in operating_rules:
                if isinstance(rule, str) and rule.strip():
                    system_parts.append(f"- {rule.strip()}")
        required_outputs = prompt_contract.get("required_outputs")
        if isinstance(required_outputs, list) and required_outputs:
            rendered_outputs = [value.strip() for value in required_outputs if isinstance(value, str) and value.strip()]
            if rendered_outputs:
                system_parts.append(f"Required outputs: {', '.join(rendered_outputs)}")
        shape_constraints = prompt_contract.get("shape_constraints")
        if isinstance(shape_constraints, dict) and shape_constraints:
            system_parts.append("Shape constraints:")
            for key, value in shape_constraints.items():
                if isinstance(key, str) and isinstance(value, str) and key.strip() and value.strip():
                    system_parts.append(f"- {key.strip()}: {value.strip()}")
    user_payload = {
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "payload_builder_version": PAYLOAD_BUILDER_VERSION,
        "candidate_input": candidate_input,
    }
    if message_content_style == "parts_list":
        system_content: str | list[dict[str, str]] = [{"type": "text", "text": "\n".join(system_parts)}]
        user_content: str | list[dict[str, str]] = [{"type": "text", "text": json.dumps(user_payload, ensure_ascii=True)}]
    else:
        system_content = "\n".join(system_parts)
        user_content = json.dumps(user_payload, ensure_ascii=True)
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0,
    }


def _parse_openai_message_content(body: dict[str, Any]) -> dict[str, Any]:
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


def _request_payload(
    *,
    relay_config: RelayConfig,
    prompt_version: str,
    routing_version: str,
    candidate_input: dict[str, Any],
    prompt_contract: dict[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    cleaned_input = _build_relay_input(candidate_input)
    if relay_config.api_style == "openai_compatible":
        return (
            _openai_request_url(relay_config.base_url),
            _build_openai_compatible_payload(
                model=relay_config.model,
                prompt_version=prompt_version,
                routing_version=routing_version,
                candidate_input=cleaned_input,
                prompt_contract=prompt_contract,
                message_content_style=relay_config.message_content_style,
            ),
        )
    payload = {
        "task": "candidate_prescreen",
        "model": relay_config.model,
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "payload_builder_version": PAYLOAD_BUILDER_VERSION,
        "input": cleaned_input,
    }
    if isinstance(prompt_contract, dict) and prompt_contract:
        payload["prompt_contract"] = prompt_contract
    return relay_config.base_url, payload


def _authorization_header(relay_config: RelayConfig) -> str:
    if relay_config.auth_style == "raw":
        return relay_config.token
    return f"Bearer {relay_config.token}"


def _extract_result_object(body: dict[str, Any], *, api_style: str) -> dict[str, Any]:
    if api_style == "openai_compatible":
        return _parse_openai_message_content(body)
    result = None
    if isinstance(body.get("result"), dict):
        result = body["result"]
    elif isinstance(body.get("output"), dict):
        result = body["output"]
    if not isinstance(result, dict):
        raise ProcessingError("schema_drift", "Relay response must provide a result object")
    return result


def screen_candidate(
    candidate_input: dict[str, Any],
    *,
    prompt_version: str,
    routing_version: str,
    relay_transport: str,
    relay_client_version: str,
    prompt_contract: dict[str, Any] | None,
    fixture_path: Path | None,
    timeout_seconds: int,
    max_retries: int,
) -> dict[str, Any]:
    fixture_key = f"{candidate_input['source']}:{candidate_input['external_id']}"
    if fixture_path is not None:
        fixture = load_json(fixture_path)
        responses = fixture.get("responses") if isinstance(fixture, dict) else None
        if not isinstance(responses, dict) or fixture_key not in responses:
            raise ProcessingError("parse_failure", f"LLM prescreen fixture is missing response for {fixture_key}")
        response = responses[fixture_key]
        if not isinstance(response, dict):
            raise ProcessingError("parse_failure", f"LLM prescreen fixture response for {fixture_key} must be an object")
        normalized = normalize_llm_result(response)
        normalized["channel_metadata"] = {
            "prompt_version": fixture.get("prompt_version", prompt_version),
            "routing_version": fixture.get("routing_version", routing_version),
            "relay_client_version": fixture.get("relay_client_version", relay_client_version),
            "model": fixture.get("model", "fixture-relay"),
            "transport": relay_transport,
            "request_id": None,
        }
        return normalized

    relay_config = RelayConfig.from_env(timeout_seconds, relay_client_version)
    request_url, payload = _request_payload(
        relay_config=relay_config,
        prompt_version=prompt_version,
        routing_version=routing_version,
        candidate_input=candidate_input,
        prompt_contract=prompt_contract,
    )
    last_error: ProcessingError | None = None
    for _attempt in range(max_retries + 1):
        request = urllib.request.Request(
            request_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": _authorization_header(relay_config),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=relay_config.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                raw_body = response.read().decode("utf-8")
                request_id = response.headers.get("X-Request-Id")
        except urllib.error.HTTPError as exc:
            error_type = "api_429" if exc.code == 429 else "dependency_unavailable"
            last_error = ProcessingError(error_type, f"Relay returned HTTP {exc.code}")
            continue
        except urllib.error.URLError as exc:
            last_error = ProcessingError("network_error", f"Relay network error: {exc.reason}")
            continue
        except SocketTimeout as exc:
            last_error = ProcessingError("provider_timeout", "Relay timed out")
            continue
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ProcessingError("parse_failure", "Relay returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise ProcessingError("schema_drift", "Relay response body must be an object")
        result = _extract_result_object(body, api_style=relay_config.api_style)
        normalized = normalize_llm_result(result)
        normalized["channel_metadata"] = {
            "prompt_version": prompt_version,
            "routing_version": routing_version,
            "relay_client_version": relay_config.client_version,
            "model": relay_config.model,
            "transport": relay_transport,
            "request_id": request_id,
        }
        return normalized
    if last_error is None:
        raise ProcessingError("dependency_unavailable", "Relay request failed before any response was received")
    raise last_error
