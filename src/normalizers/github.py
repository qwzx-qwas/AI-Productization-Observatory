"""GitHub normalizer that preserves raw traceability and README excerpt boundaries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.errors import ContractValidationError, ProcessingError
from src.common.schema import validate_instance
from src.runtime.raw_store.file_store import FileRawStore

_GITHUB_NORMALIZATION_VERSION = "github_v1"
_README_EXCERPT_MAX_LENGTH = 8000


def _compact(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    return compact or None


def _truncate_at_boundary(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    boundary = value.rfind("\n\n", 0, limit)
    if boundary >= int(limit * 0.6):
        return value[:boundary].rstrip()
    return value[:limit].rstrip()


def _normalize_topics(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str):
            continue
        topic = entry.strip().lower()
        if not topic or topic in seen:
            continue
        seen.add(topic)
        normalized.append(topic)
    return normalized or None


def _normalize_readme_excerpt(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    filtered_lines: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line:
            if filtered_lines and filtered_lines[-1]:
                filtered_lines.append("")
            continue
        if "img.shields.io" in line or line.startswith("[![") or line.startswith("!["):
            continue
        filtered_lines.append(line)

    paragraphs: list[str] = []
    current: list[str] = []
    for line in filtered_lines:
        if line == "":
            if current:
                paragraphs.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        paragraphs.append(" ".join(current))

    if not paragraphs:
        return None

    excerpt = "\n\n".join(paragraphs)
    return _truncate_at_boundary(excerpt, _README_EXCERPT_MAX_LENGTH)


def _build_metrics_snapshot(payload: dict[str, Any]) -> dict[str, Any] | None:
    metrics = {
        "star_count": payload.get("stargazers_count"),
        "fork_count": payload.get("forks_count"),
        "watcher_count": payload.get("watchers_count"),
    }
    if all(value is None for value in metrics.values()):
        return None
    return metrics


def _build_raw_text_excerpt(description: str | None, readme_excerpt: str | None) -> str | None:
    segments = [segment for segment in (description, readme_excerpt) if segment]
    if not segments:
        return None
    return _truncate_at_boundary("\n\n".join(segments), _README_EXCERPT_MAX_LENGTH)


def normalize_raw_record(
    raw_record: dict[str, Any],
    raw_store: FileRawStore,
    schema_path: Path,
    normalization_version: str = _GITHUB_NORMALIZATION_VERSION,
) -> dict[str, Any]:
    payload = raw_store.load_payload(raw_record["raw_payload_ref"])
    owner = payload.get("owner") if isinstance(payload.get("owner"), dict) else {}
    owner_login = owner.get("login") if isinstance(owner.get("login"), str) else None
    owner_name = owner.get("name") if isinstance(owner.get("name"), str) else None
    description = _compact(payload.get("description"))
    readme_excerpt = _normalize_readme_excerpt(payload.get("readme_text"))
    pushed_at = payload.get("pushed_at")
    current_summary = description[:160] if description else None

    source_item = {
        "raw_id": raw_record["raw_id"],
        "source_id": raw_record["source_id"],
        "external_id": raw_record["external_id"],
        "canonical_url": payload.get("html_url"),
        "linked_homepage_url": payload.get("homepage"),
        "linked_repo_url": None,
        "title": payload.get("name"),
        "author_name": owner_name or owner_login,
        "author_handle": owner_login,
        "published_at": pushed_at,
        "raw_text_excerpt": _build_raw_text_excerpt(description, readme_excerpt),
        "current_summary": current_summary,
        "current_metrics_json": _build_metrics_snapshot(payload),
        "topics": _normalize_topics(payload.get("topics")),
        "language": payload.get("language"),
        "item_status": "archived" if payload.get("archived") is True else "active",
        "first_observed_at": pushed_at or raw_record.get("fetched_at") or raw_record["collected_at"],
        "latest_observed_at": raw_record.get("fetched_at") or raw_record["collected_at"],
        "normalization_version": normalization_version,
    }

    try:
        validate_instance(source_item, schema_path)
    except ContractValidationError as exc:
        raise ProcessingError("json_schema_validation_failed", str(exc)) from exc
    return source_item
