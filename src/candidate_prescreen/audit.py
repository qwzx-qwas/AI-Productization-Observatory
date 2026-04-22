"""Audit-ready report helpers for the Phase1-G candidate prescreen baseline."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.candidate_prescreen.config import (
    discovery_capabilities_config,
    execution_boundary_config,
    load_candidate_prescreen_config,
)
from src.candidate_prescreen.workflow import (
    candidate_record_paths,
    candidate_record_preference_key,
    sample_key_from_record,
    validate_candidate_record,
)
from src.common.config import AppConfig
from src.common.files import dump_json, load_json, load_yaml, utc_now_iso
from src.marts.presentation import build_product_drill_down, reconcile_dashboard_view
from src.review.store import default_review_issue_store_path

DEFAULT_PHASE1_G_AUDIT_REPORT_FILE_NAME = "phase1_g_audit_ready_report.json"
SCREENING_SAMPLE_LIMIT = 12
MART_SAMPLE_LIMIT = 8
AUDIT_WRITEBACK_KEYS = (
    "merge_spot_check",
    "taxonomy_audit",
    "score_audit",
    "attention_audit",
    "unresolved_audit",
)


def default_phase1_g_audit_report_path(config: AppConfig) -> Path:
    return config.candidate_workspace_dir / DEFAULT_PHASE1_G_AUDIT_REPORT_FILE_NAME


def write_phase1_g_audit_ready_report(
    config: AppConfig,
    *,
    mart: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    report = build_phase1_g_audit_ready_report(config, mart=mart)
    dump_json(output_path or default_phase1_g_audit_report_path(config), report)
    return report


def build_phase1_g_audit_ready_report(config: AppConfig, *, mart: dict[str, Any]) -> dict[str, Any]:
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    execution_boundary = execution_boundary_config(workflow_config)
    existing_report = _load_existing_phase1_g_report(config)
    records = _load_candidate_records(config)
    source_summaries = _source_summaries(workflow_config, records)
    staging = _compact_staging_summary(config)
    review_issues = _load_review_issues(config)
    reconciliation = reconcile_dashboard_view(mart)
    audit_workflow = {
        "screening_status_queues": _screening_status_queues(records),
        "merge_spot_check": _merge_spot_check_audit(review_issues),
        "taxonomy_audit": _taxonomy_audit_samples(mart),
        "score_audit": _score_audit_samples(mart),
        "attention_audit": _attention_audit_samples(mart),
        "unresolved_audit": _unresolved_audit_samples(mart),
    }
    audit_workflow = _apply_manual_audit_writebacks(audit_workflow, existing_report)
    release_owner_signoff = _apply_manual_release_owner_signoff(existing_report)
    release_judgment = _build_release_judgment(
        execution_boundary=execution_boundary,
        source_summaries=source_summaries,
        dashboard_reconciliation={
            "window_start": reconciliation["window_start"],
            "window_end": reconciliation["window_end"],
            "check_count": reconciliation["check_count"],
            "passed_count": reconciliation["passed_count"],
            "pass_rate": reconciliation["pass_rate"],
            "all_passed": reconciliation["all_passed"],
        },
        audit_workflow=audit_workflow,
        release_owner_signoff=release_owner_signoff,
    )
    report_title = (
        f"Phase1-G audit-ready / owner-review-ready / {release_judgment['judgment']}"
    )
    return {
        "report_type": "phase1_g_audit_ready_report",
        "report_version": "phase1_g_audit_ready_v2",
        "report_title": report_title,
        "report_summary": {
            "status_labels": ["audit-ready", "owner-review-ready", release_judgment["judgment"]],
            "machine_tendency": release_judgment["judgment"],
            "summary": _report_summary_for_judgment(release_judgment["judgment"]),
        },
        "generated_at": utc_now_iso(),
        "execution_boundary": {
            "current_phase_default_live_source": execution_boundary.get("current_phase_default_live_source"),
            "product_hunt_current_phase_mode": execution_boundary.get("product_hunt_current_phase_mode"),
            "product_hunt_live_discovery_status": execution_boundary.get("product_hunt_live_discovery_status"),
            "product_hunt_future_live_path": execution_boundary.get("product_hunt_future_live_path"),
        },
        "source_runtime_boundaries": source_summaries,
        "workspace_summary": {
            "candidate_document_count": len(records),
            "sources": source_summaries,
        },
        "staging_summary": staging,
        "dashboard_reconciliation": {
            "window_start": reconciliation["window_start"],
            "window_end": reconciliation["window_end"],
            "check_count": reconciliation["check_count"],
            "passed_count": reconciliation["passed_count"],
            "pass_rate": reconciliation["pass_rate"],
            "all_passed": reconciliation["all_passed"],
        },
        "audit_workflow": audit_workflow,
        "gate_status": {
            "github_live_candidate_discovery": "implemented",
            "future_multi_source_boundary": "implemented",
            "product_hunt_phase1_exit_gate": "deferred_not_current_gate",
            "machine_pre_audit": "audit-ready",
            "human_sampled_verdict": _aggregate_human_sampled_verdict_status(audit_workflow),
            "owner_review_package": "owner-review-ready",
            "owner_signoff": release_owner_signoff["status"],
        },
        "release_owner_signoff": release_owner_signoff,
        "release_judgment": release_judgment,
        "evidence_pack": {
            "candidate_workspace_dir": str(config.candidate_workspace_dir),
            "gold_set_staging_dir": str(config.gold_set_staging_dir),
            "review_issue_store_path": str(default_review_issue_store_path(config.task_store_path)),
            "phase1_g_acceptance_evidence_path": str(config.repo_root / "docs" / "phase1_g_acceptance_evidence.md"),
            "fill_audit_log_path": str(config.candidate_workspace_dir / "fill_gold_set_staging_audit.jsonl"),
            "phase1_g_audit_ready_report_path": str(default_phase1_g_audit_report_path(config)),
        },
    }


def _load_existing_phase1_g_report(config: AppConfig) -> dict[str, Any]:
    report_path = default_phase1_g_audit_report_path(config)
    if not report_path.exists():
        return {}
    payload = load_json(report_path)
    return payload if isinstance(payload, dict) else {}


def _apply_manual_audit_writebacks(
    audit_workflow: dict[str, Any],
    existing_report: dict[str, Any],
) -> dict[str, Any]:
    existing_workflow = existing_report.get("audit_workflow")
    if not isinstance(existing_workflow, dict):
        return audit_workflow

    for audit_key in AUDIT_WRITEBACK_KEYS:
        current_entry = audit_workflow.get(audit_key)
        existing_entry = existing_workflow.get(audit_key)
        if not isinstance(current_entry, dict) or not isinstance(existing_entry, dict):
            continue
        current_entry["human_sampled_verdict"] = _normalize_human_sampled_verdict(
            _merge_manual_mapping(
                current_entry.get("human_sampled_verdict"),
                existing_entry.get("human_sampled_verdict"),
            )
        )
        current_entry["owner_signoff"] = _merge_manual_mapping(
            current_entry.get("owner_signoff"),
            existing_entry.get("owner_signoff"),
        )
    return audit_workflow


def _apply_manual_release_owner_signoff(existing_report: dict[str, Any]) -> dict[str, Any]:
    return _merge_manual_mapping(
        _pending_release_owner_signoff(),
        existing_report.get("release_owner_signoff"),
    )


def _merge_manual_mapping(default_value: Any, existing_value: Any) -> dict[str, Any]:
    merged = default_value if isinstance(default_value, dict) else {}
    if not isinstance(existing_value, dict):
        return dict(merged)
    result = dict(merged)
    result.update(existing_value)
    return result


def _aggregate_human_sampled_verdict_status(audit_workflow: dict[str, Any]) -> str:
    statuses: list[str] = []
    for audit_key in AUDIT_WRITEBACK_KEYS:
        entry = audit_workflow.get(audit_key)
        verdict = entry.get("human_sampled_verdict") if isinstance(entry, dict) else {}
        statuses.append(_human_verdict_workflow_status(verdict))
    if any(status == "flagged" for status in statuses):
        return "flagged"
    if statuses and all(status == "completed" for status in statuses):
        return "completed"
    return "pending"


def _report_summary_for_judgment(judgment: str) -> str:
    if judgment == "go":
        return (
            "Machine pre-audit artifacts, sampled human verdicts, and owner sign-off are all recorded for the "
            "current Phase1-G audit package; Product Hunt remains deferred outside the current exit gate, and the "
            "report shows no blocking release conditions."
        )
    if judgment == "no-go":
        return (
            "At least one blocking machine-pre-audit or sign-off condition remains open or rejected in the current "
            "Phase1-G audit package, so the report cannot support a release go judgment."
        )
    return (
        "Machine pre-audit artifacts are materialized for the current Phase1-G audit package, Product Hunt remains "
        "deferred outside the current exit gate, and final go stays owner-gated until sampled human verdicts and "
        "owner sign-off are completed."
    )


def _load_candidate_records(config: AppConfig) -> list[tuple[Path, dict[str, Any]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    for candidate_path in candidate_record_paths(config):
        payload = load_yaml(candidate_path)
        if not isinstance(payload, dict):
            continue
        validate_candidate_record(config, payload)
        records.append((candidate_path, payload))
    return records


def _source_summaries(
    workflow_config: dict[str, Any],
    records: list[tuple[Path, dict[str, Any]]],
) -> list[dict[str, Any]]:
    records_by_source: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    for entry in records:
        records_by_source[str(entry[1].get("source") or "")].append(entry)

    summaries: list[dict[str, Any]] = []
    sources = workflow_config.get("sources")
    if not isinstance(sources, list):
        return summaries

    for source_entry in sources:
        if not isinstance(source_entry, dict):
            continue
        source_code = str(source_entry.get("source_code") or "")
        source_records = records_by_source.get(source_code, [])
        capabilities = discovery_capabilities_config(workflow_config, source_code)
        human_status_counts = Counter(str(record.get("human_review_status") or "") for _, record in source_records)
        llm_status_counts = Counter(
            str((record.get("llm_prescreen") or {}).get("status") or "missing") for _, record in source_records
        )
        handoff_status_counts = Counter(
            str((record.get("staging_handoff") or {}).get("status") or "missing") for _, record in source_records
        )
        windows = sorted({str(record.get("source_window") or "") for _, record in source_records if record.get("source_window")})
        query_slice_ids = sorted(
            {str(record.get("query_slice_id") or "") for _, record in source_records if record.get("query_slice_id")}
        )
        discovery_modes = sorted(
            {
                str(((record.get("source_trace") or {}).get("discovery_mode")) or "")
                for _, record in source_records
                if ((record.get("source_trace") or {}).get("discovery_mode"))
            }
        )
        summaries.append(
            {
                "source_code": source_code,
                "source_id": source_entry.get("source_id"),
                "source_name": _source_name(source_code),
                "candidate_document_count": len(source_records),
                "current_phase_runtime_note": source_entry.get("current_phase_runtime_note"),
                "discovery_capabilities": {
                    "fixture_supported": capabilities.get("fixture_supported"),
                    "replay_supported": capabilities.get("replay_supported"),
                    "live_supported": capabilities.get("live_supported"),
                    "live_enabled_in_current_phase": capabilities.get("live_enabled_in_current_phase"),
                    "current_phase_live_status": capabilities.get("current_phase_live_status"),
                    "future_live_boundary_preserved": capabilities.get("future_live_boundary_preserved"),
                },
                "human_review_status_counts": dict(sorted(human_status_counts.items())),
                "llm_prescreen_status_counts": dict(sorted(llm_status_counts.items())),
                "staging_handoff_status_counts": dict(sorted(handoff_status_counts.items())),
                "windows": windows,
                "query_slice_ids": query_slice_ids,
                "discovery_modes": discovery_modes,
            }
        )
    return summaries


def _source_name(source_code: str) -> str:
    if source_code == "github":
        return "GitHub"
    if source_code == "product_hunt":
        return "Product Hunt"
    return source_code


def _compact_staging_summary(config: AppConfig) -> dict[str, Any]:
    from src.candidate_prescreen.staging import staging_progress

    progress = staging_progress(config.gold_set_staging_dir)
    return {
        "total_slots": progress["total_slots"],
        "total_filled": progress["total_filled"],
        "total_empty": progress["total_empty"],
        "is_complete": progress["is_complete"],
        "next_open_slot": progress["next_open_slot"],
    }


def _screening_status_queues(records: list[tuple[Path, dict[str, Any]]]) -> dict[str, Any]:
    queues: dict[str, Any] = {}
    for status in ("approved_for_staging", "rejected_after_human_review", "on_hold"):
        matching = [(path, record) for path, record in records if record.get("human_review_status") == status]
        matching.sort(
            key=lambda item: candidate_record_preference_key(item[1], item[0]),
            reverse=True,
        )
        queues[status] = {
            "status": "ready_for_manual_judgment" if matching else "awaiting_materialized_samples",
            "sample_count": len(matching),
            "samples": [_candidate_sample(path, record) for path, record in matching[:SCREENING_SAMPLE_LIMIT]],
        }
    return queues


def _candidate_sample(candidate_path: Path, record: dict[str, Any]) -> dict[str, Any]:
    llm_prescreen = record.get("llm_prescreen")
    channel_metadata = llm_prescreen.get("channel_metadata") if isinstance(llm_prescreen, dict) else {}
    return {
        "candidate_id": record.get("candidate_id"),
        "sample_key": sample_key_from_record(record),
        "source": record.get("source"),
        "source_window": record.get("source_window"),
        "query_slice_id": record.get("query_slice_id"),
        "selection_rule_version": record.get("selection_rule_version"),
        "title": record.get("title"),
        "canonical_url": record.get("canonical_url"),
        "human_review_status": record.get("human_review_status"),
        "staging_handoff_status": (record.get("staging_handoff") or {}).get("status"),
        "llm_prescreen_status": llm_prescreen.get("status") if isinstance(llm_prescreen, dict) else None,
        "recommended_action": llm_prescreen.get("recommended_action") if isinstance(llm_prescreen, dict) else None,
        "reason": llm_prescreen.get("reason") if isinstance(llm_prescreen, dict) else None,
        "confidence_summary": llm_prescreen.get("confidence_summary") if isinstance(llm_prescreen, dict) else None,
        "request_id": channel_metadata.get("request_id") if isinstance(channel_metadata, dict) else None,
        "candidate_document_path": str(candidate_path),
    }


def _load_review_issues(config: AppConfig) -> list[dict[str, Any]]:
    store_path = default_review_issue_store_path(config.task_store_path)
    if not store_path.exists():
        return []
    payload = load_json(store_path)
    return payload if isinstance(payload, list) else []


def _pending_human_sampled_verdict(label: str, *, sampled_method: str = "pending_human_sampling") -> dict[str, Any]:
    return {
        "status": "pending",
        "review_verdict": "pending",
        "sampled_count": 0,
        "sampled_method": sampled_method,
        "reviewer_notes": (
            f"Pending human sampled verdict for {label}; Codex has materialized the machine pre-audit evidence pack "
            "without claiming a final human judgment."
        ),
    }


def _human_verdict_workflow_status(human_sampled_verdict: Any) -> str:
    if not isinstance(human_sampled_verdict, dict):
        return "pending"

    status = str(human_sampled_verdict.get("status") or "pending")
    if status == "accepted":
        return "completed"
    if status == "rejected":
        return "flagged"
    if status in {"pending", "completed", "flagged"}:
        return status
    return "pending"


def _human_verdict_review_outcome(human_sampled_verdict: Any) -> str:
    if not isinstance(human_sampled_verdict, dict):
        return "pending"

    review_verdict = str(human_sampled_verdict.get("review_verdict") or "").strip().lower()
    if review_verdict in {"accept", "reject", "pending"}:
        return review_verdict

    status = str(human_sampled_verdict.get("status") or "pending")
    if status == "accepted":
        return "accept"
    if status == "rejected":
        return "reject"
    return "pending"


def _normalize_human_sampled_verdict(human_sampled_verdict: Any) -> dict[str, Any]:
    if not isinstance(human_sampled_verdict, dict):
        return dict(_pending_human_sampled_verdict("audit"))

    normalized = dict(human_sampled_verdict)
    normalized["status"] = _human_verdict_workflow_status(human_sampled_verdict)
    normalized["review_verdict"] = _human_verdict_review_outcome(human_sampled_verdict)
    return normalized


def _pending_owner_signoff(label: str) -> dict[str, Any]:
    return {
        "status": "pending",
        "signoff_by": None,
        "signoff_at": None,
        "signoff_notes": (
            f"Pending owner sign-off for {label}; DEC-025 and DEC-029 keep the final merge/release approval with the owner."
        ),
    }


def _pending_release_owner_signoff() -> dict[str, Any]:
    return {
        "status": "pending",
        "signoff_by": None,
        "signoff_at": None,
        "signoff_notes": (
            "Pending final owner merge/release sign-off after the sampled human verdicts are recorded and all blocking "
            "conditions are closed."
        ),
    }


def _build_audit_track(
    *,
    label: str,
    machine_status: str,
    sample_scope: str,
    evidence_refs: list[str],
    samples: list[dict[str, Any]],
    human_sampled_method: str = "pending_human_sampling",
) -> dict[str, Any]:
    return {
        "audit_label": label,
        "machine_pre_audit": {
            "status": machine_status,
            "sample_scope": sample_scope,
            "evidence_refs": evidence_refs,
            "sample_count": len(samples),
            "samples": samples,
        },
        "human_sampled_verdict": _pending_human_sampled_verdict(label, sampled_method=human_sampled_method),
        "owner_signoff": _pending_owner_signoff(label),
    }


def _merge_spot_check_audit(review_issues: list[dict[str, Any]]) -> dict[str, Any]:
    samples = []
    for issue in review_issues:
        if not isinstance(issue, dict) or issue.get("issue_type") != "entity_merge_uncertainty":
            continue
        samples.append(
            {
                "review_issue_id": issue.get("review_issue_id"),
                "priority_code": issue.get("priority_code"),
                "status": issue.get("status"),
                "target_summary": issue.get("target_summary"),
                "conflict_point": issue.get("conflict_point"),
                "recommended_action": issue.get("recommended_action"),
            }
        )
    limited_samples = samples[:MART_SAMPLE_LIMIT]
    return _build_audit_track(
        label="merge spot-check",
        machine_status="flagged" if limited_samples else "not_materialized",
        sample_scope="targeted",
        evidence_refs=[
            "review_issue_store_path",
            "docs/phase1_g_acceptance_evidence.md",
            "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
        ],
        samples=limited_samples,
        human_sampled_method="targeted_merge_risk_review",
    )


def _taxonomy_audit_samples(mart: dict[str, Any]) -> dict[str, Any]:
    fact_rows = mart.get("fact_product_observation") or []
    ranked = sorted(
        [row for row in fact_rows if isinstance(row, dict)],
        key=lambda row: (
            row.get("taxonomy_primary_code") or "",
            row.get("attention_normalized_value") is None,
            -(row.get("attention_normalized_value") or 0.0),
        ),
    )
    samples = [_mart_product_sample(mart, row) for row in ranked[:MART_SAMPLE_LIMIT]]
    return _build_audit_track(
        label="taxonomy audit",
        machine_status="passed" if samples else "not_materialized",
        sample_scope="stratified",
        evidence_refs=[
            "mart.fact_product_observation",
            "docs/phase1_g_acceptance_evidence.md",
            "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
        ],
        samples=samples,
        human_sampled_method="stratified_top_category_sampling",
    )


def _build_release_judgment(
    *,
    execution_boundary: dict[str, Any],
    source_summaries: list[dict[str, Any]],
    dashboard_reconciliation: dict[str, Any],
    audit_workflow: dict[str, Any],
    release_owner_signoff: dict[str, Any],
) -> dict[str, Any]:
    github_summary = next((summary for summary in source_summaries if summary.get("source_code") == "github"), None)
    product_hunt_summary = next((summary for summary in source_summaries if summary.get("source_code") == "product_hunt"), None)

    unresolved_items: list[dict[str, Any]] = []
    owner_required_signoff: list[dict[str, Any]] = []

    github_live_enabled = bool(
        isinstance(github_summary, dict)
        and isinstance(github_summary.get("discovery_capabilities"), dict)
        and github_summary["discovery_capabilities"].get("live_enabled_in_current_phase") is True
    )
    unresolved_items.append(
        {
            "item_id": "github_live_path",
            "title": "GitHub remains the only current-phase live candidate discovery path",
            "status": "implemented" if github_live_enabled else "missing",
            "risk_level": "low" if github_live_enabled else "high",
            "impact_scope": "current-phase live discovery coverage and operator default execution path",
            "blocks_machine_judgment": not github_live_enabled,
            "blocks_final_go": not github_live_enabled,
            "evidence": [
                f"execution_boundary.current_phase_default_live_source={execution_boundary.get('current_phase_default_live_source')!r}",
                "source_runtime_boundaries.github.discovery_capabilities.live_enabled_in_current_phase=true",
            ],
        }
    )

    product_hunt_boundary_preserved = bool(
        isinstance(product_hunt_summary, dict)
        and isinstance(product_hunt_summary.get("discovery_capabilities"), dict)
        and product_hunt_summary["discovery_capabilities"].get("live_supported") is True
        and product_hunt_summary["discovery_capabilities"].get("live_enabled_in_current_phase") is False
        and product_hunt_summary["discovery_capabilities"].get("future_live_boundary_preserved") is True
    )
    unresolved_items.append(
        {
            "item_id": "product_hunt_phase1_exit_gate",
            "title": "Product Hunt stays deferred outside the current Phase1 exit gate while preserving the future live seam",
            "status": "deferred_not_current_gate" if product_hunt_boundary_preserved else "drift_detected",
            "risk_level": "low" if product_hunt_boundary_preserved else "high",
            "impact_scope": "current-phase source boundary, exit-gate scope, Product Hunt contract continuity, and future non-breaking reactivation",
            "blocks_machine_judgment": not product_hunt_boundary_preserved,
            "blocks_final_go": not product_hunt_boundary_preserved,
            "evidence": [
                f"execution_boundary.product_hunt_current_phase_mode={execution_boundary.get('product_hunt_current_phase_mode')!r}",
                f"execution_boundary.product_hunt_live_discovery_status={execution_boundary.get('product_hunt_live_discovery_status')!r}",
                "source_runtime_boundaries.product_hunt.discovery_capabilities.live_supported=true",
                "source_runtime_boundaries.product_hunt.discovery_capabilities.live_enabled_in_current_phase=false",
                "source_runtime_boundaries.product_hunt.discovery_capabilities.future_live_boundary_preserved=true",
            ],
        }
    )

    dashboard_all_passed = dashboard_reconciliation.get("all_passed") is True
    unresolved_items.append(
        {
            "item_id": "dashboard_reconciliation",
            "title": "Mart-backed dashboard reconciliation baseline",
            "status": "passed" if dashboard_all_passed else "failed",
            "risk_level": "low" if dashboard_all_passed else "high",
            "impact_scope": "dashboard-facing consumption contract, drill-down traceability baseline, and local release usability signal",
            "blocks_machine_judgment": not dashboard_all_passed,
            "blocks_final_go": not dashboard_all_passed,
            "evidence": [
                f"dashboard_reconciliation.check_count={dashboard_reconciliation.get('check_count')}",
                f"dashboard_reconciliation.passed_count={dashboard_reconciliation.get('passed_count')}",
                f"dashboard_reconciliation.pass_rate={dashboard_reconciliation.get('pass_rate')}",
            ],
        }
    )

    audit_labels = {
        "merge_spot_check": "merge spot-check",
        "taxonomy_audit": "taxonomy audit",
        "score_audit": "score audit",
        "attention_audit": "attention audit",
        "unresolved_audit": "unresolved audit",
    }
    for audit_key, label in audit_labels.items():
        entry = audit_workflow.get(audit_key)
        if not isinstance(entry, dict):
            continue
        machine_pre_audit = entry.get("machine_pre_audit") if isinstance(entry.get("machine_pre_audit"), dict) else {}
        human_sampled_verdict = _normalize_human_sampled_verdict(entry.get("human_sampled_verdict"))
        owner_signoff = entry.get("owner_signoff") if isinstance(entry.get("owner_signoff"), dict) else {}
        machine_status = str(machine_pre_audit.get("status") or "missing")
        human_status = _human_verdict_workflow_status(human_sampled_verdict)
        human_review_verdict = _human_verdict_review_outcome(human_sampled_verdict)
        signoff_status = str(owner_signoff.get("status") or "pending")
        sample_count = int(machine_pre_audit.get("sample_count") or 0)
        if (
            machine_status == "flagged"
            or human_status == "flagged"
            or human_review_verdict == "reject"
            or signoff_status == "rejected"
        ):
            risk_level = "high"
        elif human_status == "pending" or signoff_status == "pending":
            risk_level = "medium"
        else:
            risk_level = "low"
        unresolved_items.append(
            {
                "item_id": audit_key,
                "title": f"Audit workflow: {label}",
                "status": machine_status,
                "risk_level": risk_level,
                "impact_scope": "machine pre-audit, sampled human review, and owner approval boundary for release usability validation",
                "blocks_machine_judgment": (
                    machine_status == "flagged"
                    or human_status == "flagged"
                    or human_review_verdict == "reject"
                    or signoff_status == "rejected"
                ),
                "blocks_final_go": (
                    human_status != "completed" or human_review_verdict != "accept" or signoff_status != "approved"
                ),
                "machine_pre_audit_status": machine_status,
                "human_sampled_verdict_status": human_status,
                "human_sampled_review_verdict": human_review_verdict,
                "owner_signoff_status": signoff_status,
                "evidence": [
                    f"audit_workflow.{audit_key}.machine_pre_audit.status={machine_status!r}",
                    f"audit_workflow.{audit_key}.machine_pre_audit.sample_count={sample_count}",
                    f"audit_workflow.{audit_key}.human_sampled_verdict.status={human_status!r}",
                    f"audit_workflow.{audit_key}.human_sampled_verdict.review_verdict={human_review_verdict!r}",
                    f"audit_workflow.{audit_key}.owner_signoff.status={signoff_status!r}",
                ],
            }
        )
        owner_required_signoff.append(
            {
                "item_id": f"owner_{audit_key}",
                "owner": "project owner",
                "status": signoff_status,
                "decision": (
                    f"Review the {label} machine pre-audit and the sampled human verdict, then explicitly record the owner sign-off status."
                ),
                "evidence_refs": [
                    "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
                    "docs/phase1_g_acceptance_evidence.md",
                ],
            }
        )

    owner_required_signoff.append(
        {
            "item_id": "owner_release_decision",
            "owner": "project owner",
            "status": str(release_owner_signoff.get("status") or "pending"),
            "decision": (
                "Apply the final merge/release judgment under DEC-025 and DEC-029 after reviewing the audit package, "
                "sampled human verdicts, and unresolved items."
            ),
            "evidence_refs": [
                "17_open_decisions_and_freeze_board.md",
                "14_test_plan_and_acceptance.md",
                "docs/phase1_g_acceptance_evidence.md",
            ],
        }
    )
    release_owner_status = str(release_owner_signoff.get("status") or "pending")
    unresolved_items.append(
        {
            "item_id": "release_owner_signoff",
            "title": "Final owner merge/release sign-off",
            "status": release_owner_status,
            "risk_level": (
                "high" if release_owner_status == "rejected" else "low" if release_owner_status == "approved" else "medium"
            ),
            "impact_scope": "final release approval boundary after machine pre-audit and sampled human verdicts",
            "blocks_machine_judgment": release_owner_status == "rejected",
            "blocks_final_go": release_owner_status != "approved",
            "evidence": [
                f"release_owner_signoff.status={release_owner_status!r}",
                "17_open_decisions_and_freeze_board.md",
                "14_test_plan_and_acceptance.md",
            ],
        }
    )

    machine_blockers = [item for item in unresolved_items if item["blocks_machine_judgment"]]
    final_go_blockers = [item for item in unresolved_items if item["blocks_final_go"]]
    release_owner_approved = release_owner_status == "approved"
    if machine_blockers:
        judgment = "no-go"
    elif final_go_blockers or not release_owner_approved:
        judgment = "conditional-go"
    else:
        judgment = "go"

    rationale = [
        "GitHub remains the only current-phase live candidate discovery path, matching the frozen source boundary.",
        "DEC-029 freezes Product Hunt as deferred for the current Phase1 exit gate while preserving the official GraphQL plus token-auth future live seam.",
        "Local mart-backed dashboard reconciliation currently passes all materialized checks.",
        "The five release audits now follow a structured machine_pre_audit -> human_sampled_verdict -> owner_signoff workflow, so machine output can only be conditional-go or no-go until owner approval is recorded.",
    ]
    if any(item["item_id"] == "merge_spot_check" and item["status"] == "not_materialized" for item in unresolved_items):
        rationale.append(
            "Merge spot-check currently has no materialized merge-risk cases in the local baseline, so the release package records the empty-case baseline explicitly through the assigned sampled review pack."
        )
    if release_owner_status == "approved":
        rationale.append(
            "DEC-025 keeps final merge/release sign-off with the owner, and the current report includes that recorded owner decision alongside the audit evidence."
        )
    else:
        rationale.append(
            "DEC-025 keeps final merge/release sign-off with the owner, so this report can only provide an audit-ready machine tendency plus the required pending owner decisions."
        )

    release_conditions = [
        item["title"]
        for item in final_go_blockers
    ]
    return {
        "judgment": judgment,
        "rationale": rationale,
        "unresolved_audit_summary": unresolved_items,
        "release_conditions": release_conditions,
        "owner_required_signoff": owner_required_signoff,
    }


def _score_audit_samples(mart: dict[str, Any]) -> dict[str, Any]:
    fact_rows = mart.get("fact_product_observation") or []
    ranked = sorted(
        [
            row
            for row in fact_rows
            if isinstance(row, dict)
            and (row.get("build_evidence_band") == "high" or row.get("attention_band") == "high")
        ],
        key=lambda row: (
            row.get("build_evidence_band") != "high",
            row.get("attention_band") != "high",
            -(row.get("attention_normalized_value") or 0.0),
        ),
    )
    samples = [_mart_product_sample(mart, row) for row in ranked[:MART_SAMPLE_LIMIT]]
    return _build_audit_track(
        label="score audit",
        machine_status="passed" if samples else "not_materialized",
        sample_scope="targeted",
        evidence_refs=[
            "mart.fact_product_observation",
            "docs/phase1_g_acceptance_evidence.md",
            "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
        ],
        samples=samples,
        human_sampled_method="targeted_high_signal_score_sampling",
    )


def _attention_audit_samples(mart: dict[str, Any]) -> dict[str, Any]:
    fact_rows = mart.get("fact_product_observation") or []
    ranked = sorted(
        [
            row
            for row in fact_rows
            if isinstance(row, dict) and (row.get("attention_band") == "high" or row.get("attention_band") is None)
        ],
        key=lambda row: (
            row.get("attention_band") != "high",
            -(row.get("attention_raw_value") or 0),
        ),
    )
    samples = [_mart_product_sample(mart, row) for row in ranked[:MART_SAMPLE_LIMIT]]
    return _build_audit_track(
        label="attention audit",
        machine_status="passed" if samples else "not_materialized",
        sample_scope="stratified",
        evidence_refs=[
            "mart.fact_product_observation",
            "configs/source_metric_registry.yaml",
            "docs/phase1_g_acceptance_evidence.md",
        ],
        samples=samples,
        human_sampled_method="stratified_attention_band_sampling",
    )


def _unresolved_audit_samples(mart: dict[str, Any]) -> dict[str, Any]:
    unresolved_rows = mart.get("unresolved_registry_view") or []
    samples: list[dict[str, Any]] = []
    for unresolved in unresolved_rows[:MART_SAMPLE_LIMIT]:
        if not isinstance(unresolved, dict):
            continue
        product_id = unresolved.get("target_id")
        if not isinstance(product_id, str) or not product_id:
            continue
        drill_down = build_product_drill_down(mart, product_id=product_id)
        samples.append(
            {
                "product_id": product_id,
                "review_issue_id": unresolved.get("review_issue_id"),
                "priority_code": unresolved.get("priority_code"),
                "resolution_action": unresolved.get("resolution_action"),
                "resolution_notes": unresolved.get("resolution_notes"),
                "effective_taxonomy_code": drill_down.get("effective_taxonomy_code"),
                "trace_refs": drill_down.get("trace_refs"),
            }
        )
    return _build_audit_track(
        label="unresolved audit",
        machine_status="passed" if samples else "not_materialized",
        sample_scope="full",
        evidence_refs=[
            "mart.unresolved_registry_view",
            "docs/phase1_g_acceptance_evidence.md",
            "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
        ],
        samples=samples,
        human_sampled_method="full_unresolved_registry_review",
    )


def _mart_product_sample(mart: dict[str, Any], fact_row: dict[str, Any]) -> dict[str, Any]:
    product_id = str(fact_row.get("product_id") or "")
    drill_down = build_product_drill_down(mart, product_id=product_id)
    product = drill_down.get("product") or {}
    return {
        "product_id": product_id,
        "normalized_name": product.get("normalized_name"),
        "source_id": fact_row.get("source_id"),
        "source_item_id": fact_row.get("source_item_id"),
        "observation_id": fact_row.get("observation_id"),
        "taxonomy_primary_code": fact_row.get("taxonomy_primary_code"),
        "attention_raw_value": fact_row.get("attention_raw_value"),
        "attention_normalized_value": fact_row.get("attention_normalized_value"),
        "attention_band": fact_row.get("attention_band"),
        "build_evidence_band": fact_row.get("build_evidence_band"),
        "commercial_band": fact_row.get("commercial_band"),
        "main_report_included": drill_down.get("main_report_included"),
        "trace_refs": drill_down.get("trace_refs"),
    }
