"""Persistent controller that keeps filling staging until all 300 slots are occupied.

The control loop keeps long-running responsibility in code:
- read real progress from staging YAML on disk
- consume already-written candidate docs first
- call the API-backed LLM as a constrained first-pass reviewer
- hand off only approved candidates into staging
- validate and audit every iteration
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from typing import Any, Callable

from src.candidate_prescreen.config import load_candidate_prescreen_config, query_slice_config, source_config
from src.candidate_prescreen.prompt_contract import candidate_prescreener_prompt_contract
from src.candidate_prescreen.relay import (
    clean_raw_evidence_excerpt,
    relay_preflight,
    screen_candidate,
    screen_candidate_outcome_succeeded,
)
from src.candidate_prescreen.staging import EXPECTED_TOTAL_SLOTS, handoff_candidate_to_staging, staging_progress, validate_staging_workspace
from src.candidate_prescreen.workflow import (
    archive_future_window_candidate_records,
    candidate_record_paths,
    candidate_record_preference_key,
    run_candidate_prescreen,
    semantic_candidate_key_from_record,
    validate_candidate_record,
    validate_candidate_workspace,
)
from src.common.config import AppConfig
from src.common.constants import RETRY_POLICY
from src.common.errors import ConfigError, ContractValidationError, ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from src.common.logging_utils import get_logger
from src.common.request_timing import (
    resolve_discovery_request_interval_seconds,
    resolve_request_interval_seconds,
    resolve_retry_sleep_seconds,
)

AUDIT_LOG_FILE_NAME = "fill_gold_set_staging_audit.jsonl"
DEFAULT_SOURCE_CODE = "github"
DEFAULT_LIVE_LIMIT = 1
MAX_LIVE_LIMIT = 2
RECOMMENDED_ACTION_TO_REVIEW_STATUS = {
    "candidate_pool": "approved_for_staging",
    "whitelist_candidate": "approved_for_staging",
    "hold": "on_hold",
    "reject": "rejected_after_human_review",
}
REVIEW_STATUS_TO_TEMPLATE_KEY = {
    "approved_for_staging": "approved",
    "on_hold": "hold",
    "rejected_after_human_review": "rejected",
}
TERMINAL_FILL_ERROR_TYPES = {
    "future_window_exhausted",
    "json_schema_validation_failed",
    "parse_failure",
    "relay_preflight_failed",
    "resume_state_invalid",
    "schema_drift",
}
TERMINAL_AUDIT_EVENTS = {"blocked", "completed", "interrupted_assumed", "max_iterations_reached"}


@dataclass
class LiveDiscoveryCursor:
    source_code: str
    query_slice_ids: list[str]
    window_start: date
    window_end: date
    query_index: int = 0

    @classmethod
    def from_workflow(
        cls,
        workflow_config: dict[str, Any],
        *,
        source_code: str,
        initial_window: str | None,
        query_slice_id: str | None,
    ) -> "LiveDiscoveryCursor":
        window_text = initial_window or _default_initial_window()
        window_start, window_end = _parse_window(window_text)
        if query_slice_id is not None:
            query_slice_config(workflow_config, source_code, query_slice_id)
            query_slice_ids = [query_slice_id]
        else:
            source = source_config(workflow_config, source_code)
            raw_slices = source.get("query_slices")
            if not isinstance(raw_slices, list) or not raw_slices:
                raise ContractValidationError(f"candidate_prescreen_workflow.yaml:{source_code}:query_slices must be a non-empty list")
            query_slice_ids = []
            for entry in raw_slices:
                if not isinstance(entry, dict):
                    raise ContractValidationError(f"candidate_prescreen_workflow.yaml:{source_code}:query_slices[] must be mappings")
                if entry.get("enabled") is True and isinstance(entry.get("query_slice_id"), str):
                    query_slice_ids.append(str(entry["query_slice_id"]))
            if not query_slice_ids:
                raise ContractValidationError(f"candidate_prescreen_workflow.yaml:{source_code}:query_slices has no enabled live slice")
        return cls(
            source_code=source_code,
            query_slice_ids=query_slice_ids,
            window_start=window_start,
            window_end=window_end,
        )

    def current_window(self) -> str:
        return f"{self.window_start.isoformat()}..{self.window_end.isoformat()}"

    def current_query_slice_id(self) -> str:
        return self.query_slice_ids[self.query_index]

    def advance(self) -> None:
        if len(self.query_slice_ids) > 1 and self.query_index < len(self.query_slice_ids) - 1:
            self.query_index += 1
            return
        self.query_index = 0
        window_span_days = (self.window_end - self.window_start).days
        next_start = self.window_end + timedelta(days=1)
        self.window_start = next_start
        self.window_end = next_start + timedelta(days=window_span_days)


def _parse_window(window: str) -> tuple[date, date]:
    try:
        start_text, end_text = window.split("..", 1)
        start = date.fromisoformat(start_text)
        end = date.fromisoformat(end_text)
    except ValueError as exc:
        raise ContractValidationError(f"window must look like YYYY-MM-DD..YYYY-MM-DD, got: {window}") from exc
    if end < start:
        raise ContractValidationError(f"window end must not be earlier than start: {window}")
    return start, end


def _default_initial_window() -> str:
    today = date.today()
    start = today - timedelta(days=6)
    return f"{start.isoformat()}..{today.isoformat()}"


def _current_date() -> date:
    return date.today()


def _compact_progress(progress: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_filled": progress["total_filled"],
        "total_slots": progress["total_slots"],
        "total_empty": progress["total_empty"],
        "is_complete": progress["is_complete"],
        "next_open_slot": progress["next_open_slot"],
        "documents": [
            {
                "staging_document_path": document["staging_document_path"],
                "filled_slots": document["filled_slots"],
                "empty_slots": document["empty_slots"],
                "next_empty_slot_id": document["empty_slot_ids"][0] if document["empty_slot_ids"] else None,
            }
            for document in progress["documents"]
        ],
    }


def _audit_log_path(config: AppConfig) -> Path:
    return config.candidate_workspace_dir / AUDIT_LOG_FILE_NAME


def _append_audit_log(config: AppConfig, payload: dict[str, Any]) -> None:
    audit_log_path = _audit_log_path(config)
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _is_retryable_error(error_type: str | None) -> bool:
    if not isinstance(error_type, str):
        return False
    return RETRY_POLICY.get(error_type, {}).get("retryable") is True


def _is_terminal_fill_error(error_type: str | None) -> bool:
    if not isinstance(error_type, str):
        return False
    return error_type in TERMINAL_FILL_ERROR_TYPES


def _parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_candidate_record(config: AppConfig, candidate_path: Path) -> dict[str, Any]:
    payload = load_yaml(candidate_path)
    if not isinstance(payload, dict):
        raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
    validate_candidate_record(config, payload)
    return payload


def _write_candidate_record(config: AppConfig, candidate_path: Path, record: dict[str, Any]) -> None:
    record["updated_at"] = utc_now_iso()
    validate_candidate_record(config, record)
    dump_yaml(candidate_path, record)


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


def _review_input_is_sufficient(record: dict[str, Any]) -> bool:
    if isinstance(record.get("summary"), str) and record["summary"].strip():
        return True
    if isinstance(record.get("raw_evidence_excerpt"), str) and record["raw_evidence_excerpt"].strip():
        return True
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict) or llm_prescreen.get("status") != "succeeded":
        return False
    evidence_summary = llm_prescreen.get("source_evidence_summary")
    evidence_anchors = llm_prescreen.get("evidence_anchors")
    return bool(evidence_summary) or bool(evidence_anchors)


def _repair_candidate_excerpt(record: dict[str, Any]) -> bool:
    original_excerpt = record.get("raw_evidence_excerpt")
    if not isinstance(original_excerpt, str):
        original_excerpt = ""
    repaired_excerpt = clean_raw_evidence_excerpt(original_excerpt)
    if not repaired_excerpt:
        summary = record.get("summary")
        if isinstance(summary, str) and summary.strip():
            repaired_excerpt = clean_raw_evidence_excerpt(summary)
    if repaired_excerpt and repaired_excerpt != original_excerpt:
        record["raw_evidence_excerpt"] = repaired_excerpt
        return True
    return False


def _relay_preflight_failure(
    exc: ConfigError | ProcessingError,
    *,
    failed_step: str,
) -> ProcessingError:
    return ProcessingError("relay_preflight_failed", f"{failed_step} failed before any LLM request was sent: {exc}")


def _blocked_handoff(blocking_items: list[str]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "staging_document_path": None,
        "sample_slot_id": None,
        "sample_id": None,
        "blocking_items": blocking_items,
        "last_attempted_at": utc_now_iso(),
    }


def _compose_human_review_notes(template_prefix: str, parts: list[str]) -> str:
    normalized_parts: list[str] = []
    for part in parts:
        text = " ".join(part.split())
        if text and text not in normalized_parts:
            normalized_parts.append(text)
    if not normalized_parts:
        return template_prefix
    return f"{template_prefix}; {' '.join(normalized_parts)}"


def _review_result_from_prescreen(review_card: dict[str, Any], *, review_source: str) -> dict[str, Any]:
    recommended_action = review_card.get("recommended_action")
    suggested_status = RECOMMENDED_ACTION_TO_REVIEW_STATUS.get(recommended_action)
    if suggested_status is None:
        return {
            "review_source": review_source,
            "suggested_review_status": "pending_first_pass",
            "note_template_key": None,
            "human_review_notes": None,
            "reason": "LLM review did not yield a supported recommended_action.",
            "boundary_notes": review_card.get("scope_boundary_note"),
            "evidence_sufficiency": None,
            "whitelist_reason": None,
        }

    template_key = REVIEW_STATUS_TO_TEMPLATE_KEY[suggested_status]
    reason = review_card.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        reason = review_card.get("decision_snapshot")
    boundary_notes = review_card.get("scope_boundary_note")
    assessment_hints = review_card.get("assessment_hints")
    evidence_sufficiency = None
    if isinstance(assessment_hints, dict) and isinstance(assessment_hints.get("evidence_strength"), str):
        evidence_sufficiency = assessment_hints.get("evidence_strength")

    whitelist_reason = None
    if recommended_action == "whitelist_candidate":
        whitelist_reason = "llm_first_pass_whitelist_candidate"

    return {
        "review_source": review_source,
        "suggested_review_status": suggested_status,
        "note_template_key": template_key,
        "human_review_notes": None,
        "reason": reason,
        "boundary_notes": boundary_notes,
        "evidence_sufficiency": evidence_sufficiency,
        "whitelist_reason": whitelist_reason,
    }


def _review_error_result(candidate_id: str, exc: ProcessingError | ContractValidationError) -> dict[str, Any]:
    error_type = exc.error_type if isinstance(exc, ProcessingError) else "schema_drift"
    return {
        "candidate_id": candidate_id,
        "suggested_review_status": "pending_first_pass",
        "reason": str(exc),
        "review_source": "llm_review_processing_error",
        "error_type": error_type,
    }


def _review_error_result_from_outcome(candidate_id: str, outcome: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "suggested_review_status": "pending_first_pass",
        "reason": str(outcome.get("failure_message") or outcome.get("failure_code") or "candidate prescreen failed"),
        "review_source": "llm_review_processing_error",
        "error_type": str(outcome.get("mapped_error_type") or "dependency_unavailable"),
        "failure_code": outcome.get("failure_code"),
        "llm_outcome": outcome,
    }


def _review_failure_result_from_record(record: dict[str, Any], *, review_source: str, include_error_type: bool) -> dict[str, Any]:
    llm_prescreen = record.get("llm_prescreen")
    error_type = llm_prescreen.get("error_type") if isinstance(llm_prescreen, dict) else None
    error_message = llm_prescreen.get("error_message") if isinstance(llm_prescreen, dict) else None
    result = {
        "candidate_id": record["candidate_id"],
        "suggested_review_status": "pending_first_pass",
        "reason": error_message or "candidate prescreen failed before human first-pass review could proceed",
        "review_source": review_source,
    }
    if include_error_type and isinstance(error_type, str):
        result["error_type"] = error_type
    return result


def _cooldown_remaining_seconds(record: dict[str, Any], cooldown_seconds: int) -> int:
    if cooldown_seconds <= 0:
        return 0
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict) or llm_prescreen.get("status") != "failed":
        return 0
    error_type = llm_prescreen.get("error_type")
    if not _is_retryable_error(error_type):
        return 0
    updated_at = _parse_iso_timestamp(record.get("updated_at"))
    if updated_at is None:
        return 0
    elapsed = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return max(0, int(cooldown_seconds - elapsed))


def _persist_review_failure(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
    exc: ProcessingError | ContractValidationError,
) -> None:
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        raise ContractValidationError(f"candidate prescreen record is missing llm_prescreen mapping: {candidate_path}")
    llm_prescreen["status"] = "failed"
    llm_prescreen["error_type"] = exc.error_type if isinstance(exc, ProcessingError) else "schema_drift"
    llm_prescreen["error_message"] = str(exc)
    _write_candidate_record(config, candidate_path, record)


def _persist_review_failure_outcome(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
    outcome: dict[str, Any],
) -> None:
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        raise ContractValidationError(f"candidate prescreen record is missing llm_prescreen mapping: {candidate_path}")
    llm_prescreen["status"] = "failed"
    llm_prescreen["error_type"] = outcome.get("mapped_error_type")
    llm_prescreen["error_message"] = str(outcome.get("failure_message") or outcome.get("failure_code") or "candidate prescreen failed")
    _write_candidate_record(config, candidate_path, record)


def _apply_successful_prescreen_snapshot(record: dict[str, Any], review_card: dict[str, Any]) -> None:
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict):
        raise ContractValidationError("candidate prescreen record is missing llm_prescreen mapping")
    llm_prescreen["status"] = "succeeded"
    llm_prescreen["in_observatory_scope"] = review_card["in_observatory_scope"]
    llm_prescreen["reason"] = review_card["reason"]
    llm_prescreen["decision_snapshot"] = review_card["decision_snapshot"]
    llm_prescreen["scope_boundary_note"] = review_card["scope_boundary_note"]
    llm_prescreen["source_evidence_summary"] = review_card["source_evidence_summary"]
    llm_prescreen["evidence_anchors"] = review_card["evidence_anchors"]
    llm_prescreen["review_focus_points"] = review_card["review_focus_points"]
    llm_prescreen["uncertainty_points"] = review_card["uncertainty_points"]
    llm_prescreen["recommend_candidate_pool"] = review_card["recommend_candidate_pool"]
    llm_prescreen["recommended_action"] = review_card["recommended_action"]
    llm_prescreen["confidence_summary"] = review_card["confidence_summary"]
    llm_prescreen["handoff_readiness_hint"] = review_card["handoff_readiness_hint"]
    llm_prescreen["persona_candidates"] = review_card["persona_candidates"]
    llm_prescreen["taxonomy_hints"] = review_card["taxonomy_hints"]
    llm_prescreen["assessment_hints"] = review_card["assessment_hints"]
    llm_prescreen["channel_metadata"] = review_card["channel_metadata"]
    llm_prescreen["error_type"] = None
    llm_prescreen["error_message"] = None


def _persist_successful_prescreen_snapshot(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
    review_card: dict[str, Any],
) -> None:
    _apply_successful_prescreen_snapshot(record, review_card)
    _write_candidate_record(config, candidate_path, record)


def review_candidate_with_llm(
    config: AppConfig,
    record: dict[str, Any],
    *,
    llm_fixture_path: Path | None,
    request_interval_seconds: int,
    retry_sleep_seconds: int,
    run_id: str | None = None,
) -> dict[str, Any]:
    existing = record.get("llm_prescreen")
    if isinstance(existing, dict) and existing.get("status") == "succeeded":
        # Reuse the recorded prescreen review card first so the fill loop does not
        # depend on a second relay round-trip for every pending candidate.
        return _review_result_from_prescreen(existing, review_source="existing_llm_prescreen")

    workflow_config = load_candidate_prescreen_config(config.config_dir)
    llm_defaults = workflow_config["llm_prescreen"]
    if llm_fixture_path is None:
        try:
            relay_preflight(
                default_timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
                default_client_version=str(llm_defaults["relay_client_version"]),
            )
        except (ConfigError, ProcessingError) as exc:
            raise _relay_preflight_failure(exc, failed_step="relay_preflight") from exc
    prompt_contract = candidate_prescreener_prompt_contract(
        prompt_spec_ref=str(llm_defaults.get("prompt_spec_ref") or ""),
    )
    try:
        review_outcome = screen_candidate(
            _candidate_input_from_record(record),
            prompt_version=str(llm_defaults["prompt_version"]),
            routing_version=str(llm_defaults["routing_version"]),
            relay_transport=str(llm_defaults["relay_transport"]),
            relay_client_version=str(llm_defaults["relay_client_version"]),
            prompt_contract=prompt_contract,
            fixture_path=llm_fixture_path,
            timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
            max_retries=int(llm_defaults["max_retries_default"]),
            request_interval_seconds=request_interval_seconds,
            retry_sleep_seconds=retry_sleep_seconds,
            run_id=run_id,
        )
    except (ConfigError, ContractValidationError, ProcessingError):
        if not isinstance(existing, dict) or existing.get("status") != "succeeded":
            raise
        return _review_result_from_prescreen(existing, review_source="existing_llm_prescreen_fallback")
    if not screen_candidate_outcome_succeeded(review_outcome):
        return _review_error_result_from_outcome(record["candidate_id"], review_outcome)
    review_result = _review_result_from_prescreen(review_outcome["normalized_result"], review_source="fresh_llm_review")
    review_result["llm_review_card"] = review_outcome["normalized_result"]
    review_result["llm_outcome"] = review_outcome
    return review_result


def _apply_review_decision(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
    review_result: dict[str, Any],
    *,
    note_templates: dict[str, str],
) -> dict[str, Any]:
    suggested_status = review_result["suggested_review_status"]
    if suggested_status == "pending_first_pass":
        record["staging_handoff"] = _blocked_handoff(
            [
                "candidate evidence remains insufficient for a constrained first-pass approval",
            ]
        )
        _write_candidate_record(config, candidate_path, record)
        return review_result

    template_key = str(review_result["note_template_key"])
    template_prefix = str(note_templates[template_key])
    record["human_review_status"] = suggested_status
    record["human_review_note_template_key"] = template_key
    record["human_review_notes"] = _compose_human_review_notes(
        template_prefix,
        [
            str(review_result["reason"]) if review_result.get("reason") else "",
            str(review_result["boundary_notes"]) if review_result.get("boundary_notes") else "",
            f"evidence_strength={review_result['evidence_sufficiency']}" if review_result.get("evidence_sufficiency") else "",
            f"review_source={review_result['review_source']}",
        ],
    )
    record["human_reviewed_at"] = utc_now_iso()
    if review_result.get("whitelist_reason") and not record.get("whitelist_reason"):
        record["whitelist_reason"] = review_result["whitelist_reason"]
    if suggested_status == "approved_for_staging":
        record["staging_handoff"] = {
            "status": "not_started",
            "staging_document_path": None,
            "sample_slot_id": None,
            "sample_id": None,
            "blocking_items": [],
            "last_attempted_at": utc_now_iso(),
        }
    else:
        record["staging_handoff"] = _blocked_handoff(
            [
                f"candidate first-pass review resolved to {suggested_status}",
            ]
        )
    _write_candidate_record(config, candidate_path, record)
    review_result["human_review_notes"] = record["human_review_notes"]
    return review_result


def _handoff_candidate(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    try:
        staging_document_path, slot_id = handoff_candidate_to_staging(
            record,
            candidate_path=candidate_path,
            staging_dir=config.gold_set_staging_dir,
        )
    except ContractValidationError as exc:
        if "Semantic duplicate source URL already present in staging" not in str(exc):
            raise
        record["staging_handoff"] = _blocked_handoff([str(exc)])
        _write_candidate_record(config, candidate_path, record)
        return {
            "status": "blocked",
            "candidate_id": record["candidate_id"],
            "sample_id": None,
            "staging_document_path": None,
            "sample_slot_id": None,
            "blocking_items": list(record["staging_handoff"]["blocking_items"]),
        }
    record["staging_handoff"] = {
        "status": "written",
        "staging_document_path": staging_document_path,
        "sample_slot_id": slot_id,
        "sample_id": record["candidate_id"],
        "blocking_items": [],
        "last_attempted_at": utc_now_iso(),
    }
    _write_candidate_record(config, candidate_path, record)
    return {
        "status": "written",
        "candidate_id": record["candidate_id"],
        "sample_id": record["candidate_id"],
        "staging_document_path": staging_document_path,
        "sample_slot_id": slot_id,
    }


def _scan_workspace_candidates(config: AppConfig) -> list[tuple[Path, dict[str, Any]]]:
    preferred_by_key: dict[tuple[str, str], tuple[Path, dict[str, Any]]] = {}
    for candidate_path in candidate_record_paths(config):
        record = _load_candidate_record(config, candidate_path)
        semantic_key = semantic_candidate_key_from_record(record)
        existing = preferred_by_key.get(semantic_key)
        if existing is None or candidate_record_preference_key(record, candidate_path) > candidate_record_preference_key(
            existing[1],
            existing[0],
        ):
            preferred_by_key[semantic_key] = (candidate_path, record)
    return sorted(preferred_by_key.values(), key=lambda item: str(item[0]))


def _future_window_failure(cursor: LiveDiscoveryCursor) -> dict[str, Any]:
    today = _current_date()
    return {
        "failed_step": "live_window_cursor",
        "error_type": "future_window_exhausted",
        "reason": (
            "Live discovery cursor advanced into a window that extends beyond the current date "
            f"({cursor.current_window()} while today is {today.isoformat()}); "
            "stopping instead of scanning empty future windows."
        ),
        "safe_to_retry": False,
    }


def _terminal_review_failure_from_record(
    record: dict[str, Any],
    *,
    review_source: str = "terminal_prescreen_failure",
) -> dict[str, Any] | None:
    llm_prescreen = record.get("llm_prescreen")
    if not isinstance(llm_prescreen, dict) or llm_prescreen.get("status") != "failed":
        return None
    error_type = llm_prescreen.get("error_type")
    if not _is_terminal_fill_error(error_type):
        return None
    return _review_failure_result_from_record(
        record,
        review_source=review_source,
        include_error_type=True,
    )


def _terminal_review_failure_payload(
    review_results: list[dict[str, Any]],
    *,
    live_candidate_ids: set[str] | None = None,
) -> dict[str, Any] | None:
    live_ids = live_candidate_ids or set()
    for result in review_results:
        error_type = result.get("error_type")
        if not _is_terminal_fill_error(error_type):
            continue
        candidate_id = str(result.get("candidate_id") or "candidate_llm_review")
        failed_step = "live_candidate_llm_review" if candidate_id in live_ids else "existing_workspace_llm_review"
        return {
            "failed_step": failed_step,
            "error_type": str(error_type),
            "failure_code": result.get("failure_code"),
            "reason": str(result.get("reason") or ""),
            "candidate_id": candidate_id,
            "safe_to_retry": False,
        }
    return None


def _try_handoff_existing_approved_candidate(
    config: AppConfig,
    candidate_path: Path,
    record: dict[str, Any],
) -> dict[str, Any] | None:
    if record.get("human_review_status") != "approved_for_staging":
        return None
    staging_handoff = record.get("staging_handoff")
    if isinstance(staging_handoff, dict) and staging_handoff.get("status") == "written":
        return None
    handoff_result = _handoff_candidate(config, candidate_path, record)
    if handoff_result["status"] == "blocked":
        return None
    return handoff_result


def _process_existing_workspace_candidates(
    config: AppConfig,
    *,
    llm_fixture_path: Path | None,
    note_templates: dict[str, str],
    request_interval_seconds: int,
    retry_sleep_seconds: int,
    run_id: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    review_results: list[dict[str, Any]] = []
    for candidate_path, record in _scan_workspace_candidates(config):
        handoff_result = _try_handoff_existing_approved_candidate(config, candidate_path, record)
        if handoff_result is not None:
            return review_results, handoff_result

    for candidate_path, record in _scan_workspace_candidates(config):
        if record.get("human_review_status") != "pending_first_pass":
            continue
        staging_handoff = record.get("staging_handoff")
        if isinstance(staging_handoff, dict) and staging_handoff.get("status") == "blocked":
            continue

        repaired = _repair_candidate_excerpt(record)
        if repaired:
            _write_candidate_record(config, candidate_path, record)

        terminal_failure = _terminal_review_failure_from_record(record)
        if terminal_failure is not None:
            review_results.append(terminal_failure)
            return review_results, None

        if not _review_input_is_sufficient(record):
            review_result = {
                "candidate_id": record["candidate_id"],
                "suggested_review_status": "pending_first_pass",
                "reason": "candidate summary/raw_evidence_excerpt remain insufficient for constrained first-pass review",
                "review_source": "insufficient_evidence",
            }
            review_results.append(review_result)
            continue

        cooldown_remaining = _cooldown_remaining_seconds(record, retry_sleep_seconds)
        if cooldown_remaining > 0:
            review_results.append(
                _review_failure_result_from_record(
                    record,
                    review_source="retry_cooldown",
                    include_error_type=False,
                )
            )
            continue

        try:
            review_result = review_candidate_with_llm(
                config,
                record,
                llm_fixture_path=llm_fixture_path,
                request_interval_seconds=request_interval_seconds,
                retry_sleep_seconds=retry_sleep_seconds,
                run_id=run_id,
            )
        except (ProcessingError, ContractValidationError) as exc:
            _persist_review_failure(config, candidate_path, record, exc)
            error_result = _review_error_result(record["candidate_id"], exc)
            review_results.append(error_result)
            if _is_terminal_fill_error(error_result.get("error_type")):
                return review_results, None
            continue
        review_result["candidate_id"] = record["candidate_id"]
        review_outcome = review_result.get("llm_outcome")
        if isinstance(review_outcome, dict) and not screen_candidate_outcome_succeeded(review_outcome):
            _persist_review_failure_outcome(config, candidate_path, record, review_outcome)
            review_results.append(review_result)
            if _is_terminal_fill_error(review_result.get("error_type")):
                return review_results, None
            continue
        if review_result.get("review_source") == "fresh_llm_review":
            review_card = review_result.get("llm_review_card")
            if not isinstance(review_card, dict):
                raise ContractValidationError("fresh_llm_review must provide llm_review_card before review derivation")
            _persist_successful_prescreen_snapshot(config, candidate_path, record, review_card)
            record = _load_candidate_record(config, candidate_path)
        review_results.append(
            _apply_review_decision(
                config,
                candidate_path,
                record,
                review_result,
                note_templates=note_templates,
            )
        )
        if review_result["suggested_review_status"] == "approved_for_staging":
            refreshed_record = _load_candidate_record(config, candidate_path)
            handoff_result = _handoff_candidate(config, candidate_path, refreshed_record)
            if handoff_result["status"] == "blocked":
                continue
            return review_results, handoff_result
    return review_results, None


def _process_live_candidates(
    config: AppConfig,
    *,
    cursor: LiveDiscoveryCursor,
    live_limit: int,
    discovery_fixture_path: Path | None,
    llm_fixture_path: Path | None,
    note_templates: dict[str, str],
    discovery_request_interval_seconds: int,
    request_interval_seconds: int,
    retry_sleep_seconds: int,
    run_id: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
    current_window = cursor.current_window()
    current_slice_id = cursor.current_query_slice_id()
    live_summary: dict[str, Any] = {
        "source": cursor.source_code,
        "window": current_window,
        "query_slice_id": current_slice_id,
        "limit": live_limit,
        "new_candidate_document_paths": [],
        "new_candidate_ids": [],
    }
    if discovery_fixture_path is None and cursor.window_end > _current_date():
        live_summary["failure"] = _future_window_failure(cursor)
        return live_summary, [], None

    workflow_config = load_candidate_prescreen_config(config.config_dir)
    llm_defaults = workflow_config["llm_prescreen"]
    if llm_fixture_path is None:
        try:
            relay_status = relay_preflight(
                default_timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
                default_client_version=str(llm_defaults["relay_client_version"]),
            )
        except (ConfigError, ProcessingError) as exc:
            live_summary["failure"] = {
                "failed_step": "relay_preflight",
                "error_type": "relay_preflight_failed",
                "reason": str(exc),
                "safe_to_retry": False,
            }
            return live_summary, [], None
        live_summary["relay_preflight"] = relay_status

    try:
        written_paths = run_candidate_prescreen(
            config,
            source_code=cursor.source_code,
            window=current_window,
            query_slice_id=current_slice_id,
            limit=live_limit,
            discovery_fixture_path=discovery_fixture_path,
            llm_fixture_path=llm_fixture_path,
            discovery_request_interval_seconds=discovery_request_interval_seconds,
            request_interval_seconds=request_interval_seconds,
            retry_sleep_seconds=retry_sleep_seconds,
            run_id=run_id,
        )
    except ProcessingError as exc:
        live_summary["failure"] = {
            "failed_step": "run_candidate_prescreen",
            "error_type": exc.error_type,
            "reason": str(exc),
            "safe_to_retry": _is_retryable_error(exc.error_type),
        }
        cursor.advance()
        return live_summary, [], None
    live_summary["new_candidate_document_paths"] = [str(path) for path in written_paths]

    review_results: list[dict[str, Any]] = []
    for candidate_path in written_paths:
        record = _load_candidate_record(config, candidate_path)
        live_summary["new_candidate_ids"].append(record["candidate_id"])
        repaired = _repair_candidate_excerpt(record)
        if repaired:
            _write_candidate_record(config, candidate_path, record)
        terminal_failure = _terminal_review_failure_from_record(record)
        if terminal_failure is not None:
            review_results.append(terminal_failure)
            return live_summary, review_results, None
        if not _review_input_is_sufficient(record):
            review_results.append(
                {
                    "candidate_id": record["candidate_id"],
                    "suggested_review_status": "pending_first_pass",
                    "reason": "candidate summary/raw_evidence_excerpt remain insufficient for constrained first-pass review",
                    "review_source": "insufficient_evidence",
                }
            )
            continue
        cooldown_remaining = _cooldown_remaining_seconds(record, retry_sleep_seconds)
        if cooldown_remaining > 0:
            review_results.append(
                _review_failure_result_from_record(
                    record,
                    review_source="recent_prescreen_failure",
                    include_error_type=True,
                )
            )
            continue
        try:
            review_result = review_candidate_with_llm(
                config,
                record,
                llm_fixture_path=llm_fixture_path,
                request_interval_seconds=request_interval_seconds,
                retry_sleep_seconds=retry_sleep_seconds,
                run_id=run_id,
            )
        except (ProcessingError, ContractValidationError) as exc:
            _persist_review_failure(config, candidate_path, record, exc)
            error_result = _review_error_result(record["candidate_id"], exc)
            review_results.append(error_result)
            if _is_terminal_fill_error(error_result.get("error_type")):
                return live_summary, review_results, None
            continue
        review_result["candidate_id"] = record["candidate_id"]
        review_outcome = review_result.get("llm_outcome")
        if isinstance(review_outcome, dict) and not screen_candidate_outcome_succeeded(review_outcome):
            _persist_review_failure_outcome(config, candidate_path, record, review_outcome)
            review_results.append(review_result)
            if _is_terminal_fill_error(review_result.get("error_type")):
                return live_summary, review_results, None
            continue
        if review_result.get("review_source") == "fresh_llm_review":
            review_card = review_result.get("llm_review_card")
            if not isinstance(review_card, dict):
                raise ContractValidationError("fresh_llm_review must provide llm_review_card before review derivation")
            _persist_successful_prescreen_snapshot(config, candidate_path, record, review_card)
            record = _load_candidate_record(config, candidate_path)
        review_results.append(
            _apply_review_decision(
                config,
                candidate_path,
                record,
                review_result,
                note_templates=note_templates,
            )
        )
        if review_result["suggested_review_status"] == "approved_for_staging":
            refreshed_record = _load_candidate_record(config, candidate_path)
            handoff_result = _handoff_candidate(config, candidate_path, refreshed_record)
            if handoff_result["status"] == "blocked":
                continue
            cursor.advance()
            return live_summary, review_results, handoff_result
    cursor.advance()
    return live_summary, review_results, None


def _default_source_code(workflow_config: dict[str, Any]) -> str:
    boundary = workflow_config.get("execution_boundary")
    if isinstance(boundary, dict) and isinstance(boundary.get("current_phase_default_live_source"), str):
        return str(boundary["current_phase_default_live_source"])
    return DEFAULT_SOURCE_CODE


def run_one_fill_iteration(
    config: AppConfig,
    *,
    cursor: LiveDiscoveryCursor,
    live_limit: int = DEFAULT_LIVE_LIMIT,
    discovery_fixture_path: Path | None = None,
    llm_fixture_path: Path | None = None,
    discovery_request_interval_seconds: int = 0,
    request_interval_seconds: int = 0,
    retry_sleep_seconds: int = 0,
    run_id: str | None = None,
) -> dict[str, Any]:
    if live_limit < 1 or live_limit > MAX_LIVE_LIMIT:
        raise ContractValidationError(f"live_limit must be between 1 and {MAX_LIVE_LIMIT}")

    workflow_config = load_candidate_prescreen_config(config.config_dir)
    workspace_config = workflow_config.get("workspace")
    if not isinstance(workspace_config, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml:workspace must be a mapping")
    note_templates = workspace_config.get("human_review_note_templates")
    if not isinstance(note_templates, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml:workspace:human_review_note_templates must be a mapping")

    cleanup_summary = archive_future_window_candidate_records(config, today=_current_date())

    progress_before = validate_staging_workspace(config.gold_set_staging_dir)
    if progress_before["is_complete"]:
        return {
            "iteration_completed_at": utc_now_iso(),
            "progress_before": _compact_progress(progress_before),
            "progress_after": _compact_progress(progress_before),
            "workspace_candidate_source": [],
            "review_results": [],
            "handoff": None,
            "live_discovery": None,
            "workspace_cleanup": cleanup_summary,
        }

    review_results, handoff_result = _process_existing_workspace_candidates(
        config,
        llm_fixture_path=llm_fixture_path,
        note_templates=note_templates,
        request_interval_seconds=request_interval_seconds,
        retry_sleep_seconds=retry_sleep_seconds,
        run_id=run_id,
    )
    live_discovery: dict[str, Any] | None = None
    terminal_review_failure = _terminal_review_failure_payload(review_results)
    if handoff_result is None and terminal_review_failure is not None:
        live_discovery = {"failure": terminal_review_failure}
    if handoff_result is None and terminal_review_failure is None:
        live_discovery, live_review_results, handoff_result = _process_live_candidates(
            config,
            cursor=cursor,
            live_limit=live_limit,
            discovery_fixture_path=discovery_fixture_path,
            llm_fixture_path=llm_fixture_path,
            note_templates=note_templates,
            discovery_request_interval_seconds=discovery_request_interval_seconds,
            request_interval_seconds=request_interval_seconds,
            retry_sleep_seconds=retry_sleep_seconds,
            run_id=run_id,
        )
        review_results.extend(live_review_results)
        if handoff_result is None and isinstance(live_discovery, dict) and not isinstance(live_discovery.get("failure"), dict):
            terminal_review_failure = _terminal_review_failure_payload(
                live_review_results,
                live_candidate_ids=set(live_discovery.get("new_candidate_ids") or []),
            )
            if terminal_review_failure is not None:
                live_discovery["failure"] = terminal_review_failure

    candidate_workspace_count = validate_candidate_workspace(config)
    progress_after = validate_staging_workspace(config.gold_set_staging_dir)
    return {
        "iteration_completed_at": utc_now_iso(),
        "progress_before": _compact_progress(progress_before),
        "progress_after": _compact_progress(progress_after),
        "workspace_candidate_source": [
            {
                "candidate_source": "existing_workspace",
                "candidate_id": result["candidate_id"],
                "review_status": result["suggested_review_status"],
                "reason": result.get("reason"),
                "review_source": result.get("review_source"),
                "error_type": result.get("error_type"),
            }
            for result in review_results
            if result["candidate_id"] not in (live_discovery or {}).get("new_candidate_ids", [])
        ],
        "review_results": [
            {
                "candidate_id": result["candidate_id"],
                "review_status": result["suggested_review_status"],
                "reason": result.get("reason"),
                "review_source": result.get("review_source"),
                "error_type": result.get("error_type"),
            }
            for result in review_results
        ],
        "handoff": handoff_result,
        "live_discovery": live_discovery,
        "workspace_cleanup": cleanup_summary,
        "validation": {
            "candidate_workspace_document_count": candidate_workspace_count,
            "staging_total_filled": progress_after["total_filled"],
        },
    }


def _collect_iteration_retryable_failures(summary: dict[str, Any]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    live_discovery = summary.get("live_discovery")
    if isinstance(live_discovery, dict):
        failure = live_discovery.get("failure")
        if isinstance(failure, dict) and _is_retryable_error(failure.get("error_type")):
            failures.append(
                {
                    "scope": "live_discovery",
                    "error_type": str(failure["error_type"]),
                    "reason": str(failure.get("reason") or ""),
                }
            )
    review_results = summary.get("review_results")
    if isinstance(review_results, list):
        for result in review_results:
            if not isinstance(result, dict):
                continue
            error_type = result.get("error_type")
            if _is_retryable_error(error_type):
                failures.append(
                    {
                        "scope": str(result.get("candidate_id") or "candidate_review"),
                        "error_type": str(error_type),
                        "reason": str(result.get("reason") or ""),
                    }
                )
    return failures


def _terminal_iteration_failure(summary: dict[str, Any]) -> dict[str, str] | None:
    live_discovery = summary.get("live_discovery")
    if not isinstance(live_discovery, dict):
        return None
    failure = live_discovery.get("failure")
    if not isinstance(failure, dict):
        return None
    error_type = failure.get("error_type")
    if not _is_terminal_fill_error(error_type):
        return None
    return {
        "error_type": str(error_type),
        "reason": str(failure.get("reason") or ""),
        "failed_step": str(failure.get("failed_step") or "run_candidate_prescreen"),
    }


def _wait_with_audit(
    config: AppConfig,
    logger: Any,
    *,
    run_id: str,
    iteration: int,
    wait_kind: str,
    wait_seconds: int,
    reason: str,
    sleep_fn: Callable[[float], None],
) -> None:
    if wait_seconds <= 0:
        return
    wait_entry = {
        "event": "wait",
        "run_id": run_id,
        "iteration": iteration,
        "recorded_at": utc_now_iso(),
        "wait_kind": wait_kind,
        "wait_seconds": wait_seconds,
        "reason": reason,
    }
    _append_audit_log(config, wait_entry)
    logger.info(json.dumps(wait_entry, ensure_ascii=True))
    sleep_fn(wait_seconds)


def _reconcile_unfinished_run(config: AppConfig, logger: Any) -> None:
    audit_log_path = _audit_log_path(config)
    if not audit_log_path.exists():
        return
    latest_run_id: str | None = None
    latest_run_terminal = False
    for raw_line in reversed(audit_log_path.read_text(encoding="utf-8").splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            continue
        latest_run_id = run_id
        latest_run_terminal = payload.get("event") in TERMINAL_AUDIT_EVENTS
        break
    if latest_run_id is None or latest_run_terminal:
        return
    interrupted_entry = {
        "event": "interrupted_assumed",
        "run_id": latest_run_id,
        "recorded_at": utc_now_iso(),
        "resolution_status": "interrupted_assumed",
        "reason": "a newer fill run started before this run reached a terminal audit event",
    }
    _append_audit_log(config, interrupted_entry)
    logger.info(json.dumps(interrupted_entry, ensure_ascii=True))


def fill_gold_set_staging_until_complete(
    config: AppConfig,
    *,
    source_code: str | None = None,
    initial_window: str | None = None,
    query_slice_id: str | None = None,
    live_limit: int = DEFAULT_LIVE_LIMIT,
    discovery_fixture_path: Path | None = None,
    llm_fixture_path: Path | None = None,
    max_iterations: int | None = None,
    discovery_request_interval_seconds: int | None = None,
    provider_request_interval_seconds: int | None = None,
    retry_sleep_seconds: int | None = None,
    sleep_fn: Callable[[float], None] = sleep,
) -> dict[str, Any]:
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    effective_source_code = source_code or _default_source_code(workflow_config)
    resolved_discovery_request_interval_seconds = resolve_discovery_request_interval_seconds(discovery_request_interval_seconds)
    resolved_request_interval_seconds = resolve_request_interval_seconds(provider_request_interval_seconds)
    resolved_retry_sleep_seconds = resolve_retry_sleep_seconds(retry_sleep_seconds)
    cursor = LiveDiscoveryCursor.from_workflow(
        workflow_config,
        source_code=effective_source_code,
        initial_window=initial_window,
        query_slice_id=query_slice_id,
    )
    logger = get_logger(
        "fill_gold_set_staging_until_complete",
        source_id=f"src_{effective_source_code}",
        task_id="fill_gold_set_staging_until_complete",
        resolution_status="running",
    )
    _reconcile_unfinished_run(config, logger)
    run_id = f"fill_run_{utc_now_iso()}"
    run_logger = get_logger(
        "fill_gold_set_staging_until_complete",
        source_id=f"src_{effective_source_code}",
        task_id="fill_gold_set_staging_until_complete",
        resolution_status="running",
        run_id=run_id,
    )

    initial_progress = validate_staging_workspace(config.gold_set_staging_dir)
    initial_entry = {
        "event": "initialize",
        "run_id": run_id,
        "recorded_at": utc_now_iso(),
        "source_code": effective_source_code,
        "initial_window": cursor.current_window(),
        "initial_query_slice_id": cursor.current_query_slice_id(),
        "progress": _compact_progress(initial_progress),
        "audit_log_path": str(_audit_log_path(config)),
        "discovery_request_interval_seconds": resolved_discovery_request_interval_seconds,
        "provider_request_interval_seconds": resolved_request_interval_seconds,
        "retry_sleep_seconds": resolved_retry_sleep_seconds,
    }
    _append_audit_log(config, initial_entry)
    run_logger.info(json.dumps(initial_entry, ensure_ascii=True))
    if initial_progress["is_complete"]:
        completed_entry = {
            "event": "completed",
            "run_id": run_id,
            "recorded_at": utc_now_iso(),
            "iterations": 0,
            "progress": _compact_progress(initial_progress),
        }
        _append_audit_log(config, completed_entry)
        run_logger.info(json.dumps(completed_entry, ensure_ascii=True))
        return {
            "status": "completed",
            "iterations": 0,
            "total_filled": initial_progress["total_filled"],
            "audit_log_path": str(_audit_log_path(config)),
        }

    iteration = 0
    latest_progress = initial_progress
    while not latest_progress["is_complete"]:
        if max_iterations is not None and iteration >= max_iterations:
            max_iterations_entry = {
                "event": "max_iterations_reached",
                "run_id": run_id,
                "recorded_at": utc_now_iso(),
                "iterations": iteration,
                "progress": _compact_progress(latest_progress),
            }
            _append_audit_log(config, max_iterations_entry)
            run_logger.info(json.dumps(max_iterations_entry, ensure_ascii=True))
            return {
                "status": "max_iterations_reached",
                "iterations": iteration,
                "total_filled": latest_progress["total_filled"],
                "audit_log_path": str(_audit_log_path(config)),
            }

        iteration += 1
        summary = run_one_fill_iteration(
            config,
            cursor=cursor,
            live_limit=live_limit,
            discovery_fixture_path=discovery_fixture_path,
            llm_fixture_path=llm_fixture_path,
            discovery_request_interval_seconds=resolved_discovery_request_interval_seconds,
            request_interval_seconds=resolved_request_interval_seconds,
            retry_sleep_seconds=resolved_retry_sleep_seconds,
            run_id=run_id,
        )
        audit_entry = {
            "event": "iteration",
            "run_id": run_id,
            "iteration": iteration,
            "recorded_at": utc_now_iso(),
            **summary,
        }
        _append_audit_log(config, audit_entry)
        run_logger.info(json.dumps(audit_entry, ensure_ascii=True))
        latest_progress = staging_progress(config.gold_set_staging_dir)
        terminal_failure = _terminal_iteration_failure(summary)
        if terminal_failure is not None and summary["handoff"] is None:
            blocked_entry = {
                "event": "blocked",
                "run_id": run_id,
                "iteration": iteration,
                "recorded_at": utc_now_iso(),
                "resolution_status": "blocked",
                **terminal_failure,
            }
            _append_audit_log(config, blocked_entry)
            run_logger.info(json.dumps(blocked_entry, ensure_ascii=True))
            return {
                "status": "blocked",
                "iterations": iteration,
                "total_filled": latest_progress["total_filled"],
                "audit_log_path": str(_audit_log_path(config)),
                "blocked_reason": terminal_failure["reason"],
                "blocked_error_type": terminal_failure["error_type"],
            }
        retryable_failures = _collect_iteration_retryable_failures(summary)
        if retryable_failures and not latest_progress["is_complete"]:
            failure_reason = "; ".join(
                f"{failure['scope']}:{failure['error_type']}"
                for failure in retryable_failures
            )
            _wait_with_audit(
                config,
                run_logger,
                run_id=run_id,
                iteration=iteration,
                wait_kind="failure_backoff",
                wait_seconds=resolved_retry_sleep_seconds,
                reason=f"retryable failure before next iteration: {failure_reason}",
                sleep_fn=sleep_fn,
            )
        if summary["handoff"] is None and latest_progress["total_filled"] >= EXPECTED_TOTAL_SLOTS:
            latest_progress = validate_staging_workspace(config.gold_set_staging_dir)

    completed_entry = {
        "event": "completed",
        "run_id": run_id,
        "recorded_at": utc_now_iso(),
        "iterations": iteration,
        "progress": _compact_progress(latest_progress),
    }
    _append_audit_log(config, completed_entry)
    run_logger.info(json.dumps(completed_entry, ensure_ascii=True))
    return {
        "status": "completed",
        "iterations": iteration,
        "total_filled": latest_progress["total_filled"],
        "audit_log_path": str(_audit_log_path(config)),
    }
