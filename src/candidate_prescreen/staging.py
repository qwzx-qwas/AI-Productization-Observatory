"""Write approved candidate prescreen records into the external staging carrier."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.common.errors import ContractValidationError
from src.common.files import dump_yaml, load_yaml, utc_now_iso


def _staging_files(staging_dir: Path) -> list[Path]:
    return sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml"))


def _candidate_ref(candidate_record: dict[str, Any], candidate_path: Path) -> dict[str, Any]:
    llm_prescreen = candidate_record["llm_prescreen"]
    return {
        "candidate_id": candidate_record["candidate_id"],
        "candidate_document_path": str(candidate_path),
        "query_family": candidate_record["query_family"],
        "query_slice_id": candidate_record["query_slice_id"],
        "selection_rule_version": candidate_record["selection_rule_version"],
        "recommended_action": llm_prescreen.get("recommended_action"),
        "human_review_status": candidate_record["human_review_status"],
        "human_review_notes": candidate_record.get("human_review_notes"),
        "human_reviewed_at": candidate_record.get("human_reviewed_at"),
    }


def _source_record_refs(candidate_record: dict[str, Any], candidate_path: Path) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": candidate_record["candidate_id"],
            "candidate_document_path": str(candidate_path),
            "source": candidate_record["source"],
            "source_id": candidate_record["source_id"],
            "source_window": candidate_record["source_window"],
            "external_id": candidate_record["external_id"],
            "canonical_url": candidate_record["canonical_url"],
        }
    ]


def _blocking_items(candidate_record: dict[str, Any]) -> list[str]:
    base = [
        "formal review_refs not yet provided",
        "formal evidence_refs not yet provided",
        "local_project_user raw annotation not yet provided",
        "llm raw annotation not yet provided",
        "adjudicated final decision fields not yet provided",
        "adjudication basis not yet provided",
    ]
    if candidate_record.get("human_review_status") != "approved_for_staging":
        base.append("candidate did not pass the first human review gate")
    return base


def handoff_candidate_to_staging(
    candidate_record: dict[str, Any],
    *,
    candidate_path: Path,
    staging_dir: Path,
) -> tuple[str, str]:
    if candidate_record.get("human_review_status") != "approved_for_staging":
        raise ContractValidationError("Only human_review_status = approved_for_staging may be written into staging")
    sample_id = str(candidate_record["candidate_id"])
    candidate_batch_id = str(candidate_record["candidate_batch_id"])
    source_record_refs = _source_record_refs(candidate_record, candidate_path)
    candidate_ref = _candidate_ref(candidate_record, candidate_path)
    for staging_path in _staging_files(staging_dir):
        payload = load_yaml(staging_path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Staging document must be a mapping: {staging_path}")
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ContractValidationError(f"Staging document must contain samples[]: {staging_path}")
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if sample.get("sample_id") == sample_id:
                slot_id = str(sample.get("sample_slot_id"))
                _apply_candidate_to_slot(sample, candidate_record, candidate_path, source_record_refs, candidate_ref, candidate_batch_id)
                dump_yaml(staging_path, payload)
                return str(staging_path), slot_id
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if sample.get("sample_id") is None and sample.get("current_state") == "awaiting_real_input":
                slot_id = str(sample.get("sample_slot_id"))
                _apply_candidate_to_slot(sample, candidate_record, candidate_path, source_record_refs, candidate_ref, candidate_batch_id)
                dump_yaml(staging_path, payload)
                return str(staging_path), slot_id
    raise ContractValidationError("No available staging slot remains for candidate handoff")


def _apply_candidate_to_slot(
    sample: dict[str, Any],
    candidate_record: dict[str, Any],
    candidate_path: Path,
    source_record_refs: list[dict[str, Any]],
    candidate_ref: dict[str, Any],
    candidate_batch_id: str,
) -> None:
    now_iso = utc_now_iso()
    sample["current_state"] = "candidate_approved_for_annotation"
    sample["ready_for_formal_writeflow"] = False
    sample["sample_id"] = candidate_record["candidate_id"]
    sample["target_type"] = "product"
    sample["source_record_refs"] = source_record_refs
    sample["training_pool_source"] = "candidate_pool"
    sample["whitelist_reason"] = candidate_record.get("whitelist_reason")
    sample["candidate_prescreen_ref"] = candidate_ref
    sample["review_refs"] = []
    sample["evidence_refs"] = []
    sample["blocking_items"] = _blocking_items(candidate_record)

    sample_metadata = sample.get("sample_metadata")
    if not isinstance(sample_metadata, dict):
        raise ContractValidationError("staging sample_metadata must be a mapping")
    sample_metadata["provided"] = False
    sample_metadata["sample_id"] = candidate_record["candidate_id"]
    sample_metadata["target_id"] = None
    sample_metadata["source_id"] = candidate_record["source_id"]
    sample_metadata["target_type"] = "product"
    sample_metadata["source_record_refs"] = source_record_refs
    sample_metadata["review_refs"] = []
    sample_metadata["evidence_refs"] = []
    pool_trace = sample_metadata.get("pool_trace")
    if not isinstance(pool_trace, dict):
        raise ContractValidationError("staging sample_metadata.pool_trace must be a mapping")
    pool_trace["candidate_pool_batch_id"] = candidate_batch_id
    pool_trace["training_pool_source"] = "candidate_pool"
    pool_trace["whitelist_reason"] = candidate_record.get("whitelist_reason")
    sample["staged_from_candidate_prescreen_at"] = now_iso
    sample["staged_from_candidate_prescreen_path"] = str(candidate_path)
