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
from src.common.constants import TASK_STATUSES
from src.common.errors import ContractValidationError
from src.common.files import load_json, utc_now_iso
from src.marts.presentation import build_dashboard_view, build_product_drill_down, reconcile_dashboard_view
from src.review.review_packet_builder import OPEN_REVIEW_STATUSES, build_review_queue_entry
from src.review.store import default_review_issue_store_path
from src.runtime.processing_errors import default_processing_error_store_path

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

_SUPPORTED_OPERATOR_READ_COMMANDS = [
    {
        "command": "operator_api_contract",
        "response_view": "operator_api_contract_catalog",
        "required_context": [],
        "required_params": [],
        "optional_params": ["request_id"],
    },
    {
        "command": "operator_api_snapshot",
        "response_view": "operator_api_snapshot",
        "required_context": ["config", "mart"],
        "required_params": [],
        "optional_params": ["product_id", "open_review_only", "request_id"],
    },
    {
        "command": "operator_dashboard_view",
        "response_view": "dashboard_mart_view",
        "required_context": ["mart"],
        "required_params": [],
        "optional_params": ["request_id"],
    },
    {
        "command": "operator_product_drill_down",
        "response_view": "product_drill_down",
        "required_context": ["mart"],
        "required_params": ["product_id"],
        "optional_params": ["request_id"],
    },
    {
        "command": "operator_review_queue",
        "response_view": "review_queue_view",
        "required_context": ["config"],
        "required_params": [],
        "optional_params": ["open_only", "review_issue_id", "request_id"],
    },
    {
        "command": "operator_task_inspection",
        "response_view": "task_inspection_view",
        "required_context": ["config"],
        "required_params": [],
        "optional_params": ["task_id", "status", "request_id"],
    },
]


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


def build_operator_api_contract_response(request_id: str | None = None) -> dict[str, Any]:
    """Return the read-only operator API capability catalog."""

    operation = "operator_api_contract_catalog"
    view = operator_api_capability_catalog()
    return _operator_view_response(operation=operation, request_id=request_id, view=view)


