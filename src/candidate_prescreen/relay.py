"""Relay-LLM adapter for candidate prescreening."""

from __future__ import annotations

import html
import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from socket import timeout as SocketTimeout
from time import sleep
from typing import Any, Callable

from src.candidate_prescreen.review_card import normalize_llm_result, validate_normalized_llm_prescreen
from src.candidate_prescreen.url_utils import normalize_candidate_url
from src.common.config import require_environment_variable
from src.common.constants import RETRY_POLICY
from src.common.errors import ConfigError, ContractValidationError, ProcessingError
from src.common.files import load_json
from src.common.logging_utils import get_logger
from src.common.request_timing import wait_for_request_interval

PAYLOAD_BUILDER_VERSION = "candidate_prescreen_payload_v1"
README_EXCERPT_MAX_CHARS = 8000
RELAY_API_STYLE_OPTIONS = {"relay_json", "openai_compatible"}
RELAY_AUTH_STYLE_OPTIONS = {"bearer", "raw"}
RELAY_MESSAGE_CONTENT_STYLE_OPTIONS = {"string", "parts_list"}
OUTCOME_SUCCEEDED = "succeeded"
OUTCOME_FAILED = "failed"
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


@dataclass(frozen=True)
class RelayOutcomeError(Exception):
    mapped_error_type: str
    failure_code: str
    failure_message: str
    transport_status: str = OUTCOME_SUCCEEDED
    provider_response_status: str = OUTCOME_FAILED
    content_status: str = OUTCOME_FAILED
    schema_status: str = OUTCOME_FAILED
    business_status: str = OUTCOME_FAILED


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


def clean_raw_evidence_excerpt(value: Any) -> str:
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
        "canonical_url": normalize_candidate_url(candidate_input.get("canonical_url"), field_name="candidate_input.canonical_url"),
        "title": _normalize_prompt_text(candidate_input.get("title")),
        "summary": _normalize_prompt_text(candidate_input.get("summary")),
        "raw_evidence_excerpt": clean_raw_evidence_excerpt(candidate_input.get("raw_evidence_excerpt")),
        "query_family": _normalize_prompt_text(candidate_input.get("query_family")),
        "query_slice_id": _normalize_prompt_text(candidate_input.get("query_slice_id")),
        "selection_rule_version": _normalize_prompt_text(candidate_input.get("selection_rule_version")),
        "time_field": _normalize_prompt_text(candidate_input.get("time_field")),
    }


def build_relay_candidate_input(candidate_input: dict[str, Any]) -> dict[str, Any]:
    return _build_relay_input(candidate_input)


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
        raise RelayOutcomeError(
            mapped_error_type="schema_drift",
            failure_code="provider_schema_drift",
            failure_message="OpenAI-compatible response is missing choices[]",
        )
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise RelayOutcomeError(
            mapped_error_type="schema_drift",
            failure_code="provider_schema_drift",
            failure_message="OpenAI-compatible choices[0] must be an object",
        )
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise RelayOutcomeError(
            mapped_error_type="schema_drift",
            failure_code="provider_schema_drift",
            failure_message="OpenAI-compatible choices[0].message must be an object",
        )
    content = message.get("content")
    cleaned = _openai_message_content_text(content)
    if cleaned is None:
        raise RelayOutcomeError(
            mapped_error_type="dependency_unavailable",
            failure_code="provider_empty_completion",
            failure_message="OpenAI-compatible response must provide non-empty message.content text",
            provider_response_status=OUTCOME_SUCCEEDED,
        )
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RelayOutcomeError(
            mapped_error_type="parse_failure",
            failure_code="parse_failure",
            failure_message="OpenAI-compatible response content must be valid JSON",
            provider_response_status=OUTCOME_SUCCEEDED,
        ) from exc
    if not isinstance(parsed, dict):
        raise RelayOutcomeError(
            mapped_error_type="schema_drift",
            failure_code="provider_schema_drift",
            failure_message="OpenAI-compatible response content must decode to an object",
            provider_response_status=OUTCOME_SUCCEEDED,
        )
    return parsed


