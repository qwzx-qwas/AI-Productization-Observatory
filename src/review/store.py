"""File-backed review_issue registry and taxonomy review writeback helpers."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.common.errors import ContractValidationError
from src.common.files import dump_json, ensure_parent, load_json
from src.review.review_packet_builder import (
    OPEN_REVIEW_STATUSES,
    apply_taxonomy_review_resolution,
    build_review_queue_entry,
    build_taxonomy_review_issue,
    build_unresolved_registry_entry,
    select_effective_taxonomy_assignment,
)

if os.name == "nt":
    import msvcrt
else:
    import fcntl


def default_review_issue_store_path(task_store_path: Path) -> Path:
    return task_store_path.with_name("review_issues.json")


class FileReviewIssueStore:
    """Persists review issues while keeping derived queue views reproducible."""

    def __init__(self, store_path: Path) -> None:
        self.store_path = Path(store_path)

    @property
    def lock_path(self) -> Path:
        return self.store_path.with_name(f"{self.store_path.name}.lock")

    @contextmanager
    def _exclusive_lock(self):
        ensure_parent(self.lock_path)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _load_issues_unlocked(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        try:
            payload = load_json(self.store_path)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"review_issue store is not valid JSON: {self.store_path}") from exc
        if not isinstance(payload, list):
            raise ContractValidationError(f"review_issue store must contain a JSON list: {self.store_path}")
        return payload

    def _write_issues_unlocked(self, issues: list[dict[str, Any]]) -> None:
        dump_json(self.store_path, issues)

    def all_issues(self) -> list[dict[str, Any]]:
        with self._exclusive_lock():
            return self._load_issues_unlocked()

    def get(self, review_issue_id: str) -> dict[str, Any]:
        with self._exclusive_lock():
            issues = self._load_issues_unlocked()
            for issue in issues:
                if issue.get("review_issue_id") == review_issue_id:
                    return dict(issue)
        raise ContractValidationError(f"Unknown review_issue_id: {review_issue_id}")

    def upsert(self, review_issue: dict[str, Any]) -> dict[str, Any]:
        with self._exclusive_lock():
            issues = self._load_issues_unlocked()
            merged = _upsert_review_issue_list(issues, review_issue)
            issues[:] = merged
            self._write_issues_unlocked(issues)
            return dict(review_issue)

    def queue_entries(self, *, config_dir: Path, open_only: bool = False) -> list[dict[str, Any]]:
        issues = self.all_issues()
        filtered = issues if not open_only else [issue for issue in issues if issue.get("status") in OPEN_REVIEW_STATUSES]
        return [build_review_queue_entry(issue, config_dir=config_dir) for issue in filtered]


def open_taxonomy_review_record(
    record: dict[str, Any],
    *,
    store: FileReviewIssueStore,
    target_summary: str,
    upstream_downstream_links: list[dict[str, Any]],
    config_dir: Path,
    schema_dir: Path,
    issue_type: str | None = None,
    priority_code: str | None = None,
    created_at: str | None = None,
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
    stored_issue = store.upsert(review_artifacts["review_issue"])
    updated_record = _record_with_review_issue(record, stored_issue)
    return {
        "review_packet": review_artifacts["review_packet"],
        "review_issue": stored_issue,
        "review_queue_view": build_review_queue_entry(stored_issue, config_dir=config_dir),
        "record": updated_record,
    }


def resolve_taxonomy_review_record(
    record: dict[str, Any],
    *,
    store: FileReviewIssueStore,
    review_issue_id: str,
    target_summary: str,
    upstream_downstream_links: list[dict[str, Any]],
    resolution_action: str,
    resolution_notes: str,
    reviewer: str,
    config_dir: Path,
    schema_dir: Path,
    reviewed_at: str | None = None,
    approver: str | None = None,
    approved_at: str | None = None,
    override_category_code: str | None = None,
    unresolved_mode: str | None = None,
) -> dict[str, Any]:
    existing_issue = store.get(review_issue_id)
    applied = apply_taxonomy_review_resolution(
        record,
        target_summary=target_summary,
        upstream_downstream_links=upstream_downstream_links,
        resolution_action=resolution_action,
        resolution_notes=resolution_notes,
        reviewer=reviewer,
        config_dir=config_dir,
        schema_dir=schema_dir,
        issue_type=existing_issue["issue_type"],
        priority_code=existing_issue["priority_code"],
        created_at=existing_issue["created_at"],
        reviewed_at=reviewed_at,
        approver=approver,
        approved_at=approved_at,
        override_category_code=override_category_code,
        unresolved_mode=unresolved_mode,
        related_evidence=(existing_issue.get("payload_json") or {}).get("related_evidence"),
    )
    updated_issue = dict(applied["review_issue"])
    updated_issue["assigned_to"] = existing_issue.get("assigned_to")
    stored_issue = store.upsert(updated_issue)
    applied["review_issue"] = stored_issue
    applied["review_queue_view"] = build_review_queue_entry(stored_issue, config_dir=config_dir)
    applied["record"] = _record_with_review_issue(applied["record"], stored_issue)
    return applied


def _require_current_primary_assignment(record: dict[str, Any]) -> dict[str, Any]:
    assignments = record.get("taxonomy_assignments")
    if not isinstance(assignments, list) or not assignments:
        raise ContractValidationError("Review control plane requires taxonomy_assignments on the canonical record")
    current_assignment = select_effective_taxonomy_assignment(assignments, label_role="primary")
    if current_assignment is None:
        raise ContractValidationError("Review control plane requires an active primary taxonomy assignment")
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
    raise ContractValidationError("Review control plane requires at least one traceable evidence ref")


def _record_with_review_issue(record: dict[str, Any], review_issue: dict[str, Any]) -> dict[str, Any]:
    updated = dict(record)
    updated["review_issues"] = _upsert_review_issue_list(updated.get("review_issues"), review_issue)
    updated["drill_down_refs"] = _merge_drill_down_refs(updated.get("drill_down_refs"), review_issue["review_issue_id"])

    effective_taxonomy = None
    assignments = updated.get("taxonomy_assignments")
    if isinstance(assignments, list):
        effective_taxonomy = select_effective_taxonomy_assignment(assignments, label_role="primary")
        if effective_taxonomy is not None:
            updated["effective_taxonomy"] = dict(effective_taxonomy)

    unresolved_entry = build_unresolved_registry_entry(updated["review_issues"], effective_taxonomy)
    if unresolved_entry is None:
        updated.pop("unresolved_registry_entry", None)
    else:
        updated["unresolved_registry_entry"] = unresolved_entry
    return updated


def _merge_drill_down_refs(drill_down_refs: object, review_issue_id: str) -> dict[str, Any]:
    refs = dict(drill_down_refs) if isinstance(drill_down_refs, dict) else {}
    review_issue_ids = list(refs.get("review_issue_ids") or [])
    if review_issue_id not in review_issue_ids:
        review_issue_ids.append(review_issue_id)
    refs["review_issue_ids"] = review_issue_ids
    return refs


def _upsert_review_issue_list(review_issues: object, updated_issue: dict[str, Any]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    if isinstance(review_issues, list):
        for issue in review_issues:
            if isinstance(issue, dict) and issue.get("review_issue_id") != updated_issue["review_issue_id"]:
                merged.append(dict(issue))
    merged.append(dict(updated_issue))
    return merged
