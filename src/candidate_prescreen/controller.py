"""Durable loop that keeps filling staging until the external carrier is full."""

from __future__ import annotations

import json
import random
import time
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.candidate_prescreen.config import load_candidate_prescreen_config, source_config
from src.candidate_prescreen.relay import clean_raw_evidence_excerpt, relay_min_request_interval_seconds
from src.candidate_prescreen.reviewer import CandidateReviewDecision, review_candidate_with_llm
from src.candidate_prescreen.staging import (
    StagingProgress,
    handoff_candidate_to_staging,
    summarize_staging_progress,
    validate_staging_handoff,
)
from src.candidate_prescreen.workflow import (
    run_candidate_prescreen,
    validate_candidate_record,
    validate_candidate_workspace,
)
from src.common.config import AppConfig
from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import dump_json, dump_yaml, ensure_parent, load_yaml, utc_now_iso

AUDIT_LOG_NAME = "fill_gold_set_staging_until_complete.jsonl"
CURSOR_FILE_NAME = "fill_gold_set_staging_until_complete.cursor.json"
RETRYABLE_ERROR_TYPES = {
    "api_429",
    "timeout",
    "provider_timeout",
    "network_error",
    "dependency_unavailable",
    "storage_write_failed",
}


@dataclass(frozen=True)
class FillControllerOptions:
    source_code: str = "github"
    initial_window: str | None = None
    live_limit: int = 1
    discovery_fixture_path: Path | None = None
    llm_fixture_path: Path | None = None
    review_fixture_path: Path | None = None
    max_iterations: int | None = None
    target_total_filled: int = 300
    target_file_count: int = 20
    target_slots_per_file: int = 15
    sleep_base_seconds: int = 30
    sleep_max_seconds: int = 1800


@dataclass(frozen=True)
class FillLoopResult:
    iterations: int
    total_filled: int
    target_total_filled: int
    audit_log_path: str
    cursor_path: str


def _audit_dir(config: AppConfig) -> Path:
    return config.candidate_workspace_dir / "audit"


def _audit_log_path(config: AppConfig) -> Path:
    return _audit_dir(config) / AUDIT_LOG_NAME


def _cursor_path(config: AppConfig) -> Path:
    return _audit_dir(config) / CURSOR_FILE_NAME


def _append_audit_log(config: AppConfig, payload: dict[str, Any]) -> None:
    path = _audit_log_path(config)
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def _print_iteration_summary(payload: dict[str, Any]) -> None:
    phase = payload.get("phase", "iteration")
    iteration = payload.get("iteration")
    before = payload.get("staging_progress_before", {})
    after = payload.get("staging_progress_after", before)
    message = (
        f"[{phase}] iteration={iteration} filled_before={before.get('total_filled')}/{before.get('target_total_slots')} "
        f"filled_after={after.get('total_filled')}/{after.get('target_total_slots')}"
    )
    next_slot = before.get("next_empty_slot")
    if isinstance(next_slot, dict):
        message += f" next_slot={next_slot.get('sample_slot_id')}"
    handoffs = payload.get("handoff_results")
    if isinstance(handoffs, list) and handoffs:
        first = handoffs[0]
        message += f" wrote={first.get('candidate_id')}->{first.get('sample_slot_id')}"
    elif payload.get("failure"):
        failure = payload["failure"]
        message += f" failure_step={failure.get('step')} retryable={failure.get('retryable')}"
    print(message)


def _formal_gold_set_sample_count(gold_set_dir: Path) -> int:
    sample_root = gold_set_dir / "gold_set_300"
    if not sample_root.exists():
        return 0
    return len([path for path in sample_root.iterdir() if path.is_dir()])


def _parse_window(window: str) -> tuple[date, date]:
    start_text, end_text = window.split("..", 1)
    return date.fromisoformat(start_text), date.fromisoformat(end_text)


def _window_text(start: date, end: date) -> str:
    return f"{start.isoformat()}..{end.isoformat()}"


def _step_window_back(window: str) -> str:
    start, end = _parse_window(window)
    width_days = max(1, (end - start).days)
    next_end = start - timedelta(days=1)
    next_start = next_end - timedelta(days=width_days)
    return _window_text(next_start, next_end)


