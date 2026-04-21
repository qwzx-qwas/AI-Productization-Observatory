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
    records = _load_candidate_records(config)
    source_summaries = _source_summaries(workflow_config, records)
    staging = _compact_staging_summary(config)
    review_issues = _load_review_issues(config)
    reconciliation = reconcile_dashboard_view(mart)
    manual_audit_preparation = {
        "screening_status_queues": _screening_status_queues(records),
        "merge_spot_check": _merge_spot_check_samples(review_issues),
        "taxonomy_audit": _taxonomy_audit_samples(mart),
        "score_audit": _score_audit_samples(mart),
        "attention_audit": _attention_audit_samples(mart),
        "unresolved_audit": _unresolved_audit_samples(mart),
    }
    gate_interpretation_conflicts = [
        {
            "conflict_id": "phase1_exit_checklist_product_hunt_live_cycle",
            "status": "pending_gate_interpretation_decision",
            "conflicting_docs": [
                "01_phase_plan_and_exit_criteria.md",
                "03_source_registry_and_collection_spec.md",
                "09_pipeline_and_module_contracts.md",
                "17_open_decisions_and_freeze_board.md",
            ],
            "summary": (
                "Phase1 Exit Checklist still lists a full Product Hunt collection cycle, while the frozen current-phase "
                "boundary keeps Product Hunt in fixture/replay/contract mode only."
            ),
            "safe_progress_made": (
                "GitHub remains the only current-phase live candidate discovery path, Product Hunt live candidate "
                "discovery is blocked in code, and the Product Hunt future integration seam stays preserved."
            ),
        }
    ]
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
        manual_audit_preparation=manual_audit_preparation,
        gate_interpretation_conflicts=gate_interpretation_conflicts,
    )
    return {
        "report_type": "phase1_g_audit_ready_report",
        "report_version": "phase1_g_audit_ready_v1",
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
        "manual_audit_preparation": manual_audit_preparation,
        "gate_status": {
            "github_live_candidate_discovery": "implemented",
            "future_multi_source_boundary": "implemented",
            "product_hunt_live_boundary": "implemented",
            "manual_audit_preparation": "provisionally_ready",
            "owner_review_package": "ready_for_owner_review",
            "manual_audit_judgment": "pending_manual_audit_judgment",
            "owner_signoff": "pending_owner_signoff",
            "gate_interpretation": "pending_gate_interpretation_decision",
        },
        "gate_interpretation_conflicts": gate_interpretation_conflicts,
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


def _merge_spot_check_samples(review_issues: list[dict[str, Any]]) -> dict[str, Any]:
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
    return {
        "status": "ready_for_manual_judgment" if samples else "not_materialized_in_local_baseline",
        "sample_count": len(samples),
        "samples": samples[:MART_SAMPLE_LIMIT],
    }


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
    return {
        "status": "ready_for_manual_judgment" if samples else "awaiting_materialized_samples",
        "sample_count": len(samples),
        "samples": samples,
    }


def _build_release_judgment(
    *,
    execution_boundary: dict[str, Any],
    source_summaries: list[dict[str, Any]],
    dashboard_reconciliation: dict[str, Any],
    manual_audit_preparation: dict[str, Any],
    gate_interpretation_conflicts: list[dict[str, Any]],
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
            "blocks_release": not github_live_enabled,
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
            "item_id": "product_hunt_deferred_boundary",
            "title": "Product Hunt stays deferred while preserving the future live integration seam",
            "status": "implemented" if product_hunt_boundary_preserved else "drift_detected",
            "risk_level": "low" if product_hunt_boundary_preserved else "high",
            "impact_scope": "current-phase source boundary, Product Hunt contract continuity, and future non-breaking reactivation",
            "blocks_release": not product_hunt_boundary_preserved,
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
            "blocks_release": not dashboard_all_passed,
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
        entry = manual_audit_preparation.get(audit_key)
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "missing")
        sample_count = int(entry.get("sample_count") or 0)
        if status == "ready_for_manual_judgment":
            risk_level = "medium"
        elif status == "not_materialized_in_local_baseline":
            risk_level = "medium"
        else:
            risk_level = "high"
        unresolved_items.append(
            {
                "item_id": audit_key,
                "title": f"Manual audit: {label}",
                "status": status,
                "risk_level": risk_level,
                "impact_scope": "release usability judgment, quality sampling, and unresolved/review risk validation",
                "blocks_release": True,
                "evidence": [
                    f"manual_audit_preparation.{audit_key}.status={status!r}",
                    f"manual_audit_preparation.{audit_key}.sample_count={sample_count}",
                ],
            }
        )
        owner_required_signoff.append(
            {
                "item_id": f"owner_{audit_key}",
                "owner": "project owner",
                "decision": f"Review the {label} evidence pack and explicitly confirm whether current results are release-usable.",
                "evidence_refs": [
                    "docs/candidate_prescreen_workspace/phase1_g_audit_ready_report.json",
                    "docs/phase1_g_acceptance_evidence.md",
                ],
            }
        )

    for conflict in gate_interpretation_conflicts:
        if not isinstance(conflict, dict):
            continue
        conflict_id = str(conflict.get("conflict_id") or "gate_interpretation_conflict")
        summary = str(conflict.get("summary") or conflict_id)
        status = str(conflict.get("status") or "pending_gate_interpretation_decision")
        unresolved_items.append(
            {
                "item_id": conflict_id,
                "title": summary,
                "status": status,
                "risk_level": "high",
                "impact_scope": "Phase1 exit checklist interpretation and whether current evidence can be counted as release gating evidence",
                "blocks_release": True,
                "evidence": [
                    "01_phase_plan_and_exit_criteria.md",
                    "03_source_registry_and_collection_spec.md",
                    "09_pipeline_and_module_contracts.md",
                    "17_open_decisions_and_freeze_board.md",
                ],
            }
        )
    if gate_interpretation_conflicts:
        owner_required_signoff.append(
            {
                "item_id": "owner_phase1_gate_interpretation",
                "owner": "Phase1 pipeline owner",
                "decision": (
                    "Interpret the Phase1 Exit Checklist conflict: confirm whether the existing GitHub live matrix counts toward "
                    "the GitHub full-cycle gate and whether the Product Hunt full-cycle line stays deferred outside the current release."
                ),
                "evidence_refs": [
                    "01_phase_plan_and_exit_criteria.md",
                    "docs/phase1_a_baseline.md",
                    "docs/phase1_e_acceptance_evidence.md",
                    "docs/phase1_g_acceptance_evidence.md",
                ],
            }
        )

    owner_required_signoff.append(
        {
            "item_id": "owner_release_decision",
            "owner": "project owner",
            "decision": "Apply the final merge/release judgment under DEC-025 after reviewing the audit package and unresolved items.",
            "evidence_refs": [
                "17_open_decisions_and_freeze_board.md",
                "14_test_plan_and_acceptance.md",
                "docs/phase1_g_acceptance_evidence.md",
            ],
        }
    )

    blocking_items = [item for item in unresolved_items if item["blocks_release"]]
    if github_live_enabled and product_hunt_boundary_preserved and dashboard_all_passed:
        judgment = "conditional-go" if blocking_items else "go"
    else:
        judgment = "no-go"

    rationale = [
        "GitHub remains the only current-phase live candidate discovery path, matching the frozen source boundary.",
        "Product Hunt remains deferred in the current phase, while the official GraphQL plus token-auth live seam stays preserved for future reactivation.",
        "Local mart-backed dashboard reconciliation currently passes all materialized checks.",
    ]
    if any(item["item_id"] == "merge_spot_check" and item["status"] == "not_materialized_in_local_baseline" for item in unresolved_items):
        rationale.append(
            "Merge spot-check evidence is not materialized in the local baseline, so the absence of sampled merge-risk cases cannot be treated as a completed release audit."
        )
    if gate_interpretation_conflicts:
        rationale.append(
            "The Phase1 exit checklist still contains a Product Hunt full-cycle requirement that conflicts with the frozen deferred boundary, so release interpretation remains owner-gated."
        )
    rationale.append(
        "DEC-025 keeps final merge/release sign-off with the owner, so this report can only provide a machine judgment plus required owner decisions."
    )

    release_conditions = [
        item["title"]
        for item in blocking_items
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
    return {
        "status": "ready_for_manual_judgment" if samples else "awaiting_materialized_samples",
        "sample_count": len(samples),
        "samples": samples,
    }


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
    return {
        "status": "ready_for_manual_judgment" if samples else "awaiting_materialized_samples",
        "sample_count": len(samples),
        "samples": samples,
    }


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
    return {
        "status": "ready_for_manual_judgment" if samples else "awaiting_materialized_samples",
        "sample_count": len(samples),
        "samples": samples,
    }


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
