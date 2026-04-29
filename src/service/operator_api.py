"""Read-only operator API contract helpers for Phase2-3.

The module deliberately stays framework-neutral.  It composes existing mart,
review, processing-error, and task-store readers into API-shaped payloads
without adding write paths, DB cutover flags, or dashboard-side recomputation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.common.config import AppConfig
from src.common.files import utc_now_iso
from src.marts.presentation import build_dashboard_view, build_product_drill_down, reconcile_dashboard_view
from src.review.review_packet_builder import OPEN_REVIEW_STATUSES
from src.review.runtime import list_review_queue
from src.review.store import FileReviewIssueStore, default_review_issue_store_path
from src.runtime.processing_errors import FileProcessingErrorStore, default_processing_error_store_path
from src.runtime.tasks import FileTaskStore

_PHASE2_3_EVIDENCE_REFS = [
    {
        "ref_type": "canonical_doc",
        "path": "phase2_prompt.md",
        "section": "Phase2-3 Service API And Operator Control Plane",
    },
    {
        "ref_type": "canonical_doc",
        "path": "11_metrics_and_marts.md",
        "section": "9.2 Consumption Read Contract",
    },
    {
        "ref_type": "evidence_doc",
        "path": "docs/phase1_g_acceptance_evidence.md",
        "section": "4. Local Reconciliation Evidence",
    },
]

_PENDING_HUMAN_SELECTIONS = {
    "runtime_db_driver": None,
    "migration_tool": None,
    "managed_postgresql_vendor": None,
    "secrets_manager": None,
    "dashboard_framework": None,
}


def build_operator_api_snapshot(
    *,
    config: AppConfig,
    mart: dict[str, Any],
    product_id: str | None = None,
    open_review_only: bool = False,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return the first Phase2-3 operator control-plane snapshot.

    The snapshot is API-shaped but in-process: callers can expose it through a
    CLI, tests, or a later web framework adapter without freezing that framework.
    """

    operation = "operator_api_snapshot"
    evidence_refs = list(_PHASE2_3_EVIDENCE_REFS)
    return {
        "audit": service_audit_envelope(
            operation=operation,
            request_id=request_id,
            evidence_refs=evidence_refs,
        ),
        "api_contract": operator_api_contract(),
        "dashboard_mart_view": dashboard_mart_view(mart),
        "product_drill_down": product_drill_down_view(mart, product_id=product_id) if product_id else None,
        "review_queue_view": review_queue_view(config=config, open_only=open_review_only),
        "task_inspection_view": task_inspection_view(config.task_store_path),
        "cutover_guardrails": cutover_guardrails(),
        "evidence_refs": evidence_refs,
    }