def _discover_existing_windows(config: AppConfig, source_code: str) -> list[str]:
    source_root = config.candidate_workspace_dir / source_code
    if not source_root.exists():
        return []
    windows: list[str] = []
    for path in sorted(source_root.iterdir()):
        if not path.is_dir():
            continue
        window = path.name.replace("_", "..", 1) if ".." not in path.name else path.name
        # The workspace uses YYYY-MM-DD_YYYY-MM-DD, so map it back carefully.
        parts = path.name.split("_")
        if len(parts) == 2:
            window = f"{parts[0]}..{parts[1]}"
        windows.append(window)
    return windows


def _default_initial_window(config: AppConfig, source_code: str) -> str:
    windows = _discover_existing_windows(config, source_code)
    if windows:
        return sorted(windows)[-1]
    today = date.today()
    return _window_text(today - timedelta(days=7), today)


def _query_slice_ids(workflow_config: dict[str, Any], source_code: str) -> list[str]:
    source = source_config(workflow_config, source_code)
    slices = source.get("query_slices")
    if not isinstance(slices, list) or not slices:
        raise ContractValidationError(f"candidate_prescreen_workflow.yaml is missing query_slices for {source_code}")
    query_ids = [str(entry.get("query_slice_id")) for entry in slices if isinstance(entry, dict) and entry.get("enabled") is not False]
    if not query_ids:
        raise ContractValidationError(f"candidate_prescreen_workflow.yaml has no enabled query_slice_id for {source_code}")
    return query_ids


def _load_cursor(config: AppConfig, *, source_code: str, initial_window: str, query_slice_ids: list[str]) -> dict[str, Any]:
    path = _cursor_path(config)
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("source_code") == source_code:
            return raw
    cursor = {
        "source_code": source_code,
        "current_window": initial_window,
        "next_query_index": 0,
        "query_slice_ids": query_slice_ids,
        "live_runs": 0,
        "updated_at": utc_now_iso(),
    }
    dump_json(path, cursor)
    return cursor


def _save_cursor(config: AppConfig, cursor: dict[str, Any]) -> None:
    cursor["updated_at"] = utc_now_iso()
    dump_json(_cursor_path(config), cursor)


def _next_live_request(cursor: dict[str, Any]) -> tuple[str, str]:
    query_slice_ids = cursor.get("query_slice_ids")
    if not isinstance(query_slice_ids, list) or not query_slice_ids:
        raise ContractValidationError("Live discovery cursor lost query_slice_ids")
    index = int(cursor.get("next_query_index", 0))
    query_slice_id = str(query_slice_ids[index % len(query_slice_ids)])
    window = str(cursor["current_window"])
    next_index = (index + 1) % len(query_slice_ids)
    cursor["next_query_index"] = next_index
    if next_index == 0:
        cursor["current_window"] = _step_window_back(window)
    cursor["live_runs"] = int(cursor.get("live_runs", 0)) + 1
    return window, query_slice_id


def _retry_delay_seconds(error_type: str, attempt: int, options: FillControllerOptions) -> float:
    if error_type not in RETRYABLE_ERROR_TYPES:
        return 0.0
    delay = min(options.sleep_base_seconds * (2**attempt), options.sleep_max_seconds)
    return float(delay + random.uniform(0, 1))


def _staging_progress_payload(progress: StagingProgress) -> dict[str, Any]:
    return {
        "total_filled": progress.total_filled,
        "total_slots": progress.total_slots,
        "target_total_slots": progress.target_total_slots,
        "file_count": progress.file_count,
        "target_file_count": progress.target_file_count,
        "per_file_target_slots": progress.per_file_target_slots,
        "next_empty_slot": asdict(progress.next_empty_slot) if progress.next_empty_slot is not None else None,
        "files": [asdict(summary) for summary in progress.file_summaries],
    }


def _throttle_payload(options: FillControllerOptions) -> dict[str, Any]:
    return {
        "relay_min_request_interval_seconds": relay_min_request_interval_seconds(),
        "retry_backoff_base_seconds": options.sleep_base_seconds,
        "retry_backoff_max_seconds": options.sleep_max_seconds,
    }


def _load_candidate_record(config: AppConfig, candidate_path: Path) -> dict[str, Any]:
    payload = load_yaml(candidate_path)
    if not isinstance(payload, dict):
        raise ContractValidationError(f"Candidate prescreen document must be a mapping: {candidate_path}")
    validate_candidate_record(config, payload)
    return payload


def _save_candidate_record(config: AppConfig, candidate_path: Path, record: dict[str, Any]) -> None:
    validate_candidate_record(config, record)
    dump_yaml(candidate_path, record)