def _openai_message_content_text(content: Any) -> str | None:
    if isinstance(content, str):
        cleaned = content.strip()
        return cleaned or None
    if not isinstance(content, list):
        return None
    text_parts: list[str] = []
    for part in content:
        text = _openai_message_content_part_text(part)
        if text is not None:
            text_parts.append(text)
    if not text_parts:
        return None
    return "\n".join(text_parts).strip() or None


def _openai_message_content_part_text(part: Any) -> str | None:
    if isinstance(part, str):
        cleaned = part.strip()
        return cleaned or None
    if not isinstance(part, dict):
        return None
    direct_text = part.get("text")
    if isinstance(direct_text, str):
        cleaned = direct_text.strip()
        return cleaned or None
    if isinstance(direct_text, dict):
        for key in ("value", "text"):
            nested = direct_text.get(key)
            if isinstance(nested, str):
                cleaned = nested.strip()
                if cleaned:
                    return cleaned
    value = part.get("value")
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


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


def _response_http_status(response: Any) -> int | None:
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    getcode = getattr(response, "getcode", None)
    if callable(getcode):
        try:
            code = getcode()
        except Exception:
            return None
        if isinstance(code, int):
            return code
    return None


def _screen_outcome(
    *,
    transport_status: str,
    provider_response_status: str,
    content_status: str,
    schema_status: str,
    business_status: str,
    request_id: str | None,
    http_status: int | None,
    mapped_error_type: str | None,
    failure_code: str | None,
    failure_message: str | None,
    normalized_result: dict[str, Any] | None,
    request_url: str | None,
    response_id: str | None,
    provider_usage: dict[str, int] | None,
    api_style: str | None,
    model: str | None,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "transport_status": transport_status,
        "provider_response_status": provider_response_status,
        "content_status": content_status,
        "schema_status": schema_status,
        "business_status": business_status,
        "request_id": request_id,
        "http_status": http_status,
        "mapped_error_type": mapped_error_type,
        "failure_code": failure_code,
        "failure_message": failure_message,
        "normalized_result": normalized_result,
        "request_url": request_url,
        "response_id": response_id,
        "provider_usage": provider_usage,
        "api_style": api_style,
        "model": model,
        "attempt_count": len(attempts),
        "attempts": attempts,
    }


def _successful_screen_outcome(
    *,
    request_id: str | None,
    http_status: int | None,
    normalized_result: dict[str, Any],
    request_url: str,
    response_id: str | None,
    provider_usage: dict[str, int] | None,
    api_style: str,
    model: str,
    attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    return _screen_outcome(
        transport_status=OUTCOME_SUCCEEDED,
        provider_response_status=OUTCOME_SUCCEEDED,
        content_status=OUTCOME_SUCCEEDED,
        schema_status=OUTCOME_SUCCEEDED,
        business_status=OUTCOME_SUCCEEDED,
        request_id=request_id,
        http_status=http_status,
        mapped_error_type=None,
        failure_code=None,
        failure_message=None,
        normalized_result=normalized_result,
        request_url=request_url,
        response_id=response_id,
        provider_usage=provider_usage,
        api_style=api_style,
        model=model,
        attempts=attempts,
    )


def _failed_screen_outcome(
    *,
    request_id: str | None,
    http_status: int | None,
    mapped_error_type: str,
    failure_code: str,
    failure_message: str,
    request_url: str | None,
    response_id: str | None,
    provider_usage: dict[str, int] | None,
    api_style: str | None,
    model: str | None,
    attempts: list[dict[str, Any]],
    transport_status: str = OUTCOME_SUCCEEDED,
    provider_response_status: str = OUTCOME_FAILED,
    content_status: str = OUTCOME_FAILED,
    schema_status: str = OUTCOME_FAILED,
    business_status: str = OUTCOME_FAILED,
) -> dict[str, Any]:
    return _screen_outcome(
        transport_status=transport_status,
        provider_response_status=provider_response_status,
        content_status=content_status,
        schema_status=schema_status,
        business_status=business_status,
        request_id=request_id,
        http_status=http_status,
        mapped_error_type=mapped_error_type,
        failure_code=failure_code,
        failure_message=failure_message,
        normalized_result=None,
        request_url=request_url,
        response_id=response_id,
        provider_usage=provider_usage,
        api_style=api_style,
        model=model,
        attempts=attempts,
    )


def screen_candidate_outcome_succeeded(outcome: dict[str, Any]) -> bool:
    return all(
        outcome.get(field_name) == OUTCOME_SUCCEEDED
        for field_name in (
            "transport_status",
            "provider_response_status",
            "content_status",
            "schema_status",
            "business_status",
        )
    )


def screen_candidate_outcome_to_error(outcome: dict[str, Any]) -> ProcessingError:
    error_type = str(outcome.get("mapped_error_type") or "dependency_unavailable")
    message = str(outcome.get("failure_message") or outcome.get("failure_code") or "candidate prescreen relay failed")
    return ProcessingError(error_type, message)


def relay_preflight(
    *,
    default_timeout_seconds: int,
    default_client_version: str,
) -> dict[str, Any]:
    """Validate that the configured relay endpoint is structurally usable before a long fill run."""

    relay_config = RelayConfig.from_env(default_timeout_seconds, default_client_version)
    request_url = (
        _openai_request_url(relay_config.base_url)
        if relay_config.api_style == "openai_compatible"
        else relay_config.base_url.rstrip("/")
    )
    parsed = urllib.parse.urlparse(request_url)
    if not parsed.scheme or not parsed.hostname:
        raise ConfigError("APO_LLM_RELAY_BASE_URL must include a valid scheme and hostname")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)
    except OSError as exc:
        raise ProcessingError(
            "network_error",
            f"Relay preflight could not resolve {parsed.hostname}:{port}: {exc}",
        ) from exc
    return {
        "request_url": request_url,
        "host": parsed.hostname,
        "port": port,
        "model": relay_config.model,
        "api_style": relay_config.api_style,
        "auth_style": relay_config.auth_style,
        "client_version": relay_config.client_version,
    }


