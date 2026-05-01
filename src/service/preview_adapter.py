"""Framework-neutral Phase2-4 read-only preview adapter.

The adapter turns the Phase2-3 operator read catalog and read payloads into a
UI-oriented view model without importing a frontend framework.  Streamlit, or
any later dashboard shell, can consume this model as a preview surface while
the production frontend framework remains unfrozen.
"""

from __future__ import annotations

from typing import Any

from src.common.config import AppConfig
from src.common.constants import TASK_STATUSES
from src.common.errors import ContractValidationError
from src.service.operator_api import cutover_guardrails, dispatch_operator_read, service_audit_envelope

_PHASE2_4_EVIDENCE_REFS = [
    {
        "ref_type": "canonical_doc",
        "path": "phase2_prompt.md",
        "section": "Phase2-4 Frontend Serviceization",
    },
    {
        "ref_type": "canonical_doc",
        "path": "15_tech_stack_and_runtime.md",
        "section": "10. Frontend / Dashboard Architecture Discipline",
    },
    {
        "ref_type": "decision",
        "decision_id": "DEC-030",
        "path": "17_open_decisions_and_freeze_board.md",
    },
]


def build_phase2_4_preview_model(
    *,
    config: AppConfig,
    mart: dict[str, Any],
    product_id: str | None = None,
    open_review_only: bool = False,
    task_id: str | None = None,
    task_status: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a stable read-only preview model over operator service reads."""

    _validate_optional_string(product_id, "product_id")
    _validate_bool(open_review_only, "open_review_only")
    _validate_optional_string(task_id, "task_id")
    _validate_optional_task_status(task_status)

    catalog_response = dispatch_operator_read(
        "operator_api_contract",
        {"request_id": _child_request_id(request_id, "catalog")},
    )
    dashboard_response = dispatch_operator_read(
        "operator_dashboard_view",
        {"request_id": _child_request_id(request_id, "dashboard")},
        mart=mart,
    )
    product_response = None
    if product_id:
        product_response = dispatch_operator_read(
            "operator_product_drill_down",
            {
                "product_id": product_id,
                "request_id": _child_request_id(request_id, "product"),
            },
            mart=mart,
        )
    review_response = dispatch_operator_read(
        "operator_review_queue",
        {
            "open_only": open_review_only,
            "request_id": _child_request_id(request_id, "review"),
        },
        config=config,
    )
    task_response = dispatch_operator_read(
        "operator_task_inspection",
        {
            "task_id": task_id,
            "status": task_status,
            "request_id": _child_request_id(request_id, "task"),
        },
        config=config,
    )

    service_reads = {
        "operator_api_contract": catalog_response["view"],
        "dashboard_mart_view": dashboard_response["view"],
        "product_drill_down": product_response["view"] if product_response else None,
        "review_queue_view": review_response["view"],
        "task_inspection_view": task_response["view"],
    }
    guardrails = cutover_guardrails()
    preview_model = {
        "audit": service_audit_envelope(
            operation="phase2_4_preview_model",
            request_id=request_id,
            evidence_refs=_PHASE2_4_EVIDENCE_REFS,
            phase="Phase2-4",
        ),
        "preview_contract_version": "phase2_4_preview_model_v1",
        "preview_status": "read_only_preview_adapter_started",
        "framework_policy": {
            "preview_surface": "framework_neutral_adapter",
            "streamlit_allowed_as_preview_only": True,
            "production_dashboard_framework_frozen": False,
            "framework_binding": None,
            "frontend_completion_claimed": False,
        },
        "navigation": _preview_navigation(
            catalog_response["view"],
            selected_product_id=product_id,
            task_id=task_id,
            task_status=task_status,
        ),
        "service_reads": service_reads,
        "blocked_actions": list(catalog_response["view"]["blocked_write_operations"]),
        "cutover_guardrails": guardrails,
        "evidence_refs": _preview_evidence_refs(service_reads),
    }
    preview_model["contract_checks"] = _preview_contract_checks(preview_model)
    return preview_model


def _preview_navigation(
    catalog: dict[str, Any],
    *,
    selected_product_id: str | None,
    task_id: str | None,
    task_status: str | None,
) -> list[dict[str, Any]]:
    commands = {entry["command"]: entry for entry in catalog.get("supported_read_commands") or []}
    return [
        _navigation_item(
            "overview",
            "dashboard_mart_view",
            commands["operator_dashboard_view"],
            selected=True,
        ),
        _navigation_item(
            "product_trace",
            "product_drill_down",
            commands["operator_product_drill_down"],
            selected=selected_product_id is not None,
            selected_params={"product_id": selected_product_id},
        ),
        _navigation_item(
            "review_queue",
            "review_queue_view",
            commands["operator_review_queue"],
        ),
        _navigation_item(
            "task_inspection",
            "task_inspection_view",
            commands["operator_task_inspection"],
            selected=task_id is not None or task_status is not None,
            selected_params={"task_id": task_id, "status": task_status},
        ),
        _navigation_item(
            "contract_catalog",
            "operator_api_contract_catalog",
            commands["operator_api_contract"],
        ),
    ]


def _navigation_item(
    nav_id: str,
    view_type: str,
    command: dict[str, Any],
    *,
    selected: bool = False,
    selected_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    params = {key: value for key, value in (selected_params or {}).items() if value is not None}
    return {
        "nav_id": nav_id,
        "view_type": view_type,
        "operator_read_command": command["command"],
        "required_params": list(command["required_params"]),
        "optional_params": list(command["optional_params"]),
        "required_context": list(command["required_context"]),
        "selected": selected,
        "selected_params": params,
        "read_only": True,
    }


def _preview_evidence_refs(service_reads: dict[str, Any]) -> list[dict[str, Any]]:
    refs = list(_PHASE2_4_EVIDENCE_REFS)
    dashboard = service_reads.get("dashboard_mart_view") or {}
    refs.extend(dashboard.get("evidence_refs") or [])
    product = service_reads.get("product_drill_down") or {}
    refs.extend(product.get("evidence_refs") or [])
    review = service_reads.get("review_queue_view") or {}
    refs.extend(review.get("evidence_refs") or [])
    task = service_reads.get("task_inspection_view") or {}
    refs.extend(task.get("evidence_refs") or [])
    return refs


def _preview_contract_checks(preview_model: dict[str, Any]) -> dict[str, Any]:
    checks = [
        _contract_check("phase2_4_audit", preview_model["audit"].get("phase") == "Phase2-4"),
        _contract_check("read_only_audit", preview_model["audit"].get("read_only") is True),
        _contract_check("no_audit_side_effects", preview_model["audit"].get("side_effects") == []),
        _contract_check(
            "production_frontend_framework_unfrozen",
            preview_model["framework_policy"].get("production_dashboard_framework_frozen") is False,
        ),
        _contract_check("no_framework_binding", preview_model["framework_policy"].get("framework_binding") is None),
        _contract_check(
            "no_frontend_completion_claim",
            preview_model["framework_policy"].get("frontend_completion_claimed") is False,
        ),
        _contract_check("no_approved_write_operations", _approved_write_operations(preview_model) == []),
        _contract_check("task_submission_blocked", "task_submission" in preview_model["blocked_actions"]),
        _contract_check("review_resolution_blocked", "review_resolution" in preview_model["blocked_actions"]),
        _contract_check("replay_trigger_blocked", "replay_trigger" in preview_model["blocked_actions"]),
        _contract_check("runtime_cutover_blocked", "runtime_cutover" in preview_model["blocked_actions"]),
        _contract_check("cutover_not_eligible", preview_model["cutover_guardrails"].get("cutover_eligible") is False),
        _contract_check(
            "runtime_cutover_not_executed",
            preview_model["cutover_guardrails"].get("runtime_cutover_executed") is False,
        ),
        _contract_check(
            "production_db_readiness_not_claimed",
            preview_model["cutover_guardrails"].get("production_db_readiness_claimed") is False,
        ),
        _contract_check(
            "db_backed_runtime_not_default",
            preview_model["cutover_guardrails"].get("db_backed_runtime_default") is False,
        ),
    ]
    return {
        "all_passed": all(check["passed"] for check in checks),
        "check_count": len(checks),
        "passed_count": sum(1 for check in checks if check["passed"]),
        "checks": checks,
    }


def _approved_write_operations(preview_model: dict[str, Any]) -> list[Any]:
    contract = preview_model["service_reads"].get("operator_api_contract") or {}
    operations = contract.get("approved_write_operations")
    return list(operations) if isinstance(operations, list) else []


def _contract_check(check_id: str, passed: bool) -> dict[str, Any]:
    return {"check_id": check_id, "passed": passed}


def _child_request_id(request_id: str | None, suffix: str) -> str | None:
    return f"{request_id}:{suffix}" if request_id else None


def _validate_optional_string(value: object, field_name: str) -> None:
    if value is not None and (not isinstance(value, str) or not value):
        raise ContractValidationError(f"{field_name} must be a non-empty string")


def _validate_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ContractValidationError(f"{field_name} must be a boolean")


def _validate_optional_task_status(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value:
        raise ContractValidationError("task_status must be a non-empty string")
    if value not in TASK_STATUSES:
        raise ContractValidationError(f"Unsupported task status filter: {value}")