def _repair_raw_excerpt(record: dict[str, Any]) -> bool:
    raw_excerpt = record.get("raw_evidence_excerpt")
    cleaned = clean_raw_evidence_excerpt(raw_excerpt)
    if not cleaned or cleaned == raw_excerpt:
        return False
    record["raw_evidence_excerpt"] = cleaned
    record["updated_at"] = utc_now_iso()
    return True


def _has_reviewable_evidence(record: dict[str, Any]) -> bool:
    summary = str(record.get("summary") or "").strip()
    raw_excerpt = str(record.get("raw_evidence_excerpt") or "").strip()
    return bool(summary or raw_excerpt)


def _workspace_candidate_paths(config: AppConfig) -> list[Path]:
    if not config.candidate_workspace_dir.exists():
        return []
    return sorted(path for path in config.candidate_workspace_dir.rglob("*.yaml") if path.name.startswith("cand_"))


def _candidate_needs_handoff(record: dict[str, Any]) -> bool:
    handoff = record.get("staging_handoff")
    handoff_status = handoff.get("status") if isinstance(handoff, dict) else None
    return record.get("human_review_status") == "approved_for_staging" and handoff_status != "written"


def _candidate_needs_review(record: dict[str, Any]) -> bool:
    handoff = record.get("staging_handoff")
    handoff_status = handoff.get("status") if isinstance(handoff, dict) else None
    if record.get("human_review_status") != "pending_first_pass" or handoff_status == "written":
        return False
    # Keep first-pass backlog recoverable, but do not keep re-sending the same
    # unchanged pending candidate to the reviewer on every fill iteration.
    return record.get("human_reviewed_at") in (None, "")


def _note_for_decision(
    decision: CandidateReviewDecision,
    *,
    note_templates: dict[str, str],
) -> tuple[str | None, str | None]:
    if decision.suggested_review_status == "approved_for_staging":
        prefix = note_templates["approved"]
        return "approved", prefix if not decision.rationale else f"{prefix}; {decision.rationale}"
    if decision.suggested_review_status == "on_hold":
        prefix = note_templates["hold"]
        return "hold", prefix if not decision.rationale else f"{prefix}; {decision.rationale}"
    if decision.suggested_review_status == "rejected_after_human_review":
        prefix = note_templates["rejected"]
        return "rejected", prefix if not decision.rationale else f"{prefix}; {decision.rationale}"
    return None, None


def _apply_review_decision(
    record: dict[str, Any],
    decision: CandidateReviewDecision,
    *,
    note_templates: dict[str, str],
) -> None:
    note_key, note_text = _note_for_decision(decision, note_templates=note_templates)
    record["human_review_status"] = decision.suggested_review_status
    record["human_review_note_template_key"] = note_key
    record["human_review_notes"] = note_text
    record["human_reviewed_at"] = utc_now_iso()
    record["updated_at"] = utc_now_iso()


def _review_failure_result(
    *,
    record: dict[str, Any],
    candidate_path: Path,
    review_origin: str,
    exc: ProcessingError,
) -> dict[str, Any]:
    return {
        "candidate_id": str(record["candidate_id"]),
        "candidate_document_path": str(candidate_path),
        "review_origin": review_origin,
        "suggested_review_status": str(record.get("human_review_status") or "pending_first_pass"),
        "reviewer_failure": {
            "error_type": exc.error_type,
            "message": str(exc),
            "retryable": exc.error_type in RETRYABLE_ERROR_TYPES,
        },
    }


def _handoff_candidate_record(
    config: AppConfig,
    *,
    candidate_path: Path,
    record: dict[str, Any],
) -> dict[str, Any]:
    staging_document_path, slot_id = handoff_candidate_to_staging(
        record,
        candidate_path=candidate_path,
        staging_dir=config.gold_set_staging_dir,
    )
    record["staging_handoff"] = {
        "status": "written",
        "staging_document_path": staging_document_path,
        "sample_slot_id": slot_id,
        "sample_id": record["candidate_id"],
        "blocking_items": [],
        "last_attempted_at": utc_now_iso(),
    }
    record["updated_at"] = utc_now_iso()
    _save_candidate_record(config, candidate_path, record)
    validate_staging_handoff(
        staging_document_path=staging_document_path,
        candidate_id=str(record["candidate_id"]),
        candidate_path=candidate_path,
        sample_slot_id=slot_id,
    )
    return {
        "candidate_id": str(record["candidate_id"]),
        "candidate_document_path": str(candidate_path),
        "staging_document_path": staging_document_path,
        "sample_slot_id": slot_id,
        "sample_id": str(record["candidate_id"]),
    }