def _normalize_provider_usage(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, int] = {}
    for key, raw_value in value.items():
        if isinstance(raw_value, bool):
            continue
        if isinstance(raw_value, int):
            normalized[str(key)] = raw_value
            continue
        if not isinstance(raw_value, dict):
            continue
        for nested_key, nested_value in raw_value.items():
            if isinstance(nested_value, bool):
                continue
            if isinstance(nested_value, int):
                normalized[f"{key}.{nested_key}"] = nested_value
    return normalized or None


def _extract_provider_audit(body: dict[str, Any], *, api_style: str) -> tuple[str | None, dict[str, int] | None]:
    response_id = body.get("id")
    if not isinstance(response_id, str) or not response_id.strip():
        response_id = body.get("request_id")
    normalized_response_id = response_id.strip() if isinstance(response_id, str) and response_id.strip() else None
    if api_style == "openai_compatible":
        return normalized_response_id, _normalize_provider_usage(body.get("usage"))
    usage = body.get("usage")
    if usage is None and isinstance(body.get("result"), dict):
        usage = body["result"].get("usage")
    return normalized_response_id, _normalize_provider_usage(usage)


def _attempt_event(
    *,
    attempt: int,
    request_url: str,
    api_style: str,
    model: str,
    transport_status: str,
    provider_response_status: str,
    content_status: str,
    schema_status: str,
    business_status: str,
    http_status: int | None,
    request_id: str | None,
    response_id: str | None,
    provider_usage: dict[str, int] | None,
    mapped_error_type: str | None,
    failure_code: str | None,
    failure_message: str | None,
    retry_scheduled: bool,
) -> dict[str, Any]:
    return {
        "attempt": attempt,
        "request_url": request_url,
        "api_style": api_style,
        "model": model,
        "transport_status": transport_status,
        "provider_response_status": provider_response_status,
        "content_status": content_status,
        "schema_status": schema_status,
        "business_status": business_status,
        "http_status": http_status,
        "request_id": request_id,
        "response_id": response_id,
        "provider_usage": provider_usage,
        "mapped_error_type": mapped_error_type,
        "failure_code": failure_code,
        "failure_message": failure_message,
        "retry_scheduled": retry_scheduled,
    }


