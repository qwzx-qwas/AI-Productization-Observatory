"""End-to-end candidate prescreen workflow helpers."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.candidate_prescreen.config import (
    build_analysis_run_key,
    build_sample_key,
    candidate_batch_id,
    candidate_id,
    load_candidate_prescreen_config,
)
from src.candidate_prescreen.discovery import discover_candidates, discovery_metadata
from src.candidate_prescreen.prompt_contract import candidate_prescreener_prompt_contract
from src.candidate_prescreen.review_card import empty_llm_prescreen, validate_candidate_review_card
from src.candidate_prescreen.relay import (
    PAYLOAD_BUILDER_VERSION,
    build_relay_candidate_input,
    screen_candidate,
    screen_candidate_outcome_succeeded,
)
from src.candidate_prescreen.staging import handoff_candidate_to_staging
from src.candidate_prescreen.url_utils import candidate_url_dedupe_key, normalize_candidate_url
from src.common.config import AppConfig
from src.common.constants import RETRY_POLICY
from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from src.common.logging_utils import get_logger
from src.common.request_timing import (
    resolve_discovery_request_interval_seconds,
    resolve_request_interval_seconds,
    resolve_retry_sleep_seconds,
)
from src.common.schema import validate_instance

DUPLICATE_ARCHIVE_DIR_NAME = ".duplicate_archive"
DUPLICATE_ARCHIVE_AUDIT_FILE_NAME = "duplicate_candidate_archive_audit.jsonl"
INVALID_WINDOW_ARCHIVE_DIR_NAME = ".invalid_window_archive"
INVALID_WINDOW_ARCHIVE_AUDIT_FILE_NAME = "invalid_window_candidate_archive_audit.jsonl"
FUTURE_WINDOW_GRACE_DAYS = 7


def _schema_path(config: AppConfig) -> Path:
    return config.schema_dir / "candidate_prescreen_record.schema.json"


def _candidate_doc_path(config: AppConfig, source: str, window: str, candidate_identifier: str) -> Path:
    return config.candidate_workspace_dir / source / window.replace("..", "_") / f"{candidate_identifier}.yaml"


def candidate_archive_dir(config: AppConfig) -> Path:
    return config.candidate_workspace_dir / DUPLICATE_ARCHIVE_DIR_NAME


def candidate_invalid_window_archive_dir(config: AppConfig) -> Path:
    return config.candidate_workspace_dir / INVALID_WINDOW_ARCHIVE_DIR_NAME


def _is_archived_candidate_path(config: AppConfig, candidate_path: Path) -> bool:
    for archive_dir in (candidate_archive_dir(config), candidate_invalid_window_archive_dir(config)):
        try:
            candidate_path.relative_to(archive_dir)
            return True
        except ValueError:
            continue
    return False


def candidate_record_paths(config: AppConfig) -> list[Path]:
    if not config.candidate_workspace_dir.exists():
        return []
    paths: list[Path] = []
    for candidate_path in sorted(config.candidate_workspace_dir.rglob("*.yaml")):
        if candidate_path.name.startswith("."):
            continue
        if _is_archived_candidate_path(config, candidate_path):
            continue
        try:
            relative_parts = candidate_path.relative_to(config.candidate_workspace_dir).parts
        except ValueError:
            continue
        if any(part.startswith(".") for part in relative_parts[:-1]):
            continue
        paths.append(candidate_path)
    return paths


def _source_summary(item: dict[str, Any]) -> str:
    summary = item.get("summary")
    if isinstance(summary, str):
        return summary
    return ""


def _raw_excerpt(item: dict[str, Any]) -> str:
    excerpt = item.get("raw_evidence_excerpt")
    if isinstance(excerpt, str):
        return excerpt
    return ""


def _candidate_input(item: dict[str, Any], metadata: dict[str, Any], window: str) -> dict[str, Any]:
    return {
        "source": metadata["source_id"].replace("src_", ""),
        "source_id": metadata["source_id"],
        "source_window": window,
        "time_field": metadata["time_field"],
        "external_id": str(item["external_id"]),
        "canonical_url": normalize_candidate_url(item.get("canonical_url"), field_name="candidate_discovery_item.canonical_url"),
        "title": item["title"],
        "summary": _source_summary(item),
        "raw_evidence_excerpt": _raw_excerpt(item),
        "query_family": metadata["query_family"],
        "query_slice_id": metadata["query_slice_id"],
        "selection_rule_version": metadata["selection_rule_version"],
    }


def _source_trace(candidate_input: dict[str, Any], metadata: dict[str, Any], *, discovery_mode: str) -> dict[str, Any]:
    return {
        "discovery_mode": discovery_mode,
        "selection_basis": metadata["selection_basis"],
        "source_item_ref": {
            "source": candidate_input["source"],
            "source_id": candidate_input["source_id"],
            "source_window": candidate_input["source_window"],
            "external_id": candidate_input["external_id"],
            "canonical_url": candidate_input["canonical_url"],
        },
    }


def _empty_prescreen_record(
    candidate_input: dict[str, Any],
    *,
    batch_id: str,
    candidate_identifier: str,
    metadata: dict[str, Any],
    llm_defaults: dict[str, Any],
    discovery_mode: str,
) -> dict[str, Any]:
    now_iso = utc_now_iso()
    return {
        "document_type": "candidate_prescreen_record",
        "document_version": "candidate_prescreen_v1",
        "candidate_id": candidate_identifier,
        "candidate_batch_id": batch_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "source": candidate_input["source"],
        "source_id": candidate_input["source_id"],
        "source_window": candidate_input["source_window"],
        "time_field": candidate_input["time_field"],
        "external_id": candidate_input["external_id"],
        "canonical_url": candidate_input["canonical_url"],
        "title": candidate_input["title"],
        "summary": candidate_input["summary"],
        "raw_evidence_excerpt": candidate_input["raw_evidence_excerpt"],
        "query_family": candidate_input["query_family"],
        "query_slice_id": candidate_input["query_slice_id"],
        "selection_rule_version": candidate_input["selection_rule_version"],
        "source_trace": _source_trace(candidate_input, metadata, discovery_mode=discovery_mode),
        "llm_prescreen": empty_llm_prescreen(
            prompt_version=str(llm_defaults["prompt_version"]),
            routing_version=str(llm_defaults["routing_version"]),
            relay_client_version=str(llm_defaults["relay_client_version"]),
            relay_transport=str(llm_defaults["relay_transport"]),
        ),
        "whitelist_reason": None,
        "human_review_status": "pending_first_pass",
        "human_review_note_template_key": None,
        "human_review_notes": None,
        "human_reviewed_at": None,
        "staging_handoff": {
            "status": "not_started",
            "staging_document_path": None,
            "sample_slot_id": None,
            "sample_id": None,
            "blocking_items": [],
            "last_attempted_at": None,
        },
    }


def _apply_candidate_snapshot(
    record: dict[str, Any],
    candidate_input: dict[str, Any],
    *,
    metadata: dict[str, Any],
    discovery_mode: str,
) -> None:
    record["source"] = candidate_input["source"]
    record["source_id"] = candidate_input["source_id"]
    record["source_window"] = candidate_input["source_window"]
    record["time_field"] = candidate_input["time_field"]
    record["external_id"] = candidate_input["external_id"]
    record["canonical_url"] = candidate_input["canonical_url"]
    record["title"] = candidate_input["title"]
    record["summary"] = candidate_input["summary"]
    record["raw_evidence_excerpt"] = candidate_input["raw_evidence_excerpt"]
    record["query_family"] = candidate_input["query_family"]
    record["query_slice_id"] = candidate_input["query_slice_id"]
    record["selection_rule_version"] = candidate_input["selection_rule_version"]
    record["source_trace"] = _source_trace(candidate_input, metadata, discovery_mode=discovery_mode)


def _parse_iso_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def semantic_candidate_key_from_record(record: dict[str, Any]) -> tuple[str, str]:
    return candidate_url_dedupe_key(
        record.get("source_id"),
        record.get("canonical_url"),
        source_field_name="candidate_prescreen_record.source_id",
        url_field_name="candidate_prescreen_record.canonical_url",
    )


def sample_key_from_record(record: dict[str, Any]) -> str:
    return build_sample_key(
        str(record.get("source_id") or ""),
        str(record.get("canonical_url") or ""),
    )


def _candidate_input_from_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": record["source"],
        "source_id": record["source_id"],
        "source_window": record["source_window"],
        "time_field": record["time_field"],
        "external_id": record["external_id"],
        "canonical_url": record["canonical_url"],
        "title": record["title"],
        "summary": record.get("summary") or "",
        "raw_evidence_excerpt": record.get("raw_evidence_excerpt") or "",
        "query_family": record.get("query_family"),
        "query_slice_id": record.get("query_slice_id"),
        "selection_rule_version": record.get("selection_rule_version"),
    }


def _analysis_run_key_for_candidate(candidate_input: dict[str, Any], *, llm_defaults: dict[str, Any]) -> str:
    sample_key = build_sample_key(candidate_input["source_id"], candidate_input["canonical_url"])
    return build_analysis_run_key(
        sample_key=sample_key,
        cleaned_candidate_input=build_relay_candidate_input(candidate_input),
        prompt_version=str(llm_defaults["prompt_version"]),
        routing_version=str(llm_defaults["routing_version"]),
        relay_client_version=str(llm_defaults["relay_client_version"]),
        payload_builder_version=PAYLOAD_BUILDER_VERSION,
    )


def _workspace_sample_index(config: AppConfig) -> dict[str, tuple[Path, dict[str, Any]]]:
    if not config.candidate_workspace_dir.exists():
        return {}
    preferred_by_key: dict[str, tuple[Path, dict[str, Any]]] = {}
    for candidate_path in candidate_record_paths(config):
        payload = load_yaml(candidate_path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
        validate_candidate_record(config, payload)
        sample_key = sample_key_from_record(payload)
        existing = preferred_by_key.get(sample_key)
        if existing is None or candidate_record_preference_key(payload, candidate_path) > candidate_record_preference_key(
            existing[1],
            existing[0],
        ):
            preferred_by_key[sample_key] = (candidate_path, payload)
    return preferred_by_key


def candidate_record_preference_key(record: dict[str, Any], candidate_path: Path) -> tuple[int, int, int, datetime, str]:
    staging_handoff = record.get("staging_handoff")
    staging_status = staging_handoff.get("status") if isinstance(staging_handoff, dict) else None
    handoff_rank = 2 if staging_status == "written" else 1 if staging_status == "not_started" else 0
    review_status = record.get("human_review_status")
    review_rank = {
        "approved_for_staging": 3,
        "on_hold": 2,
        "rejected_after_human_review": 1,
        "pending_first_pass": 0,
    }.get(review_status, 0)
    llm_prescreen = record.get("llm_prescreen")
    llm_rank = 1 if isinstance(llm_prescreen, dict) and llm_prescreen.get("status") == "succeeded" else 0
    return (handoff_rank, review_rank, llm_rank, _parse_iso_timestamp(record.get("updated_at")), str(candidate_path))


def _workspace_semantic_index(config: AppConfig) -> dict[tuple[str, str], tuple[Path, dict[str, Any]]]:
    if not config.candidate_workspace_dir.exists():
        return {}
    preferred_by_key: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for candidate_path in candidate_record_paths(config):
        payload = load_yaml(candidate_path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
        validate_candidate_record(config, payload)
        semantic_key = semantic_candidate_key_from_record(payload)
        existing = preferred_by_key.get(semantic_key)
        if existing is None or candidate_record_preference_key(payload, candidate_path) > candidate_record_preference_key(
            existing[1],
            existing[0],
        ):
            preferred_by_key[semantic_key] = (candidate_path, payload)
    return preferred_by_key


def _retry_cooldown_active(record: dict[str, Any], *, retry_sleep_seconds: int) -> bool:
    if retry_sleep_seconds <= 0:
        return False
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        return False
    error_type = llm_prescreen.get("error_type")
    if RETRY_POLICY.get(error_type, {}).get("retryable") is not True:
        return False
    updated_at = _parse_iso_timestamp(record.get("updated_at"))
    elapsed_seconds = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return elapsed_seconds < retry_sleep_seconds


def _should_refresh_existing_record(
    record: dict[str, Any],
    *,
    current_analysis_run_key: str,
    llm_defaults: dict[str, Any],
    retry_sleep_seconds: int,
) -> bool:
    if record.get("human_review_status") != "pending_first_pass":
        return False
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        return True
    existing_analysis_run_key = _analysis_run_key_for_candidate(
        _candidate_input_from_record(record),
        llm_defaults=llm_defaults,
    )
    if existing_analysis_run_key != current_analysis_run_key:
        return True
    status = llm_prescreen.get("status")
    if status == "succeeded":
        return False
    if status != "failed":
        return True
    if _retry_cooldown_active(record, retry_sleep_seconds=retry_sleep_seconds):
        return False
    error_type = llm_prescreen.get("error_type")
    return RETRY_POLICY.get(error_type, {}).get("retryable") is True


def _archive_audit_path(config: AppConfig) -> Path:
    return candidate_archive_dir(config) / DUPLICATE_ARCHIVE_AUDIT_FILE_NAME


def _append_archive_audit(config: AppConfig, payload: dict[str, Any]) -> None:
    audit_path = _archive_audit_path(config)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _invalid_window_archive_audit_path(config: AppConfig) -> Path:
    return candidate_invalid_window_archive_dir(config) / INVALID_WINDOW_ARCHIVE_AUDIT_FILE_NAME


def _append_invalid_window_archive_audit(config: AppConfig, payload: dict[str, Any]) -> None:
    audit_path = _invalid_window_archive_audit_path(config)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _parse_source_window(window: Any) -> tuple[date, date] | None:
    if not isinstance(window, str) or ".." not in window:
        return None
    start_text, end_text = window.split("..", 1)
    try:
        return date.fromisoformat(start_text), date.fromisoformat(end_text)
    except ValueError:
        return None


def _archive_destination_path(config: AppConfig, candidate_path: Path) -> Path:
    relative_path = candidate_path.relative_to(config.candidate_workspace_dir)
    destination = candidate_archive_dir(config) / relative_path
    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate_destination = destination.with_name(f"{stem}__archived_{counter}{suffix}")
        if not candidate_destination.exists():
            return candidate_destination
        counter += 1


def _invalid_window_archive_destination_path(config: AppConfig, candidate_path: Path) -> Path:
    relative_path = candidate_path.relative_to(config.candidate_workspace_dir)
    destination = candidate_invalid_window_archive_dir(config) / relative_path
    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate_destination = destination.with_name(f"{stem}__archived_{counter}{suffix}")
        if not candidate_destination.exists():
            return candidate_destination
        counter += 1


def archive_duplicate_candidate_records(config: AppConfig) -> dict[str, Any]:
    active_paths = candidate_record_paths(config)
    grouped: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = {}
    for candidate_path in active_paths:
        record = load_yaml(candidate_path)
        if not isinstance(record, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
        validate_candidate_record(config, record)
        grouped.setdefault(semantic_candidate_key_from_record(record), []).append((candidate_path, record))

    archived_records: list[dict[str, Any]] = []
    skipped_groups: list[dict[str, Any]] = []
    duplicate_group_count = 0
    for semantic_key, entries in sorted(grouped.items(), key=lambda item: item[0]):
        if len(entries) <= 1:
            continue
        duplicate_group_count += 1
        written_entries = [
            (candidate_path, record)
            for candidate_path, record in entries
            if isinstance(record.get("staging_handoff"), dict) and record["staging_handoff"].get("status") == "written"
        ]
        if len(written_entries) > 1:
            skipped = {
                "source_id": semantic_key[0],
                "normalized_canonical_url": semantic_key[1],
                "dedupe_basis": "source_id + normalized canonical_url",
                "reason": "multiple_written_staging_records",
                "candidate_ids": [record["candidate_id"] for _, record in entries],
                "candidate_paths": [str(candidate_path) for candidate_path, _ in entries],
            }
            skipped_groups.append(skipped)
            _append_archive_audit(
                config,
                {
                    "event": "duplicate_group_skipped",
                    "recorded_at": utc_now_iso(),
                    **skipped,
                },
            )
            continue
        if written_entries:
            kept_path, kept_record = written_entries[0]
        else:
            kept_path, kept_record = max(
                entries,
                key=lambda item: candidate_record_preference_key(item[1], item[0]),
            )
        for candidate_path, record in entries:
            if candidate_path == kept_path:
                continue
            destination = _archive_destination_path(config, candidate_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(candidate_path, destination)
            archived_entry = {
                "source_id": semantic_key[0],
                "normalized_canonical_url": semantic_key[1],
                "dedupe_basis": "source_id + normalized canonical_url",
                "archived_candidate_id": record["candidate_id"],
                "archived_external_id": record["external_id"],
                "archived_canonical_url": record["canonical_url"],
                "archived_from": str(candidate_path),
                "archived_to": str(destination),
                "kept_candidate_id": kept_record["candidate_id"],
                "kept_external_id": kept_record["external_id"],
                "kept_canonical_url": kept_record["canonical_url"],
                "kept_candidate_path": str(kept_path),
            }
            archived_records.append(archived_entry)
            _append_archive_audit(
                config,
                {
                    "event": "candidate_archived",
                    "recorded_at": utc_now_iso(),
                    **archived_entry,
                },
            )

    return {
        "duplicate_group_count": duplicate_group_count,
        "archived_record_count": len(archived_records),
        "skipped_group_count": len(skipped_groups),
        "archived_records": archived_records,
        "skipped_groups": skipped_groups,
        "active_candidate_document_count": validate_candidate_workspace(config),
        "archive_audit_path": str(_archive_audit_path(config)),
    }


def archive_future_window_candidate_records(
    config: AppConfig,
    *,
    today: date | None = None,
    grace_days: int = FUTURE_WINDOW_GRACE_DAYS,
) -> dict[str, Any]:
    effective_today = today or date.today()
    future_cutoff = effective_today + timedelta(days=grace_days)
    archived_records: list[dict[str, Any]] = []
    skipped_records: list[dict[str, Any]] = []

    for candidate_path in candidate_record_paths(config):
        payload = load_yaml(candidate_path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
        validate_candidate_record(config, payload)
        parsed_window = _parse_source_window(payload.get("source_window"))
        if parsed_window is None:
            skipped = {
                "candidate_id": payload.get("candidate_id"),
                "candidate_path": str(candidate_path),
                "reason": "source_window_unparseable",
            }
            skipped_records.append(skipped)
            _append_invalid_window_archive_audit(
                config,
                {
                    "event": "invalid_window_candidate_skipped",
                    "recorded_at": utc_now_iso(),
                    **skipped,
                },
            )
            continue

        _, window_end = parsed_window
        if window_end <= future_cutoff:
            continue

        destination = _invalid_window_archive_destination_path(config, candidate_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(candidate_path, destination)
        archived_entry = {
            "candidate_id": payload["candidate_id"],
            "candidate_path": str(candidate_path),
            "archived_to": str(destination),
            "source_window": payload.get("source_window"),
            "future_cutoff": future_cutoff.isoformat(),
        }
        archived_records.append(archived_entry)
        _append_invalid_window_archive_audit(
            config,
            {
                "event": "invalid_window_candidate_archived",
                "recorded_at": utc_now_iso(),
                **archived_entry,
            },
        )

    return {
        "future_cutoff": future_cutoff.isoformat(),
        "archived_record_count": len(archived_records),
        "skipped_record_count": len(skipped_records),
        "archived_records": archived_records,
        "skipped_records": skipped_records,
        "active_candidate_document_count": validate_candidate_workspace(config),
        "archive_audit_path": str(_invalid_window_archive_audit_path(config)),
    }


def validate_candidate_record(config: AppConfig, record: dict[str, Any]) -> None:
    validate_instance(record, _schema_path(config))
    normalize_candidate_url(record.get("canonical_url"), field_name="candidate_prescreen_record.canonical_url")
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    workspace = workflow_config.get("workspace")
    if not isinstance(workspace, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml:workspace must be a mapping")
    note_templates = workspace.get("human_review_note_templates")
    if not isinstance(note_templates, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml:workspace:human_review_note_templates must be a mapping")
    validate_candidate_review_card(record, note_templates=note_templates)


def run_candidate_prescreen(
    config: AppConfig,
    *,
    source_code: str,
    window: str,
    query_slice_id: str | None,
    limit: int,
    discovery_fixture_path: Path | None,
    llm_fixture_path: Path | None,
    discovery_request_interval_seconds: int | None = None,
    request_interval_seconds: int | None = None,
    retry_sleep_seconds: int | None = None,
    run_id: str | None = None,
) -> list[Path]:
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    llm_defaults = workflow_config["llm_prescreen"]
    resolved_discovery_request_interval_seconds = resolve_discovery_request_interval_seconds(discovery_request_interval_seconds)
    resolved_request_interval_seconds = resolve_request_interval_seconds(request_interval_seconds)
    resolved_retry_sleep_seconds = resolve_retry_sleep_seconds(retry_sleep_seconds)
    discovery_mode = "fixture" if discovery_fixture_path is not None else "live"
    items = discover_candidates(
        workflow_config,
        source_code=source_code,
        window=window,
        query_slice_id=query_slice_id,
        limit=limit,
        fixture_path=discovery_fixture_path,
        timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
        request_interval_seconds=resolved_discovery_request_interval_seconds,
        run_id=run_id,
    )
    metadata = discovery_metadata(
        workflow_config,
        source_code=source_code,
        window=window,
        query_slice_id=query_slice_id,
        discovery_mode=discovery_mode,
    )
    logger = get_logger(
        "candidate_prescreen_workflow",
        source_id=str(metadata["source_id"]),
        task_id="run_candidate_prescreen",
        resolution_status="running",
        run_id=run_id,
    )
    batch_id = candidate_batch_id(source_code, window, metadata["query_slice_id"])
    preferred_by_key = _workspace_sample_index(config)
    written_paths: list[Path] = []
    for item in items:
        if len(written_paths) >= limit:
            break
        try:
            candidate_input = _candidate_input(item, metadata, window)
        except ContractValidationError as exc:
            logger.info(
                {
                    "event": "candidate_rejected",
                    "window": window,
                    "query_slice_id": metadata["query_slice_id"],
                    "candidate_external_id": str(item.get("external_id") or ""),
                    "candidate_canonical_url": item.get("canonical_url"),
                    "reason": str(exc),
                    "rejection_reason": "invalid_canonical_url",
                }
            )
            continue
        sample_key = build_sample_key(
            candidate_input["source_id"],
            candidate_input["canonical_url"],
        )
        current_analysis_run_key = _analysis_run_key_for_candidate(
            candidate_input,
            llm_defaults=llm_defaults,
        )
        existing_entry = preferred_by_key.get(sample_key)
        if existing_entry is not None:
            output_path, record = existing_entry
            if (
                record.get("source_window") != candidate_input["source_window"]
                or record.get("query_slice_id") != candidate_input["query_slice_id"]
            ):
                continue
            if not _should_refresh_existing_record(
                record,
                current_analysis_run_key=current_analysis_run_key,
                llm_defaults=llm_defaults,
                retry_sleep_seconds=resolved_retry_sleep_seconds,
            ):
                continue
            _apply_candidate_snapshot(record, candidate_input, metadata=metadata, discovery_mode=discovery_mode)
            record["candidate_batch_id"] = batch_id
        else:
            candidate_identifier = candidate_id(source_code, window, metadata["query_slice_id"], candidate_input["external_id"])
            record = _empty_prescreen_record(
                candidate_input,
                batch_id=batch_id,
                candidate_identifier=candidate_identifier,
                metadata=metadata,
                llm_defaults=llm_defaults,
                discovery_mode=discovery_mode,
            )
            output_path = _candidate_doc_path(config, source_code, window, candidate_identifier)
        try:
            llm_outcome = screen_candidate(
                candidate_input,
                prompt_version=str(llm_defaults["prompt_version"]),
                routing_version=str(llm_defaults["routing_version"]),
                relay_transport=str(llm_defaults["relay_transport"]),
                relay_client_version=str(llm_defaults["relay_client_version"]),
                prompt_contract=candidate_prescreener_prompt_contract(
                    prompt_spec_ref=str(llm_defaults.get("prompt_spec_ref") or ""),
                ),
                fixture_path=llm_fixture_path,
                timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
                max_retries=int(llm_defaults["max_retries_default"]),
                request_interval_seconds=resolved_request_interval_seconds,
                retry_sleep_seconds=resolved_retry_sleep_seconds,
                run_id=run_id,
            )
        except (ProcessingError, ContractValidationError) as exc:
            record["llm_prescreen"]["status"] = "failed"
            if isinstance(exc, ProcessingError):
                record["llm_prescreen"]["error_type"] = exc.error_type
            else:
                record["llm_prescreen"]["error_type"] = "schema_drift"
            record["llm_prescreen"]["error_message"] = str(exc)
        else:
            if not screen_candidate_outcome_succeeded(llm_outcome):
                record["llm_prescreen"]["status"] = "failed"
                record["llm_prescreen"]["error_type"] = llm_outcome.get("mapped_error_type")
                record["llm_prescreen"]["error_message"] = (
                    llm_outcome.get("failure_message")
                    or llm_outcome.get("failure_code")
                )
            else:
                llm_result = llm_outcome["normalized_result"]
                record["llm_prescreen"]["status"] = "succeeded"
                record["llm_prescreen"]["in_observatory_scope"] = llm_result["in_observatory_scope"]
                record["llm_prescreen"]["reason"] = llm_result["reason"]
                record["llm_prescreen"]["decision_snapshot"] = llm_result["decision_snapshot"]
                record["llm_prescreen"]["scope_boundary_note"] = llm_result["scope_boundary_note"]
                record["llm_prescreen"]["source_evidence_summary"] = llm_result["source_evidence_summary"]
                record["llm_prescreen"]["evidence_anchors"] = llm_result["evidence_anchors"]
                record["llm_prescreen"]["review_focus_points"] = llm_result["review_focus_points"]
                record["llm_prescreen"]["uncertainty_points"] = llm_result["uncertainty_points"]
                record["llm_prescreen"]["recommend_candidate_pool"] = llm_result["recommend_candidate_pool"]
                record["llm_prescreen"]["recommended_action"] = llm_result["recommended_action"]
                record["llm_prescreen"]["confidence_summary"] = llm_result["confidence_summary"]
                record["llm_prescreen"]["handoff_readiness_hint"] = llm_result["handoff_readiness_hint"]
                record["llm_prescreen"]["persona_candidates"] = llm_result["persona_candidates"]
                record["llm_prescreen"]["taxonomy_hints"] = llm_result["taxonomy_hints"]
                record["llm_prescreen"]["assessment_hints"] = llm_result["assessment_hints"]
                record["llm_prescreen"]["channel_metadata"] = llm_result["channel_metadata"]
                record["llm_prescreen"]["error_type"] = None
                record["llm_prescreen"]["error_message"] = None
        record["updated_at"] = utc_now_iso()
        validate_candidate_record(config, record)
        dump_yaml(output_path, record)
        preferred_by_key[sample_key] = (output_path, record)
        written_paths.append(output_path)
    return written_paths


def validate_candidate_workspace(config: AppConfig) -> int:
    if config.candidate_workspace_dir == config.gold_set_dir or config.gold_set_dir in config.candidate_workspace_dir.parents:
        raise ContractValidationError("candidate workspace must stay outside gold_set/")
    active_paths = candidate_record_paths(config)
    if not active_paths:
        return 0
    candidate_ids: set[str] = set()
    count = 0
    for path in active_paths:
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {path}")
        validate_candidate_record(config, payload)
        candidate_identifier = payload["candidate_id"]
        if candidate_identifier in candidate_ids:
            raise ContractValidationError(f"Duplicate candidate_id in candidate workspace: {candidate_identifier}")
        candidate_ids.add(candidate_identifier)
        count += 1
    return count


def handoff_candidates_to_staging(
    config: AppConfig,
    *,
    candidate_ids: list[str] | None,
) -> list[tuple[Path, str, str]]:
    results: list[tuple[Path, str, str]] = []
    selected = set(candidate_ids or [])
    for path in sorted(config.candidate_workspace_dir.rglob("*.yaml")):
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            continue
        validate_candidate_record(config, payload)
        candidate_identifier = str(payload["candidate_id"])
        if selected and candidate_identifier not in selected:
            continue
        if payload["human_review_status"] != "approved_for_staging":
            continue
        try:
            staging_document_path, slot_id = handoff_candidate_to_staging(
                payload,
                candidate_path=path,
                staging_dir=config.gold_set_staging_dir,
            )
        except ContractValidationError as exc:
            if "Semantic duplicate source URL already present in staging" not in str(exc):
                raise
            payload["staging_handoff"] = {
                "status": "blocked",
                "staging_document_path": None,
                "sample_slot_id": None,
                "sample_id": None,
                "blocking_items": [str(exc)],
                "last_attempted_at": utc_now_iso(),
            }
            payload["updated_at"] = utc_now_iso()
            validate_candidate_record(config, payload)
            dump_yaml(path, payload)
            continue
        payload["staging_handoff"] = {
            "status": "written",
            "staging_document_path": staging_document_path,
            "sample_slot_id": slot_id,
            "sample_id": candidate_identifier,
            "blocking_items": [],
            "last_attempted_at": utc_now_iso(),
        }
        payload["updated_at"] = utc_now_iso()
        validate_candidate_record(config, payload)
        dump_yaml(path, payload)
        results.append((path, staging_document_path, slot_id))
    return results