def _workspace_review_loop(
    config: AppConfig,
    *,
    note_templates: dict[str, str],
    review_timeout_seconds: int,
    review_max_retries: int,
    review_fixture_path: Path | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    review_results: list[dict[str, Any]] = []
    handoff_results: list[dict[str, Any]] = []
    for candidate_path in _workspace_candidate_paths(config):
        record = _load_candidate_record(config, candidate_path)
        if _repair_raw_excerpt(record):
            _save_candidate_record(config, candidate_path, record)

        if _candidate_needs_handoff(record):
            handoff_results.append(_handoff_candidate_record(config, candidate_path=candidate_path, record=record))
            break

        if not _candidate_needs_review(record):
            continue
        if not _has_reviewable_evidence(record):
            review_results.append(
                {
                    "candidate_id": str(record["candidate_id"]),
                    "candidate_document_path": str(candidate_path),
                    "review_origin": "existing_workspace",
                    "suggested_review_status": "pending_first_pass",
                    "reason": "No readable summary or raw_evidence_excerpt available for first-pass review.",
                }
            )
            continue

        try:
            decision = review_candidate_with_llm(
                record,
                fixture_path=review_fixture_path,
                timeout_seconds=review_timeout_seconds,
                max_retries=review_max_retries,
            )
        except ProcessingError as exc:
            if exc.error_type not in RETRYABLE_ERROR_TYPES:
                raise
            # Keep the candidate pending so a later rerun can retry reviewer work
            # once the relay/provider path recovers.
            review_results.append(
                _review_failure_result(
                    record=record,
                    candidate_path=candidate_path,
                    review_origin="existing_workspace",
                    exc=exc,
                )
            )
            continue
        _apply_review_decision(record, decision, note_templates=note_templates)
        _save_candidate_record(config, candidate_path, record)
        review_results.append(
            {
                "candidate_id": str(record["candidate_id"]),
                "candidate_document_path": str(candidate_path),
                "review_origin": "existing_workspace",
                **decision.as_dict(),
            }
        )
        if decision.suggested_review_status == "approved_for_staging":
            handoff_results.append(_handoff_candidate_record(config, candidate_path=candidate_path, record=record))
            break
    return review_results, handoff_results


def _live_review_loop(
    config: AppConfig,
    *,
    options: FillControllerOptions,
    note_templates: dict[str, str],
    review_timeout_seconds: int,
    review_max_retries: int,
    cursor: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    window, query_slice_id = _next_live_request(cursor)
    _save_cursor(config, cursor)
    written_paths = run_candidate_prescreen(
        config,
        source_code=options.source_code,
        window=window,
        query_slice_id=query_slice_id,
        limit=options.live_limit,
        discovery_fixture_path=options.discovery_fixture_path,
        llm_fixture_path=options.llm_fixture_path,
    )
    live_fetch = {
        "source": "live_github_prescreen" if options.source_code == "github" else f"live_{options.source_code}_prescreen",
        "window": window,
        "query_slice_id": query_slice_id,
        "candidate_document_paths": [str(path) for path in written_paths],
    }
    review_results: list[dict[str, Any]] = []
    handoff_results: list[dict[str, Any]] = []
    for candidate_path in written_paths:
        record = _load_candidate_record(config, candidate_path)
        if _repair_raw_excerpt(record):
            _save_candidate_record(config, candidate_path, record)
        if not _has_reviewable_evidence(record):
            review_results.append(
                {
                    "candidate_id": str(record["candidate_id"]),
                    "candidate_document_path": str(candidate_path),
                    "review_origin": live_fetch["source"],
                    "suggested_review_status": "pending_first_pass",
                    "reason": "No readable summary or raw_evidence_excerpt available after live discovery.",
                }
            )
            continue

        try:
            decision = review_candidate_with_llm(
                record,
                fixture_path=options.review_fixture_path,
                timeout_seconds=review_timeout_seconds,
                max_retries=review_max_retries,
            )
        except ProcessingError as exc:
            if exc.error_type not in RETRYABLE_ERROR_TYPES:
                raise
            # A live candidate with transient reviewer failure should stay recoverable
            # without aborting the whole fill iteration.
            review_results.append(
                _review_failure_result(
                    record=record,
                    candidate_path=candidate_path,
                    review_origin=live_fetch["source"],
                    exc=exc,
                )
            )
            continue
        _apply_review_decision(record, decision, note_templates=note_templates)
        _save_candidate_record(config, candidate_path, record)
        review_results.append(
            {
                "candidate_id": str(record["candidate_id"]),
                "candidate_document_path": str(candidate_path),
                "review_origin": live_fetch["source"],
                **decision.as_dict(),
            }
        )
        if decision.suggested_review_status == "approved_for_staging":
            handoff_results.append(_handoff_candidate_record(config, candidate_path=candidate_path, record=record))
            break
    return [str(path) for path in written_paths], review_results, handoff_results, live_fetch


def run_one_fill_iteration(
    config: AppConfig,
    *,
    options: FillControllerOptions,
    iteration: int,
    cursor: dict[str, Any],
) -> dict[str, Any]:
    if options.live_limit <= 0 or options.live_limit > 2:
        raise ContractValidationError("fill-gold-set-staging-until-complete live_limit must stay within 1..2")

    workflow_config = load_candidate_prescreen_config(config.config_dir)
    workspace = workflow_config.get("workspace")
    llm_prescreen = workflow_config.get("llm_prescreen")
    if not isinstance(workspace, dict) or not isinstance(llm_prescreen, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml lost workspace or llm_prescreen mappings")
    note_templates = workspace.get("human_review_note_templates")
    if not isinstance(note_templates, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml human_review_note_templates must stay a mapping")

    validate_candidate_workspace(config)
    before_progress = summarize_staging_progress(
        config.gold_set_staging_dir,
        target_file_count=options.target_file_count,
        per_file_target_slots=options.target_slots_per_file,
    )
    if before_progress.total_filled > options.target_total_filled:
        raise ContractValidationError(
            f"Staging already exceeds target_total_filled={options.target_total_filled}: {before_progress.total_filled}"
        )
    if before_progress.is_complete and before_progress.total_filled == options.target_total_filled:
        return {
            "phase": "already_complete",
            "iteration": iteration,
            "timestamp": utc_now_iso(),
            "throttle": _throttle_payload(options),
            "staging_progress_before": _staging_progress_payload(before_progress),
            "staging_progress_after": _staging_progress_payload(before_progress),
            "workspace_candidates_considered": [],
            "live_fetch": None,
            "review_results": [],
            "handoff_results": [],
            "failure": None,
        }

    gold_set_sample_count_before = _formal_gold_set_sample_count(config.gold_set_dir)
    review_timeout_seconds = int(llm_prescreen.get("timeout_seconds_default", 30))
    review_max_retries = int(llm_prescreen.get("max_retries_default", 2))

    workspace_review_results, handoff_results = _workspace_review_loop(
        config,
        note_templates=note_templates,
        review_timeout_seconds=review_timeout_seconds,
        review_max_retries=review_max_retries,
        review_fixture_path=options.review_fixture_path,
    )
    live_fetch: dict[str, Any] | None = None
    if not handoff_results:
        live_paths, live_review_results, live_handoffs, live_fetch = _live_review_loop(
            config,
            options=options,
            note_templates=note_templates,
            review_timeout_seconds=review_timeout_seconds,
            review_max_retries=review_max_retries,
            cursor=cursor,
        )
        workspace_review_results.extend(live_review_results)
        handoff_results.extend(live_handoffs)
        if live_fetch is not None:
            live_fetch["candidate_document_paths"] = live_paths

    validate_candidate_workspace(config)
    after_progress = summarize_staging_progress(
        config.gold_set_staging_dir,
        target_file_count=options.target_file_count,
        per_file_target_slots=options.target_slots_per_file,
    )
    gold_set_sample_count_after = _formal_gold_set_sample_count(config.gold_set_dir)
    if gold_set_sample_count_after != gold_set_sample_count_before:
        raise ContractValidationError("fill controller must not write into the formal gold_set/gold_set_300/ directory")

    return {
        "phase": "iteration",
        "iteration": iteration,
        "timestamp": utc_now_iso(),
        "throttle": _throttle_payload(options),
        "staging_progress_before": _staging_progress_payload(before_progress),
        "staging_progress_after": _staging_progress_payload(after_progress),
        "workspace_candidates_considered": [str(path) for path in _workspace_candidate_paths(config)],
        "live_fetch": live_fetch,
        "review_results": workspace_review_results,
        "handoff_results": handoff_results,
        "failure": None,
    }


def fill_gold_set_staging_until_complete(
    config: AppConfig,
    *,
    options: FillControllerOptions,
) -> FillLoopResult:
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    query_slice_ids = _query_slice_ids(workflow_config, options.source_code)
    initial_window = options.initial_window or _default_initial_window(config, options.source_code)
    cursor = _load_cursor(
        config,
        source_code=options.source_code,
        initial_window=initial_window,
        query_slice_ids=query_slice_ids,
    )
    attempt = 0
    iteration = 0

    initial_progress = summarize_staging_progress(
        config.gold_set_staging_dir,
        target_file_count=options.target_file_count,
        per_file_target_slots=options.target_slots_per_file,
    )
    init_event = {
        "phase": "init",
        "iteration": 0,
        "timestamp": utc_now_iso(),
        "throttle": _throttle_payload(options),
        "staging_progress_before": _staging_progress_payload(initial_progress),
        "staging_progress_after": _staging_progress_payload(initial_progress),
        "workspace_candidates_considered": [str(path) for path in _workspace_candidate_paths(config)],
        "live_fetch": None,
        "review_results": [],
        "handoff_results": [],
        "failure": None,
    }
    _append_audit_log(config, init_event)
    _print_iteration_summary(init_event)

    while True:
        current_progress = summarize_staging_progress(
            config.gold_set_staging_dir,
            target_file_count=options.target_file_count,
            per_file_target_slots=options.target_slots_per_file,
        )
        if current_progress.is_complete and current_progress.total_filled == options.target_total_filled:
            completion_event = {
                "phase": "complete",
                "iteration": iteration,
                "timestamp": utc_now_iso(),
                "throttle": _throttle_payload(options),
                "staging_progress_before": _staging_progress_payload(current_progress),
                "staging_progress_after": _staging_progress_payload(current_progress),
                "workspace_candidates_considered": [],
                "live_fetch": None,
                "review_results": [],
                "handoff_results": [],
                "failure": None,
            }
            _append_audit_log(config, completion_event)
            _print_iteration_summary(completion_event)
            return FillLoopResult(
                iterations=iteration,
                total_filled=current_progress.total_filled,
                target_total_filled=options.target_total_filled,
                audit_log_path=str(_audit_log_path(config)),
                cursor_path=str(_cursor_path(config)),
            )
        if options.max_iterations is not None and iteration >= options.max_iterations:
            raise ContractValidationError(
                f"fill-gold-set-staging-until-complete stopped after max_iterations={options.max_iterations} before completion"
            )

        iteration += 1
        try:
            event = run_one_fill_iteration(config, options=options, iteration=iteration, cursor=cursor)
        except ProcessingError as exc:
            failure_event = {
                "phase": "iteration_failure",
                "iteration": iteration,
                "timestamp": utc_now_iso(),
                "throttle": _throttle_payload(options),
                "staging_progress_before": _staging_progress_payload(current_progress),
                "staging_progress_after": _staging_progress_payload(current_progress),
                "workspace_candidates_considered": [],
                "live_fetch": None,
                "review_results": [],
                "handoff_results": [],
                "failure": {
                    "step": "processing",
                    "error_type": exc.error_type,
                    "message": str(exc),
                    "retryable": exc.error_type in RETRYABLE_ERROR_TYPES,
                },
            }
            _append_audit_log(config, failure_event)
            _print_iteration_summary(failure_event)
            delay = _retry_delay_seconds(exc.error_type, attempt, options)
            if exc.error_type not in RETRYABLE_ERROR_TYPES:
                raise
            attempt += 1
            if delay > 0:
                time.sleep(delay)
            continue
        except ContractValidationError as exc:
            failure_event = {
                "phase": "iteration_failure",
                "iteration": iteration,
                "timestamp": utc_now_iso(),
                "throttle": _throttle_payload(options),
                "staging_progress_before": _staging_progress_payload(current_progress),
                "staging_progress_after": _staging_progress_payload(current_progress),
                "workspace_candidates_considered": [],
                "live_fetch": None,
                "review_results": [],
                "handoff_results": [],
                "failure": {
                    "step": "contract_validation",
                    "error_type": "schema_drift",
                    "message": str(exc),
                    "retryable": False,
                },
            }
            _append_audit_log(config, failure_event)
            _print_iteration_summary(failure_event)
            raise

        attempt = 0
        _append_audit_log(config, event)
        _print_iteration_summary(event)