def _extract_result_object(body: dict[str, Any], *, api_style: str) -> dict[str, Any]:
    if api_style == "openai_compatible":
        return _parse_openai_message_content(body)
    result = None
    if isinstance(body.get("result"), dict):
        result = body["result"]
    elif isinstance(body.get("output"), dict):
        result = body["output"]
    if not isinstance(result, dict):
        raise RelayOutcomeError(
            mapped_error_type="schema_drift",
            failure_code="provider_schema_drift",
            failure_message="Relay response must provide a result object",
        )
    if not result:
        raise RelayOutcomeError(
            mapped_error_type="dependency_unavailable",
            failure_code="provider_empty_completion",
            failure_message="Relay response returned an empty result object",
            provider_response_status=OUTCOME_SUCCEEDED,
        )
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
    request_interval_seconds: int = 0,
    retry_sleep_seconds: int = 0,
    sleep_fn: Callable[[float], None] = sleep,
    run_id: str | None = None,
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
        try:
            validate_normalized_llm_prescreen(normalized)
        except ContractValidationError as exc:
            return _failed_screen_outcome(
                request_id=None,
                http_status=None,
                mapped_error_type="json_schema_validation_failed",
                failure_code="output_schema_validation_failed",
                failure_message=str(exc),
                request_url=str(fixture_path),
                response_id=None,
                provider_usage=None,
                api_style="fixture",
                model=str(normalized["channel_metadata"].get("model") or "fixture-relay"),
                attempts=[],
                transport_status=OUTCOME_SUCCEEDED,
                provider_response_status=OUTCOME_SUCCEEDED,
                content_status=OUTCOME_SUCCEEDED,
            )
        return _successful_screen_outcome(
            request_id=None,
            http_status=None,
            normalized_result=normalized,
            request_url=str(fixture_path),
            response_id=None,
            provider_usage=None,
            api_style="fixture",
            model=str(normalized["channel_metadata"].get("model") or "fixture-relay"),
            attempts=[],
        )

    relay_config = RelayConfig.from_env(timeout_seconds, relay_client_version)
    logger = get_logger(
        "candidate_prescreen_relay",
        source_id=str(candidate_input.get("source_id") or f"src_{candidate_input.get('source', 'unknown')}"),
        task_id="candidate_prescreen_relay",
        resolution_status="running",
        run_id=run_id,
    )
    request_url, payload = _request_payload(
        relay_config=relay_config,
        prompt_version=prompt_version,
        routing_version=routing_version,
        candidate_input=candidate_input,
        prompt_contract=prompt_contract,
    )
    attempts: list[dict[str, Any]] = []

    def _wait_before_retry(error: ProcessingError, attempt_index: int) -> None:
        if retry_sleep_seconds <= 0 or attempt_index >= max_retries:
            return
        if RETRY_POLICY.get(error.error_type, {}).get("retryable") is not True:
            return
        logger.info(
            json.dumps(
                {
                    "event": "wait",
                    "wait_kind": "retry_backoff",
                    "wait_scope": "relay_retry",
                    "wait_seconds": retry_sleep_seconds,
                    "candidate_external_id": candidate_input.get("external_id"),
                    "attempt": attempt_index + 1,
                    "error_type": error.error_type,
                },
                ensure_ascii=True,
            )
        )
        sleep_fn(retry_sleep_seconds)

    last_error: ProcessingError | None = None
    for attempt in range(max_retries + 1):
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
        waited_seconds = wait_for_request_interval(
            "candidate_prescreen_relay",
            request_interval_seconds,
            sleep_fn=sleep_fn,
        )
        if waited_seconds > 0:
            logger.info(
                json.dumps(
                    {
                        "event": "wait",
                        "wait_kind": "request_interval",
                        "wait_scope": "relay_provider_request",
                        "wait_seconds": waited_seconds,
                        "candidate_external_id": candidate_input.get("external_id"),
                        "attempt": attempt + 1,
                    },
                    ensure_ascii=True,
                )
            )
        try:
            with urllib.request.urlopen(
                request,
                timeout=relay_config.timeout_seconds,
                context=ssl.create_default_context(),
            ) as response:
                raw_body = response.read().decode("utf-8")
                request_id = response.headers.get("X-Request-Id")
                http_status = _response_http_status(response)
        except urllib.error.HTTPError as exc:
            error_type = "api_429" if exc.code == 429 else "dependency_unavailable"
            last_error = ProcessingError(error_type, f"Relay returned HTTP {exc.code}")
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_FAILED,
                    provider_response_status=OUTCOME_FAILED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=exc.code,
                    request_id=None,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type=last_error.error_type,
                    failure_code=last_error.error_type,
                    failure_message=str(last_error),
                    retry_scheduled=attempt < max_retries and RETRY_POLICY.get(error_type, {}).get("retryable") is True,
                )
            )
            _wait_before_retry(last_error, attempt)
            continue
        except urllib.error.URLError as exc:
            last_error = ProcessingError("network_error", f"Relay network error: {exc.reason}")
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_FAILED,
                    provider_response_status=OUTCOME_FAILED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=None,
                    request_id=None,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type=last_error.error_type,
                    failure_code=last_error.error_type,
                    failure_message=str(last_error),
                    retry_scheduled=attempt < max_retries,
                )
            )
            _wait_before_retry(last_error, attempt)
            continue
        except SocketTimeout as exc:
            last_error = ProcessingError("provider_timeout", "Relay timed out")
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_FAILED,
                    provider_response_status=OUTCOME_FAILED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=None,
                    request_id=None,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type=last_error.error_type,
                    failure_code=last_error.error_type,
                    failure_message=str(last_error),
                    retry_scheduled=attempt < max_retries,
                )
            )
            _wait_before_retry(last_error, attempt)
            continue
        last_error = None
        if not raw_body.strip():
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_SUCCEEDED,
                    provider_response_status=OUTCOME_SUCCEEDED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=http_status,
                    request_id=request_id,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type="dependency_unavailable",
                    failure_code="provider_empty_completion",
                    failure_message="Relay returned an empty HTTP 200 body",
                    retry_scheduled=False,
                )
            )
            return _failed_screen_outcome(
                request_id=request_id,
                http_status=http_status,
                mapped_error_type="dependency_unavailable",
                failure_code="provider_empty_completion",
                failure_message="Relay returned an empty HTTP 200 body",
                request_url=request_url,
                response_id=None,
                provider_usage=None,
                api_style=relay_config.api_style,
                model=relay_config.model,
                attempts=attempts,
                transport_status=OUTCOME_SUCCEEDED,
                provider_response_status=OUTCOME_SUCCEEDED,
            )
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_SUCCEEDED,
                    provider_response_status=OUTCOME_SUCCEEDED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=http_status,
                    request_id=request_id,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type="parse_failure",
                    failure_code="parse_failure",
                    failure_message="Relay returned invalid JSON",
                    retry_scheduled=False,
                )
            )
            return _failed_screen_outcome(
                request_id=request_id,
                http_status=http_status,
                mapped_error_type="parse_failure",
                failure_code="parse_failure",
                failure_message="Relay returned invalid JSON",
                request_url=request_url,
                response_id=None,
                provider_usage=None,
                api_style=relay_config.api_style,
                model=relay_config.model,
                attempts=attempts,
                transport_status=OUTCOME_SUCCEEDED,
                provider_response_status=OUTCOME_SUCCEEDED,
            )
        if not isinstance(body, dict):
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_SUCCEEDED,
                    provider_response_status=OUTCOME_FAILED,
                    content_status=OUTCOME_FAILED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=http_status,
                    request_id=request_id,
                    response_id=None,
                    provider_usage=None,
                    mapped_error_type="schema_drift",
                    failure_code="provider_schema_drift",
                    failure_message="Relay response body must be an object",
                    retry_scheduled=False,
                )
            )
            return _failed_screen_outcome(
                request_id=request_id,
                http_status=http_status,
                mapped_error_type="schema_drift",
                failure_code="provider_schema_drift",
                failure_message="Relay response body must be an object",
                request_url=request_url,
                response_id=None,
                provider_usage=None,
                api_style=relay_config.api_style,
                model=relay_config.model,
                attempts=attempts,
                transport_status=OUTCOME_SUCCEEDED,
            )
        response_id, provider_usage = _extract_provider_audit(body, api_style=relay_config.api_style)
        try:
            result = _extract_result_object(body, api_style=relay_config.api_style)
        except RelayOutcomeError as exc:
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=exc.transport_status,
                    provider_response_status=exc.provider_response_status,
                    content_status=exc.content_status,
                    schema_status=exc.schema_status,
                    business_status=exc.business_status,
                    http_status=http_status,
                    request_id=request_id,
                    response_id=response_id,
                    provider_usage=provider_usage,
                    mapped_error_type=exc.mapped_error_type,
                    failure_code=exc.failure_code,
                    failure_message=exc.failure_message,
                    retry_scheduled=False,
                )
            )
            return _failed_screen_outcome(
                request_id=request_id,
                http_status=http_status,
                mapped_error_type=exc.mapped_error_type,
                failure_code=exc.failure_code,
                failure_message=exc.failure_message,
                request_url=request_url,
                response_id=response_id,
                provider_usage=provider_usage,
                api_style=relay_config.api_style,
                model=relay_config.model,
                attempts=attempts,
                transport_status=exc.transport_status,
                provider_response_status=exc.provider_response_status,
                content_status=exc.content_status,
                schema_status=exc.schema_status,
                business_status=exc.business_status,
            )
        normalized = normalize_llm_result(result)
        normalized["channel_metadata"] = {
            "prompt_version": prompt_version,
            "routing_version": routing_version,
            "relay_client_version": relay_config.client_version,
            "model": relay_config.model,
            "transport": relay_transport,
            "request_id": request_id,
        }
        try:
            validate_normalized_llm_prescreen(normalized)
        except ContractValidationError as exc:
            attempts.append(
                _attempt_event(
                    attempt=attempt + 1,
                    request_url=request_url,
                    api_style=relay_config.api_style,
                    model=relay_config.model,
                    transport_status=OUTCOME_SUCCEEDED,
                    provider_response_status=OUTCOME_SUCCEEDED,
                    content_status=OUTCOME_SUCCEEDED,
                    schema_status=OUTCOME_FAILED,
                    business_status=OUTCOME_FAILED,
                    http_status=http_status,
                    request_id=request_id,
                    response_id=response_id,
                    provider_usage=provider_usage,
                    mapped_error_type="json_schema_validation_failed",
                    failure_code="output_schema_validation_failed",
                    failure_message=str(exc),
                    retry_scheduled=False,
                )
            )
            return _failed_screen_outcome(
                request_id=request_id,
                http_status=http_status,
                mapped_error_type="json_schema_validation_failed",
                failure_code="output_schema_validation_failed",
                failure_message=str(exc),
                request_url=request_url,
                response_id=response_id,
                provider_usage=provider_usage,
                api_style=relay_config.api_style,
                model=relay_config.model,
                attempts=attempts,
                transport_status=OUTCOME_SUCCEEDED,
                provider_response_status=OUTCOME_SUCCEEDED,
                content_status=OUTCOME_SUCCEEDED,
            )
        attempts.append(
            _attempt_event(
                attempt=attempt + 1,
                request_url=request_url,
                api_style=relay_config.api_style,
                model=relay_config.model,
                transport_status=OUTCOME_SUCCEEDED,
                provider_response_status=OUTCOME_SUCCEEDED,
                content_status=OUTCOME_SUCCEEDED,
                schema_status=OUTCOME_SUCCEEDED,
                business_status=OUTCOME_SUCCEEDED,
                http_status=http_status,
                request_id=request_id,
                response_id=response_id,
                provider_usage=provider_usage,
                mapped_error_type=None,
                failure_code=None,
                failure_message=None,
                retry_scheduled=False,
            )
        )
        return _successful_screen_outcome(
            request_id=request_id,
            http_status=http_status,
            normalized_result=normalized,
            request_url=request_url,
            response_id=response_id,
            provider_usage=provider_usage,
            api_style=relay_config.api_style,
            model=relay_config.model,
            attempts=attempts,
        )
    if last_error is None:
        last_error = ProcessingError("dependency_unavailable", "Relay request failed before any response was received")
    return _failed_screen_outcome(
        request_id=None,
        http_status=None,
        mapped_error_type=last_error.error_type,
        failure_code=last_error.error_type,
        failure_message=str(last_error),
        request_url=request_url,
        response_id=None,
        provider_usage=None,
        api_style=relay_config.api_style,
        model=relay_config.model,
        attempts=attempts,
        transport_status=OUTCOME_FAILED,
    )
