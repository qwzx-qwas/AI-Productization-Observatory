"""Relay-LLM adapter for candidate prescreening."""

from __future__ import annotations

import json
import os
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


@dataclass(frozen=True)
class RelayConfig:
    base_url: str
    token: str
    model: str
    timeout_seconds: int
    client_version: str

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
        return cls(
            base_url=base_url,
            token=token,
            model=model,
            timeout_seconds=timeout_seconds,
            client_version=client_version,
        )


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
    payload = {
        "task": "candidate_prescreen",
        "model": relay_config.model,
        "prompt_version": prompt_version,
        "routing_version": routing_version,
        "input": candidate_input,
    }
    if isinstance(prompt_contract, dict) and prompt_contract:
        payload["prompt_contract"] = prompt_contract
    last_error: ProcessingError | None = None
    for _attempt in range(max_retries + 1):
        request = urllib.request.Request(
            relay_config.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {relay_config.token}",
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
        result = None
        if isinstance(body, dict):
            if isinstance(body.get("result"), dict):
                result = body["result"]
            elif isinstance(body.get("output"), dict):
                result = body["output"]
        if not isinstance(result, dict):
            raise ProcessingError("schema_drift", "Relay response must provide a result object")
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
