"""Review helpers for taxonomy-triggered review packets, writeback, and registry derivation."""

from __future__ import annotations

import hashlib
from typing import Any

from src.common.errors import ContractValidationError
from src.common.files import load_yaml, utc_now_iso
from src.common.schema import validate_instance

MODULE_NAME = "review_packet_builder"
TRIGGER_VERSION = "review_packet_builder_v1"
TAXONOMY_REVIEW_ISSUE_TYPES = {"taxonomy_low_confidence", "taxonomy_conflict"}
OPEN_REVIEW_STATUSES = {"open", "assigned", "in_review"}


def describe_contract() -> dict[str, str]:
    return {
        "module_name": MODULE_NAME,
        "status": "implemented_taxonomy_writeback_baseline",
        "run_unit": "per_review_trigger",
        "version_dependency": TRIGGER_VERSION,
    }


def build_taxonomy_review_issue(
    current_assignment: dict[str, Any],
    related_evidence: list[dict[str, Any]],
    *,
    target_summary: str,
    upstream_downstream_links: list[dict[str, Any]],
    config_dir,
    schema_dir,
    issue_type: str | None = None,
    priority_code: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    rules = load_yaml(config_dir / "review_rules_v0.yaml")
    packet_issue_type = issue_type or _infer_taxonomy_issue_type(current_assignment, related_evidence)
    _validate_issue_type(packet_issue_type, rules)
    _validate_priority(priority_code, rules, allow_none=True)

    packet = {
        "target_summary": target_summary,
        "issue_type": packet_issue_type,
        "current_auto_result": _packet_current_auto_result(current_assignment),
        "related_evidence": related_evidence[: max(1, min(len(related_evidence), 3))],
        "conflict_point": current_assignment.get("rationale") or "Taxonomy evidence requires human review.",
        "recommended_action": _recommended_action_for_issue(current_assignment, packet_issue_type),
        "upstream_downstream_links": upstream_downstream_links,
    }
    validate_instance(packet, schema_dir / "review_packet.schema.json")

    timestamp = created_at or utc_now_iso()
    issue_priority = priority_code or _default_priority_for_issue(packet_issue_type, current_assignment)
    _validate_priority(issue_priority, rules, allow_none=False)
    review_issue = {
        "review_issue_id": _stable_issue_id(packet_issue_type, current_assignment["target_type"], current_assignment["target_id"]),
        "issue_type": packet_issue_type,
        "target_type": current_assignment["target_type"],
        "target_id": current_assignment["target_id"],
        "priority_code": issue_priority,
        "status": "open",
        "assigned_to": None,
        "reviewer": None,
        "reviewed_at": None,
        "resolution_action": None,
        "approver": None,
        "approved_at": None,
        "maker_checker_required": _maker_checker_required(issue_priority, resolution_action=None),
        "payload_json": packet,
        "resolution_payload_json": None,
        "created_at": timestamp,
        "updated_at": timestamp,
        "resolved_at": None,
        "resolution_notes": None,
    }

    return {
        "review_packet": packet,
        "review_issue": review_issue,
        "review_queue_view": build_review_queue_entry(review_issue, config_dir=config_dir),
    }


def resolve_taxonomy_review_issue(
    review_issue: dict[str, Any],
    current_assignment: dict[str, Any],
    *,
    resolution_action: str,
    resolution_notes: str,
    reviewer: str,
    config_dir,
    reviewed_at: str | None = None,
    approver: str | None = None,
    approved_at: str | None = None,
    override_category_code: str | None = None,
    unresolved_mode: str | None = None,
) -> dict[str, Any]:
    rules = load_yaml(config_dir / "review_rules_v0.yaml")
    if review_issue.get("issue_type") not in TAXONOMY_REVIEW_ISSUE_TYPES:
        raise ContractValidationError("resolve_taxonomy_review_issue only supports taxonomy review issues")
    _validate_resolution_action(resolution_action, rules)
    normalized_unresolved_mode = _normalize_unresolved_mode(
        resolution_action,
        unresolved_mode=unresolved_mode,
        rules=rules,
    )

    review_timestamp = reviewed_at or utc_now_iso()
    updated_issue = dict(review_issue)
    updated_issue.update(
        {
            "reviewer": reviewer,
            "reviewed_at": review_timestamp,
            "resolution_action": resolution_action,
            "resolution_notes": resolution_notes,
            "status": "dismissed" if resolution_action == "reject_issue" else "resolved",
            "updated_at": review_timestamp,
            "resolved_at": review_timestamp,
        }
    )

    maker_checker_required = bool(updated_issue.get("maker_checker_required")) or _maker_checker_required(
        updated_issue["priority_code"],
        resolution_action=resolution_action,
    )
    updated_issue["maker_checker_required"] = maker_checker_required
    if maker_checker_required and resolution_action == "override_auto_result":
        if not approver or not approved_at:
            raise ContractValidationError("High-impact taxonomy overrides require approver and approved_at")
        updated_issue["approver"] = approver
        updated_issue["approved_at"] = approved_at
    else:
        updated_issue["approver"] = approver
        updated_issue["approved_at"] = approved_at

    resolution_payload = {
        "resolution_action": resolution_action,
        "resolution_notes": resolution_notes,
    }
    if override_category_code is not None:
        resolution_payload["override_category_code"] = override_category_code
    if normalized_unresolved_mode is not None:
        resolution_payload["unresolved_mode"] = normalized_unresolved_mode
    updated_issue["resolution_payload_json"] = resolution_payload

    writeback_assignment = None
    if resolution_action == "override_auto_result" or (
        resolution_action == "mark_unresolved" and normalized_unresolved_mode == "writeback_unresolved"
    ):
        writeback_assignment = _build_taxonomy_writeback_assignment(
            review_issue=updated_issue,
            current_assignment=current_assignment,
            resolution_notes=resolution_notes,
            reviewed_at=review_timestamp,
            override_category_code=override_category_code,
        )

    return {"review_issue": updated_issue, "taxonomy_assignment": writeback_assignment}


def apply_taxonomy_review_resolution(
    record: dict[str, Any],
    *,
    target_summary: str,
    upstream_downstream_links: list[dict[str, Any]],
    resolution_action: str,
    resolution_notes: str,
    reviewer: str,
    config_dir,
    schema_dir,
    issue_type: str | None = None,
    priority_code: str | None = None,
    created_at: str | None = None,
    reviewed_at: str | None = None,
    approver: str | None = None,
    approved_at: str | None = None,
    override_category_code: str | None = None,
    unresolved_mode: str | None = None,
    related_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    current_assignment = _require_current_primary_assignment(record)
    review_artifacts = build_taxonomy_review_issue(
        current_assignment,
        related_evidence or _related_evidence_for_record(record, current_assignment),
        target_summary=target_summary,
        upstream_downstream_links=upstream_downstream_links,
        config_dir=config_dir,
        schema_dir=schema_dir,
        issue_type=issue_type,
        priority_code=priority_code,
        created_at=created_at,
    )
    resolved = resolve_taxonomy_review_issue(
        review_artifacts["review_issue"],
        current_assignment,
        resolution_action=resolution_action,
        resolution_notes=resolution_notes,
        reviewer=reviewer,
        config_dir=config_dir,
        reviewed_at=reviewed_at,
        approver=approver,
        approved_at=approved_at,
        override_category_code=override_category_code,
        unresolved_mode=unresolved_mode,
    )

    updated_record = dict(record)
    updated_issue = resolved["review_issue"]
    updated_assignments = [dict(item) for item in record.get("taxonomy_assignments") or []]
    if resolved["taxonomy_assignment"] is not None:
        validate_instance(resolved["taxonomy_assignment"], schema_dir / "taxonomy_assignment.schema.json")
        updated_assignments.append(resolved["taxonomy_assignment"])
    updated_record["taxonomy_assignments"] = updated_assignments
    updated_record["review_issues"] = _upsert_review_issue(record.get("review_issues"), updated_issue)

    effective_taxonomy = select_effective_taxonomy_assignment(updated_assignments, label_role=current_assignment["label_role"])
    if effective_taxonomy is not None:
        updated_record["effective_taxonomy"] = dict(effective_taxonomy)

    unresolved_entry = build_unresolved_registry_entry(updated_record["review_issues"], effective_taxonomy)
    if unresolved_entry is None:
        updated_record.pop("unresolved_registry_entry", None)
    else:
        updated_record["unresolved_registry_entry"] = unresolved_entry

    updated_record["drill_down_refs"] = _merge_drill_down_refs(
        record.get("drill_down_refs"),
        updated_issue["review_issue_id"],
    )

    return {
        "review_packet": review_artifacts["review_packet"],
        "review_issue": updated_issue,
        "review_queue_view": build_review_queue_entry(updated_issue, config_dir=config_dir),
        "taxonomy_assignment": resolved["taxonomy_assignment"],
        "record": updated_record,
    }


def build_review_queue_entry(review_issue: dict[str, Any], *, config_dir) -> dict[str, Any]:
    rules = load_yaml(config_dir / "review_rules_v0.yaml")
    queue_bucket = "default"
    for bucket_rule in rules["queue_buckets"]:
        if _matches_queue_bucket(review_issue, bucket_rule["when"]):
            queue_bucket = bucket_rule["queue_bucket"]
            break
    return {
        "review_issue_id": review_issue["review_issue_id"],
        "priority_code": review_issue["priority_code"],
        "status": review_issue["status"],
        "assigned_to": review_issue.get("assigned_to"),
        "created_at": review_issue["created_at"],
        "queue_bucket": queue_bucket,
    }


def select_effective_taxonomy_assignment(assignments: list[dict[str, Any]], *, label_role: str = "primary") -> dict[str, Any] | None:
    eligible = [
        assignment
        for assignment in assignments
        if assignment.get("label_role") == label_role and assignment.get("result_status") == "active"
    ]
    if not eligible:
        return None
    return sorted(
        eligible,
        key=lambda assignment: (
            1 if assignment.get("is_override") else 0,
            assignment.get("effective_from") or "",
            assignment.get("assigned_at") or "",
        ),
    )[-1]


def build_unresolved_registry_entry(
    review_issues: list[dict[str, Any]],
    effective_assignment: dict[str, Any] | None,
) -> dict[str, Any] | None:
    taxonomy_issues = [issue for issue in review_issues if issue.get("issue_type") in TAXONOMY_REVIEW_ISSUE_TYPES]
    if not taxonomy_issues:
        return None

    selected_issue = sorted(
        taxonomy_issues,
        key=lambda issue: issue.get("reviewed_at") or issue.get("updated_at") or issue.get("created_at") or "",
    )[-1]
    effective_unresolved = bool(
        effective_assignment
        and effective_assignment.get("label_role") == "primary"
        and effective_assignment.get("category_code") == "unresolved"
    )
    return {
        "target_id": selected_issue["target_id"],
        "issue_type": selected_issue["issue_type"],
        "priority_code": selected_issue["priority_code"],
        "resolution_action": selected_issue.get("resolution_action"),
        "review_issue_id": selected_issue["review_issue_id"],
        "resolution_notes": selected_issue.get("resolution_notes"),
        "reviewed_at": selected_issue.get("reviewed_at"),
        "is_stale": _is_stale(selected_issue),
        "is_effective_unresolved": effective_unresolved and selected_issue.get("resolution_action") == "mark_unresolved",
    }


def _build_taxonomy_writeback_assignment(
    *,
    review_issue: dict[str, Any],
    current_assignment: dict[str, Any],
    resolution_notes: str,
    reviewed_at: str,
    override_category_code: str | None,
) -> dict[str, Any]:
    category_code = "unresolved" if review_issue["resolution_action"] == "mark_unresolved" else override_category_code
    if not category_code:
        raise ContractValidationError("override_auto_result requires override_category_code")

    evidence_refs = current_assignment.get("evidence_refs_json") or _evidence_refs_from_review_issue(review_issue)
    if not evidence_refs:
        raise ContractValidationError("Taxonomy writeback requires at least one evidence ref")

    prior_assignment_id = current_assignment.get("assignment_id") or _stable_assignment_id(current_assignment)
    return {
        "target_type": current_assignment["target_type"],
        "target_id": current_assignment["target_id"],
        "taxonomy_version": current_assignment["taxonomy_version"],
        "label_level": current_assignment["label_level"],
        "label_role": current_assignment["label_role"],
        "category_code": category_code,
        "confidence": None,
        "rationale": resolution_notes,
        "assigned_by": MODULE_NAME,
        "model_or_rule_version": TRIGGER_VERSION,
        "assigned_at": reviewed_at,
        "is_override": True,
        "override_review_issue_id": review_issue["review_issue_id"],
        "result_status": "active",
        "effective_from": reviewed_at,
        "supersedes_assignment_id": prior_assignment_id,
        "evidence_refs_json": evidence_refs,
    }


def _evidence_refs_from_review_issue(review_issue: dict[str, Any]) -> list[dict[str, Any]]:
    packet = review_issue.get("payload_json") or {}
    related = packet.get("related_evidence") or []
    refs = []
    for item in related:
        if isinstance(item, dict):
            ref = {key: item[key] for key in ("source_item_id", "evidence_type", "source_url") if key in item}
            if ref:
                refs.append(ref)
    return refs


def _packet_current_auto_result(current_assignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_type": current_assignment["target_type"],
        "target_id": current_assignment["target_id"],
        "taxonomy_version": current_assignment["taxonomy_version"],
        "label_role": current_assignment["label_role"],
        "category_code": current_assignment["category_code"],
        "confidence": current_assignment.get("confidence"),
        "result_status": current_assignment.get("result_status"),
    }


def _infer_taxonomy_issue_type(current_assignment: dict[str, Any], related_evidence: list[dict[str, Any]]) -> str:
    if current_assignment.get("category_code") == "unresolved":
        return "taxonomy_conflict"
    if any(item.get("evidence_type") == "unclear_description_signal" for item in related_evidence):
        return "taxonomy_low_confidence"
    confidence = current_assignment.get("confidence")
    if confidence is None or confidence < 0.75:
        return "taxonomy_low_confidence"
    return "taxonomy_conflict"


def _recommended_action_for_issue(current_assignment: dict[str, Any], issue_type: str) -> str:
    if current_assignment.get("category_code") == "unresolved":
        return "mark_unresolved"
    if issue_type == "taxonomy_low_confidence":
        return "needs_more_evidence"
    return "override_auto_result"


def _default_priority_for_issue(issue_type: str, current_assignment: dict[str, Any]) -> str:
    if issue_type == "taxonomy_conflict":
        return "P1"
    if current_assignment.get("category_code") == "unresolved":
        return "P1"
    return "P2"


def _maker_checker_required(priority_code: str, *, resolution_action: str | None) -> bool:
    return priority_code == "P0" and resolution_action == "override_auto_result"


def _matches_queue_bucket(review_issue: dict[str, Any], when: dict[str, Any]) -> bool:
    for key, expected in when.items():
        if key == "stale":
            if bool(expected) != _is_stale(review_issue):
                return False
            continue
        value = review_issue.get(key)
        if isinstance(expected, list):
            if value not in expected:
                return False
        elif value != expected:
            return False
    return True


def _is_stale(review_issue: dict[str, Any]) -> bool:
    if review_issue.get("status") not in OPEN_REVIEW_STATUSES:
        return False
    payload = review_issue.get("payload_json") or {}
    return bool(payload.get("is_stale"))


def _validate_issue_type(issue_type: str, rules: dict[str, Any]) -> None:
    if issue_type not in rules["issue_types"]:
        raise ContractValidationError(f"Unsupported review issue_type: {issue_type}")


def _validate_priority(priority_code: str | None, rules: dict[str, Any], *, allow_none: bool) -> None:
    if priority_code is None and allow_none:
        return
    if priority_code not in rules["priority_system"]:
        raise ContractValidationError(f"Unsupported priority_code: {priority_code}")


def _validate_resolution_action(resolution_action: str, rules: dict[str, Any]) -> None:
    if resolution_action not in rules["resolution_actions"]:
        raise ContractValidationError(f"Unsupported resolution_action: {resolution_action}")


def _normalize_unresolved_mode(
    resolution_action: str,
    *,
    unresolved_mode: str | None,
    rules: dict[str, Any],
) -> str | None:
    if resolution_action != "mark_unresolved":
        if unresolved_mode is not None:
            raise ContractValidationError("unresolved_mode is only valid when resolution_action = mark_unresolved")
        return None

    modes = rules.get("unresolved_handling", {}).get("unresolved_modes") or []
    mode = unresolved_mode or "writeback_unresolved"
    if mode not in modes:
        raise ContractValidationError(f"Unsupported unresolved_mode: {mode}")
    return mode


def _require_current_primary_assignment(record: dict[str, Any]) -> dict[str, Any]:
    assignments = record.get("taxonomy_assignments")
    if not isinstance(assignments, list) or not assignments:
        raise ContractValidationError("Taxonomy review resolution requires canonical taxonomy_assignments on the record")
    current_assignment = select_effective_taxonomy_assignment(assignments, label_role="primary")
    if current_assignment is None:
        raise ContractValidationError("Taxonomy review resolution requires an active primary taxonomy assignment")
    return current_assignment


def _related_evidence_for_record(record: dict[str, Any], current_assignment: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = current_assignment.get("evidence_refs_json")
    if isinstance(evidence, list) and evidence:
        return evidence

    drill_down_refs = record.get("drill_down_refs") or {}
    source_item_id = drill_down_refs.get("source_item_id") or record.get("source_item_id")
    source_url = record.get("source_url")
    if source_item_id and source_url:
        return [{"source_item_id": source_item_id, "evidence_type": "job_statement", "source_url": source_url}]
    raise ContractValidationError("Taxonomy review resolution requires at least one traceable evidence ref")


def _upsert_review_issue(review_issues: object, updated_issue: dict[str, Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    if isinstance(review_issues, list):
        for issue in review_issues:
            if isinstance(issue, dict) and issue.get("review_issue_id") != updated_issue["review_issue_id"]:
                merged.append(dict(issue))
    merged.append(updated_issue)
    return merged


def _merge_drill_down_refs(drill_down_refs: object, review_issue_id: str) -> dict[str, Any]:
    refs = dict(drill_down_refs) if isinstance(drill_down_refs, dict) else {}
    review_issue_ids = list(refs.get("review_issue_ids") or [])
    if review_issue_id not in review_issue_ids:
        review_issue_ids.append(review_issue_id)
    refs["review_issue_ids"] = review_issue_ids
    return refs


def _stable_issue_id(issue_type: str, target_type: str, target_id: str) -> str:
    seed = f"{issue_type}|{target_type}|{target_id}|{TRIGGER_VERSION}"
    return f"rev_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _stable_assignment_id(assignment: dict[str, Any]) -> str:
    seed = "|".join(
        [
            assignment["target_type"],
            assignment["target_id"],
            assignment["taxonomy_version"],
            assignment["label_role"],
            assignment.get("category_code") or "",
            assignment.get("assigned_at") or "",
        ]
    )
    return f"tax_{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"