def service_audit_envelope(
    *,
    operation: str,
    request_id: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a read-only audit envelope for later service adapters."""

    generated_at = utc_now_iso()
    normalized_request_id = request_id or _stable_request_id(operation, generated_at)
    return {
        "request_id": normalized_request_id,
        "operation": operation,
        "generated_at": generated_at,
        "phase": "Phase2-3",
        "read_only": True,
        "side_effects": [],
        "runtime_cutover_executed": False,
        "production_db_readiness_claimed": False,
        "evidence_refs": list(evidence_refs or []),
    }


def operator_api_contract() -> dict[str, Any]:
    """Describe the framework-neutral contract exposed by this module."""

    return {
        "phase": "Phase2-3",
        "status": "service_api_contract_started",
        "framework_binding": None,
        "write_paths_enabled": False,
        "dashboard_read_policy": "mart_or_materialized_view_first",
        "drill_down_policy": "traceability_only_no_metric_recompute",
        "review_state_policy": "preserve_review_issue_status_and_maker_checker_fields",
        "task_state_policy": "preserve_runtime_task_status_and_blocked_replay_semantics",
        "endpoint_shapes": [
            "dashboard_mart_view",
            "product_drill_down",
            "review_queue_view",
            "task_inspection_view",
        ],
    }


def dashboard_mart_view(mart: dict[str, Any]) -> dict[str, Any]:
    """Expose dashboard payloads that are already derived from mart outputs."""

    dashboard = build_dashboard_view(mart)
    reconciliation = reconcile_dashboard_view(mart)
    return {
        "view_type": "dashboard_mart_view",
        "read_model": "mart_backed",
        "mart_first_discipline": {
            "runtime_detail_join_allowed": False,
            "business_metric_recompute_allowed": False,
            "main_report_semantics": dashboard.get("main_report_semantics"),
        },
        "window_start": mart.get("window_start"),
        "window_end": mart.get("window_end"),
        "mart_version": mart.get("mart_version"),
        "payload": dashboard,
        "reconciliation": {
            "all_passed": reconciliation["all_passed"],
            "pass_rate": reconciliation["pass_rate"],
            "check_count": reconciliation["check_count"],
            "passed_count": reconciliation["passed_count"],
            "dashboard_contract_ref": reconciliation["dashboard_contract_ref"],
        },
        "evidence_refs": [
            {
                "ref_type": "mart_contract",
                "dataset": "dashboard_read_contract",
                "mart_version": mart.get("mart_version"),
            }
        ],
    }


def product_drill_down_view(mart: dict[str, Any], *, product_id: str) -> dict[str, Any]:
    """Expose trace-only product drill-down without redeciding mart metrics."""

    drill_down = build_product_drill_down(mart, product_id=product_id)
    trace_refs = drill_down["trace_refs"]
    return {
        "view_type": "product_drill_down",
        "product_id": product_id,
        "trace_policy": "runtime_objects_for_evidence_only_no_metric_recompute",
        "payload": drill_down,
        "evidence_refs": _drill_down_evidence_refs(trace_refs),
    }


def review_queue_view(*, config: AppConfig, open_only: bool = False) -> dict[str, Any]:
    """Expose review queue state without flattening it into success/failure."""

    store = FileReviewIssueStore(default_review_issue_store_path(config.task_store_path))
    issues = store.all_issues()
    queue_entries = list_review_queue(config_dir=config.config_dir, task_store_path=config.task_store_path, open_only=open_only)
    issue_by_id = {issue.get("review_issue_id"): issue for issue in issues}
    entries = []
    for queue_entry in queue_entries:
        issue = issue_by_id.get(queue_entry.get("review_issue_id"), {})
        merged = dict(issue)
        merged.update(queue_entry)
        entries.append(merged)
    return {
        "view_type": "review_queue_view",
        "open_only": open_only,
        "state_model": "review_issue",
        "generic_success_failure_flattening_allowed": False,
        "maker_checker_bypass_allowed": False,
        "issue_count": len(entries),
        "open_issue_count": sum(1 for issue in issues if issue.get("status") in OPEN_REVIEW_STATUSES),
        "items": [_review_queue_item(entry) for entry in entries],
        "evidence_refs": [
            {
                "ref_type": "canonical_doc",
                "path": "12_review_policy.md",
                "section": "5.5 Maker-Checker Writeback",
            }
        ],
    }


def task_inspection_view(task_store_path: Path) -> dict[str, Any]:
    """Expose task and processing-error state while preserving blocked replay."""

    task_store = FileTaskStore(task_store_path)
    processing_error_store = FileProcessingErrorStore(default_processing_error_store_path(task_store_path))
    tasks = task_store.all_tasks()
    processing_errors = processing_error_store.all_errors()
    return {
        "view_type": "task_inspection_view",
        "state_model": "runtime_task",
        "generic_success_failure_flattening_allowed": False,
        "blocked_replay_bypass_allowed": False,
        "task_count": len(tasks),
        "blocked_task_count": sum(1 for task in tasks if task.get("status") == "blocked"),
        "processing_error_count": len(processing_errors),
        "tasks": [_task_item(task) for task in tasks],
        "processing_errors": [_processing_error_item(error) for error in processing_errors],
        "evidence_refs": [
            {
                "ref_type": "canonical_doc",
                "path": "18_runtime_task_and_replay_contracts.md",
                "section": "6. Blocked Task Rules",
            },
            {
                "ref_type": "canonical_doc",
                "path": "13_error_and_retry_policy.md",
                "section": "1. Two failure paths",
            },
        ],
    }


def cutover_guardrails() -> dict[str, Any]:
    """Return explicit Phase2-3 no-cutover guardrail flags."""

    return {
        "runtime_backend_default": "file_backed_local_harness",
        "db_backed_runtime_default": False,
        "real_db_connection": False,
        "cutover_eligible": False,
        "runtime_cutover_executed": False,
        "production_db_readiness_claimed": False,
        "runtime_cutover_readiness_claimed": False,
        "pending_human_selections": dict(_PENDING_HUMAN_SELECTIONS),
    }


def _review_queue_item(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "review_issue_id": entry.get("review_issue_id"),
        "issue_type": entry.get("issue_type"),
        "status": entry.get("status"),
        "priority_code": entry.get("priority_code"),
        "queue_bucket": entry.get("queue_bucket"),
        "target_type": entry.get("target_type"),
        "target_id": entry.get("target_id"),
        "resolution_action": entry.get("resolution_action"),
        "maker_checker_required": entry.get("maker_checker_required"),
        "reviewer": entry.get("reviewer"),
        "approver": entry.get("approver"),
        "evidence_refs": _extract_review_evidence_refs(entry),
    }


def _task_item(task: dict[str, Any]) -> dict[str, Any]:
    payload = task.get("payload_json") if isinstance(task.get("payload_json"), dict) else {}
    return {
        "task_id": task.get("task_id"),
        "task_type": task.get("task_type"),
        "task_scope": task.get("task_scope"),
        "source_id": task.get("source_id"),
        "target_type": task.get("target_type"),
        "target_id": task.get("target_id"),
        "window_start": task.get("window_start"),
        "window_end": task.get("window_end"),
        "status": task.get("status"),
        "attempt_count": task.get("attempt_count"),
        "max_attempts": task.get("max_attempts"),
        "parent_task_id": task.get("parent_task_id"),
        "last_error_type": task.get("last_error_type"),
        "last_error_message": task.get("last_error_message"),
        "replay_reason": payload.get("replay_reason"),
        "replay_basis": payload.get("replay_basis"),
        "resume_checkpoint_verified": payload.get("resume_checkpoint_verified"),
        "blocked_replay": task.get("status") == "blocked" or task.get("last_error_type") == "blocked_replay",
    }


def _processing_error_item(error: dict[str, Any]) -> dict[str, Any]:
    return {
        "error_id": error.get("error_id"),
        "module_name": error.get("module_name"),
        "run_id": error.get("run_id"),
        "source_id": error.get("source_id"),
        "target_type": error.get("target_type"),
        "target_id": error.get("target_id"),
        "error_type": error.get("error_type"),
        "retry_count": error.get("retry_count"),
        "resolution_status": error.get("resolution_status"),
        "next_retry_at": error.get("next_retry_at"),
    }


def _drill_down_evidence_refs(trace_refs: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for evidence_id in trace_refs.get("evidence_ids") or []:
        refs.append({"ref_type": "evidence", "evidence_id": evidence_id})
    for review_issue_id in trace_refs.get("review_issue_ids") or []:
        refs.append({"ref_type": "review_issue", "review_issue_id": review_issue_id})
    if trace_refs.get("source_item_id"):
        refs.append({"ref_type": "source_item", "source_item_id": trace_refs["source_item_id"]})
    if trace_refs.get("observation_id"):
        refs.append({"ref_type": "observation", "observation_id": trace_refs["observation_id"]})
    return refs


def _extract_review_evidence_refs(entry: dict[str, Any]) -> list[dict[str, Any]]:
    payload = entry.get("payload_json")
    if not isinstance(payload, dict):
        return []
    related = payload.get("related_evidence")
    if not isinstance(related, list):
        return []
    return [dict(item) for item in related if isinstance(item, dict)]


def _stable_request_id(operation: str, generated_at: str) -> str:
    seed = f"{operation}:{generated_at}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"opapi_{digest}"