def build_operator_dashboard_response(
    *,
    mart: dict[str, Any],
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return only the dashboard/mart service view with audit metadata."""

    operation = "operator_dashboard_mart_view"
    view = dashboard_mart_view(mart)
    return _operator_view_response(operation=operation, request_id=request_id, view=view)


def build_operator_product_drill_down_response(
    *,
    mart: dict[str, Any],
    product_id: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return only the trace-only product drill-down service view."""

    operation = "operator_product_drill_down"
    view = product_drill_down_view(mart, product_id=product_id)
    return _operator_view_response(operation=operation, request_id=request_id, view=view)


def build_operator_review_queue_response(
    *,
    config: AppConfig,
    open_only: bool = False,
    review_issue_id: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return only the review queue service view with review semantics intact."""

    operation = "operator_review_queue_view"
    view = review_queue_view(config=config, open_only=open_only, review_issue_id=review_issue_id)
    return _operator_view_response(operation=operation, request_id=request_id, view=view)


def build_operator_task_inspection_response(
    *,
    task_store_path: Path,
    task_id: str | None = None,
    status: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Return only the runtime task inspection service view."""

    operation = "operator_task_inspection_view"
    view = task_inspection_view(task_store_path, task_id=task_id, status=status)
    return _operator_view_response(operation=operation, request_id=request_id, view=view)


def dispatch_operator_read(
    command: str,
    params: dict[str, Any] | None = None,
    *,
    config: AppConfig | None = None,
    mart: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch a framework-neutral operator read command.

    This is the narrow adapter seam for a later web framework or control-plane
    shell. It intentionally accepts already-loaded read models so the service
    layer does not decide how to build marts, claim tasks, or open write paths.
    """

    if not isinstance(command, str) or not command:
        raise ContractValidationError("operator read command must be a non-empty string")
    if params is None:
        normalized_params: dict[str, Any] = {}
    elif isinstance(params, dict):
        normalized_params = dict(params)
    else:
        raise ContractValidationError("operator read params must be a mapping")
    _reject_unknown_params(command, normalized_params)
    request_id = _optional_string(normalized_params.get("request_id"), "request_id")
    if command == "operator_api_contract":
        return build_operator_api_contract_response(request_id=request_id)
    if command == "operator_api_snapshot":
        return build_operator_api_snapshot(
            config=_require_config(config, command),
            mart=_require_mart(mart, command),
            product_id=_optional_string(normalized_params.get("product_id"), "product_id"),
            open_review_only=_optional_bool(normalized_params.get("open_review_only"), "open_review_only"),
            request_id=request_id,
        )
    if command == "operator_dashboard_view":
        return build_operator_dashboard_response(
            mart=_require_mart(mart, command),
            request_id=request_id,
        )
    if command == "operator_product_drill_down":
        return build_operator_product_drill_down_response(
            mart=_require_mart(mart, command),
            product_id=_required_string(normalized_params.get("product_id"), "product_id"),
            request_id=request_id,
        )
    if command == "operator_review_queue":
        return build_operator_review_queue_response(
            config=_require_config(config, command),
            open_only=_optional_bool(normalized_params.get("open_only"), "open_only"),
            review_issue_id=_optional_string(normalized_params.get("review_issue_id"), "review_issue_id"),
            request_id=request_id,
        )
    if command == "operator_task_inspection":
        return build_operator_task_inspection_response(
            task_store_path=_require_config(config, command).task_store_path,
            task_id=_optional_string(normalized_params.get("task_id"), "task_id"),
            status=_optional_string(normalized_params.get("status"), "status"),
            request_id=request_id,
        )
    raise ContractValidationError(f"Unsupported operator read command: {command}")


def service_audit_envelope(
    *,
    operation: str,
    request_id: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    phase: str = "Phase2-3",
) -> dict[str, Any]:
    """Build a read-only audit envelope for later service adapters."""

    generated_at = utc_now_iso()
    normalized_request_id = request_id or _stable_request_id(operation, generated_at)
    return {
        "request_id": normalized_request_id,
        "operation": operation,
        "generated_at": generated_at,
        "phase": phase,
        "read_only": True,
        "side_effects": [],
        "runtime_cutover_executed": False,
        "production_db_readiness_claimed": False,
        "evidence_refs": list(evidence_refs or []),
    }


def _operator_view_response(
    *,
    operation: str,
    request_id: str | None,
    view: dict[str, Any],
) -> dict[str, Any]:
    evidence_refs = list(_PHASE2_3_EVIDENCE_REFS)
    return {
        "audit": service_audit_envelope(
            operation=operation,
            request_id=request_id,
            evidence_refs=evidence_refs,
        ),
        "api_contract": operator_api_contract(),
        "view": view,
        "cutover_guardrails": cutover_guardrails(),
        "evidence_refs": evidence_refs,
    }


def operator_api_contract() -> dict[str, Any]:
    """Describe the framework-neutral contract exposed by this module."""

    return {
        "service_contract_version": "operator_api_contract_v1",
        "phase": "Phase2-3",
        "status": "service_api_contract_started",
        "framework_binding": None,
        "write_paths_enabled": False,
        "approved_write_operations": [],
        "blocked_write_operations": [
            "task_submission",
            "review_resolution",
            "replay_trigger",
            "runtime_cutover",
        ],
        "dashboard_read_policy": "mart_or_materialized_view_first",
        "drill_down_policy": "traceability_only_no_metric_recompute",
        "review_state_policy": "preserve_review_issue_status_and_maker_checker_fields",
        "task_state_policy": "preserve_runtime_task_status_and_blocked_replay_semantics",
        "endpoint_shapes": [
            "operator_api_contract_catalog",
            "dashboard_mart_view",
            "product_drill_down",
            "review_queue_view",
            "task_inspection_view",
        ],
    }


def operator_api_capability_catalog() -> dict[str, Any]:
    """Describe available read commands without exposing service write paths."""

    contract = operator_api_contract()
    return {
        "view_type": "operator_api_contract_catalog",
        "service_contract_version": contract["service_contract_version"],
        "framework_binding": contract["framework_binding"],
        "write_paths_enabled": contract["write_paths_enabled"],
        "approved_write_operations": list(contract["approved_write_operations"]),
        "blocked_write_operations": list(contract["blocked_write_operations"]),
        "supported_read_commands": [dict(command) for command in _SUPPORTED_OPERATOR_READ_COMMANDS],
        "write_operations_not_available": [
            "task_submission",
            "review_resolution",
            "replay_trigger",
            "runtime_cutover",
        ],
        "guardrails": cutover_guardrails(),
        "evidence_refs": list(_PHASE2_3_EVIDENCE_REFS),
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

    try:
        drill_down = build_product_drill_down(mart, product_id=product_id)
    except KeyError as exc:
        raise ContractValidationError(f"Product drill-down trace is unavailable for product_id={product_id}") from exc
    trace_refs = drill_down["trace_refs"]
    return {
        "view_type": "product_drill_down",
        "product_id": product_id,
        "trace_policy": "runtime_objects_for_evidence_only_no_metric_recompute",
        "payload": drill_down,
        "evidence_refs": _drill_down_evidence_refs(trace_refs),
    }


def review_queue_view(
    *,
    config: AppConfig,
    open_only: bool = False,
    review_issue_id: str | None = None,
) -> dict[str, Any]:
    """Expose review queue state without flattening it into success/failure."""

    issues = _read_json_list(default_review_issue_store_path(config.task_store_path), "review_issue store")
    filtered = issues if not open_only else [issue for issue in issues if issue.get("status") in OPEN_REVIEW_STATUSES]
    if review_issue_id is not None:
        filtered = [issue for issue in filtered if issue.get("review_issue_id") == review_issue_id]
    entries = []
    for issue in filtered:
        merged = dict(issue)
        merged.update(build_review_queue_entry(issue, config_dir=config.config_dir))
        entries.append(merged)
    return {
        "view_type": "review_queue_view",
        "open_only": open_only,
        "review_issue_id": review_issue_id,
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


def task_inspection_view(
    task_store_path: Path,
    *,
    task_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """Expose task and processing-error state while preserving blocked replay."""

    if status is not None and status not in TASK_STATUSES:
        raise ContractValidationError(f"Unsupported task status filter: {status}")
    tasks = _read_json_list(task_store_path, "task store")
    processing_errors = _read_json_list(default_processing_error_store_path(task_store_path), "processing_error store")
    if task_id is not None:
        tasks = [task for task in tasks if task.get("task_id") == task_id]
        processing_errors = [error for error in processing_errors if error.get("run_id") == task_id]
    if status is not None:
        tasks = [task for task in tasks if task.get("status") == status]
        task_ids = {task.get("task_id") for task in tasks}
        processing_errors = [error for error in processing_errors if error.get("run_id") in task_ids]
    return {
        "view_type": "task_inspection_view",
        "task_id": task_id,
        "status": status,
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


def _require_config(config: AppConfig | None, command: str) -> AppConfig:
    if not isinstance(config, AppConfig):
        raise ContractValidationError(f"{command} requires AppConfig")
    return config


def _require_mart(mart: dict[str, Any] | None, command: str) -> dict[str, Any]:
    if not isinstance(mart, dict):
        raise ContractValidationError(f"{command} requires a preloaded mart read model")
    return mart


def _reject_unknown_params(command: str, params: dict[str, Any]) -> None:
    catalog_entry = next(
        (entry for entry in _SUPPORTED_OPERATOR_READ_COMMANDS if entry["command"] == command),
        None,
    )
    if catalog_entry is None:
        return
    allowed_params = set(catalog_entry["required_params"]) | set(catalog_entry["optional_params"])
    unknown_params = sorted(set(params) - allowed_params)
    if unknown_params:
        joined = ", ".join(unknown_params)
        raise ContractValidationError(f"{command} received unsupported params: {joined}")


def _required_string(value: object, field_name: str) -> str:
    if isinstance(value, Path):
        return str(value)
    if not isinstance(value, str) or not value:
        raise ContractValidationError(f"{field_name} must be a non-empty string")
    return value


def _optional_string(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field_name)


def _optional_bool(value: object, field_name: str) -> bool:
    if value is None:
        return False
    if not isinstance(value, bool):
        raise ContractValidationError(f"{field_name} must be a boolean")
    return value


def _stable_request_id(operation: str, generated_at: str) -> str:
    seed = f"{operation}:{generated_at}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    return f"opapi_{digest}"


def _read_json_list(path: Path, description: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = load_json(path)
    if not isinstance(payload, list):
        raise ContractValidationError(f"{description} must contain a JSON list: {path}")
    rows: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ContractValidationError(f"{description}[{index}] must be a JSON object: {path}")
        rows.append(dict(item))
    return rows
