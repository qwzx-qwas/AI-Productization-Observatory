"""URL validation and normalization helpers for candidate prescreen handoff boundaries."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.common.errors import ContractValidationError


def _require_non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value.strip()


def _normalized_netloc(parts: Any, field_name: str) -> str:
    hostname = parts.hostname
    if not isinstance(hostname, str) or not hostname:
        raise ContractValidationError(f"{field_name} must include a hostname")
    normalized_host = hostname.lower()
    if ":" in normalized_host and not normalized_host.startswith("["):
        normalized_host = f"[{normalized_host}]"
    userinfo = ""
    if parts.username is not None:
        userinfo = parts.username
        if parts.password is not None:
            userinfo = f"{userinfo}:{parts.password}"
        userinfo = f"{userinfo}@"
    if parts.port is not None:
        return f"{userinfo}{normalized_host}:{parts.port}"
    return f"{userinfo}{normalized_host}"


def normalize_candidate_url(value: Any, *, field_name: str = "canonical_url") -> str:
    raw_url = _require_non_empty_string(value, field_name)
    parts = urlsplit(raw_url)
    scheme = parts.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ContractValidationError(f"{field_name} must use http or https")
    normalized_path = parts.path or "/"
    if normalized_path != "/":
        normalized_path = normalized_path.rstrip("/") or "/"
    normalized_query = urlencode(sorted(parse_qsl(parts.query, keep_blank_values=True)))
    return urlunsplit(
        (
            scheme,
            _normalized_netloc(parts, field_name),
            normalized_path,
            normalized_query,
            "",
        )
    )


def candidate_url_dedupe_key(
    source_id: Any,
    canonical_url: Any,
    *,
    source_field_name: str = "source_id",
    url_field_name: str = "canonical_url",
) -> tuple[str, str]:
    return (
        _require_non_empty_string(source_id, source_field_name),
        normalize_candidate_url(canonical_url, field_name=url_field_name),
    )
