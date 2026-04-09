"""Write approved candidate prescreen records into the external staging carrier."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.candidate_prescreen.url_utils import candidate_url_dedupe_key, normalize_candidate_url
from src.common.errors import ContractValidationError
from src.common.files import dump_yaml, load_yaml, utc_now_iso

EXPECTED_STAGING_DOCUMENT_COUNT = 20
EXPECTED_SAMPLES_PER_DOCUMENT = 15
EXPECTED_TOTAL_SLOTS = EXPECTED_STAGING_DOCUMENT_COUNT * EXPECTED_SAMPLES_PER_DOCUMENT


def _staging_files(staging_dir: Path) -> list[Path]:
    return sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml"))


def _sample_is_filled(sample: dict[str, Any]) -> bool:
    sample_id = sample.get("sample_id")
    return isinstance(sample_id, str) and bool(sample_id.strip())


def _require_mapping(value: Any, description: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{description} must be a mapping")
    return value


def _require_non_empty_string(value: Any, description: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractValidationError(f"{description} must be a non-empty string")
    return value


def _parse_iso_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _sample_source_url_key(sample: dict[str, Any]) -> tuple[str, str] | None:
    if not _sample_is_filled(sample):
        return None
    source_record_refs = sample.get("source_record_refs")
    if not isinstance(source_record_refs, list) or not source_record_refs:
        return None
    ref = source_record_refs[0]
    if not isinstance(ref, dict):
        return None
    return candidate_url_dedupe_key(
        ref.get("source_id"),
        ref.get("canonical_url"),
        source_field_name="staging source_record_refs[0].source_id",
        url_field_name="staging source_record_refs[0].canonical_url",
    )


def _sample_key(sample: dict[str, Any]) -> str | None:
    sample_metadata = sample.get("sample_metadata")
    if isinstance(sample_metadata, dict):
        sample_key = sample_metadata.get("sample_key")
        if isinstance(sample_key, str) and sample_key.strip():
            return sample_key.strip()
    source_record_refs = sample.get("source_record_refs")
    if not isinstance(source_record_refs, list) or not source_record_refs:
        return None
    ref = source_record_refs[0]
    if not isinstance(ref, dict):
        return None
    sample_key = ref.get("sample_key")
    if isinstance(sample_key, str) and sample_key.strip():
        return sample_key.strip()
    return None


def _sample_identity_key(sample: dict[str, Any]) -> tuple[str, str] | None:
    sample_key = _sample_key(sample)
    if sample_key is not None:
        return ("sample_key", sample_key)
    url_key = _sample_source_url_key(sample)
    if url_key is None:
        return None
    return ("source_url", f"{url_key[0]}::{url_key[1]}")


def _sample_candidate_document_path(sample: dict[str, Any]) -> Path | None:
    source_record_refs = sample.get("source_record_refs")
    if isinstance(source_record_refs, list) and source_record_refs:
        ref = source_record_refs[0]
        if isinstance(ref, dict) and isinstance(ref.get("candidate_document_path"), str) and ref.get("candidate_document_path"):
            return Path(str(ref["candidate_document_path"]))
    candidate_ref = sample.get("candidate_prescreen_ref")
    if isinstance(candidate_ref, dict) and isinstance(candidate_ref.get("candidate_document_path"), str) and candidate_ref.get("candidate_document_path"):
        return Path(str(candidate_ref["candidate_document_path"]))
    return None


def _sample_preference_key(sample: dict[str, Any]) -> tuple[int, datetime, str]:
    candidate_path = _sample_candidate_document_path(sample)
    candidate_path_exists = 1 if candidate_path is not None and candidate_path.exists() else 0
    staged_at = _parse_iso_timestamp(sample.get("staged_from_candidate_prescreen_at"))
    slot_id = str(sample.get("sample_slot_id") or "")
    return (candidate_path_exists, staged_at, slot_id)


def _reset_sample_to_empty(sample: dict[str, Any]) -> None:
    sample["current_state"] = "awaiting_real_input"
    sample["ready_for_formal_writeflow"] = False
    sample["sample_id"] = None
    sample["target_type"] = "product"
    sample["review_closed"] = None
    sample["clear_adjudication"] = None
    sample["primary_category_code"] = None
    sample["review_refs"] = []
    sample["evidence_refs"] = []
    sample["source_record_refs"] = []
    sample["training_pool_source"] = "candidate_pool"
    sample["whitelist_reason"] = None
    local_annotation = _require_mapping(sample.get("local_project_user_annotation"), "staging local_project_user_annotation")
    local_annotation["provided"] = False
    local_annotation["primary_category_code"] = None
    local_annotation["secondary_category_code"] = None
    local_annotation["primary_persona_code"] = None
    local_annotation["delivery_form_code"] = None
    local_annotation["build_evidence_band"] = None
    local_annotation["need_clarity_band"] = None
    local_annotation["rationale"] = None
    local_annotation["evidence_refs"] = []
    local_annotation["review_recommended"] = None
    local_annotation["review_reason"] = None
    local_annotation["taxonomy_change_suggestion"] = None
    local_annotation["channel_metadata"] = {}
    llm_annotation = _require_mapping(sample.get("llm_annotation"), "staging llm_annotation")
    llm_annotation["provided"] = False
    llm_annotation["primary_category_code"] = None
    llm_annotation["secondary_category_code"] = None
    llm_annotation["primary_persona_code"] = None
    llm_annotation["delivery_form_code"] = None
    llm_annotation["build_evidence_band"] = None
    llm_annotation["need_clarity_band"] = None
    llm_annotation["rationale"] = None
    llm_annotation["evidence_refs"] = []
    llm_annotation["review_recommended"] = None
    llm_annotation["review_reason"] = None
    llm_annotation["taxonomy_change_suggestion"] = None
    llm_channel_metadata = _require_mapping(llm_annotation.get("channel_metadata"), "staging llm_annotation.channel_metadata")
    llm_channel_metadata["prompt_version"] = None
    llm_channel_metadata["routing_version"] = None
    adjudicated_output = _require_mapping(sample.get("adjudicated_output"), "staging adjudicated_output")
    adjudicated_output["provided"] = False
    adjudicated_output["sample_id"] = None
    adjudicated_output["target_type"] = "product"
    adjudicated_output["target_id"] = None
    adjudicated_output["primary_category_code"] = None
    adjudicated_output["secondary_category_code"] = None
    adjudicated_output["primary_persona_code"] = None
    adjudicated_output["delivery_form_code"] = None
    adjudicated_output["build_evidence_band"] = None
    adjudicated_output["need_clarity_band"] = None
    adjudicated_output["rationale"] = None
    adjudicated_output["evidence_refs"] = []
    adjudicated_output["review_recommended"] = None
    adjudicated_output["review_reason"] = None
    adjudicated_output["taxonomy_change_suggestion"] = None
    adjudication_basis = _require_mapping(sample.get("adjudication_basis"), "staging adjudication_basis")
    adjudication_basis["provided"] = False
    adjudication_basis["adjudicated_at"] = None
    adjudication_basis["adjudication_rationale"] = None
    adjudication_basis["decision_basis_refs"] = []
    adjudication_basis["notes"] = None
    sample_metadata = _require_mapping(sample.get("sample_metadata"), "staging sample_metadata")
    sample_metadata["provided"] = False
    sample_metadata["sample_id"] = None
    sample_metadata["target_id"] = None
    sample_metadata["source_id"] = None
    sample_metadata["target_type"] = "product"
    sample_metadata["sample_key"] = None
    sample_metadata["source_record_refs"] = []
    sample_metadata["review_refs"] = []
    sample_metadata["evidence_refs"] = []
    eligibility_snapshot = _require_mapping(sample_metadata.get("eligibility_snapshot"), "staging sample_metadata.eligibility_snapshot")
    eligibility_snapshot["review_closed"] = None
    eligibility_snapshot["sufficient_evidence"] = None
    eligibility_snapshot["clear_adjudication"] = None
    eligibility_snapshot["is_unresolved"] = None
    pool_trace = _require_mapping(sample_metadata.get("pool_trace"), "staging sample_metadata.pool_trace")
    pool_trace["candidate_pool_batch_id"] = None
    pool_trace["training_pool_source"] = "candidate_pool"
    pool_trace["whitelist_reason"] = None
    sample["blocking_items"] = [
        "real sample_id not yet provided",
        "local_project_user raw annotation not yet provided",
        "llm raw annotation not yet provided",
        "adjudicated final decision fields not yet provided",
        "adjudication basis not yet provided",
        "review_refs/evidence_refs/source_record_refs not yet provided",
    ]
    sample.pop("candidate_prescreen_ref", None)
    sample.pop("staged_from_candidate_prescreen_at", None)
    sample.pop("staged_from_candidate_prescreen_path", None)


def dedupe_staging_semantic_duplicates(staging_dir: Path) -> dict[str, Any]:
    loaded_documents: dict[Path, dict[str, Any]] = {}
    samples_by_key: dict[tuple[str, str], list[tuple[Path, dict[str, Any]]]] = {}
    for staging_path in _staging_files(staging_dir):
        payload = _require_mapping(load_yaml(staging_path), f"staging document {staging_path}")
        loaded_documents[staging_path] = payload
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ContractValidationError(f"Staging document must contain samples[]: {staging_path}")
        for sample in samples:
            sample_mapping = _require_mapping(sample, f"{staging_path}:samples[]")
            semantic_key = _sample_identity_key(sample_mapping)
            if semantic_key is None:
                continue
            samples_by_key.setdefault(semantic_key, []).append((staging_path, sample_mapping))

    cleared_slots: list[dict[str, Any]] = []
    touched_paths: set[Path] = set()
    duplicate_group_count = 0
    for semantic_key, entries in sorted(samples_by_key.items(), key=lambda item: item[0]):
        if len(entries) <= 1:
            continue
        duplicate_group_count += 1
        kept_path, kept_sample = max(entries, key=lambda item: _sample_preference_key(item[1]))
        kept_slot_id = str(kept_sample.get("sample_slot_id"))
        kept_sample_id = str(kept_sample.get("sample_id"))
        for staging_path, sample in entries:
            if staging_path == kept_path and sample is kept_sample:
                continue
            source_ref = _require_mapping(sample.get("source_record_refs")[0], "staging source_record_refs[0]")
            kept_source_ref = _require_mapping(kept_sample.get("source_record_refs")[0], "staging source_record_refs[0]")
            cleared_slots.append(
                {
                    "dedupe_key_type": semantic_key[0],
                    "dedupe_key_value": semantic_key[1],
                    "dedupe_basis": "sample_key" if semantic_key[0] == "sample_key" else "source_id + normalized canonical_url",
                    "cleared_external_id": source_ref.get("external_id"),
                    "cleared_canonical_url": source_ref.get("canonical_url"),
                    "cleared_staging_document_path": str(staging_path),
                    "cleared_sample_slot_id": str(sample.get("sample_slot_id")),
                    "cleared_sample_id": str(sample.get("sample_id")),
                    "kept_external_id": kept_source_ref.get("external_id"),
                    "kept_canonical_url": kept_source_ref.get("canonical_url"),
                    "kept_staging_document_path": str(kept_path),
                    "kept_sample_slot_id": kept_slot_id,
                    "kept_sample_id": kept_sample_id,
                }
            )
            _reset_sample_to_empty(sample)
            touched_paths.add(staging_path)
    for staging_path in sorted(touched_paths):
        dump_yaml(staging_path, loaded_documents[staging_path])
    progress = validate_staging_workspace(staging_dir)
    return {
        "duplicate_group_count": duplicate_group_count,
        "cleared_slot_count": len(cleared_slots),
        "cleared_slots": cleared_slots,
        "staging_total_filled": progress["total_filled"],
        "staging_total_empty": progress["total_empty"],
    }


def staging_progress(staging_dir: Path) -> dict[str, Any]:
    staging_paths = _staging_files(staging_dir)
    if len(staging_paths) != EXPECTED_STAGING_DOCUMENT_COUNT:
        raise ContractValidationError(
            f"Staging carrier must retain {EXPECTED_STAGING_DOCUMENT_COUNT} YAML files, found {len(staging_paths)}"
        )

    documents: list[dict[str, Any]] = []
    total_filled = 0
    total_slots = 0
    next_open_slot: dict[str, Any] | None = None
    for staging_path in staging_paths:
        payload = _require_mapping(load_yaml(staging_path), f"staging document {staging_path}")
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ContractValidationError(f"Staging document must contain samples[]: {staging_path}")
        if len(samples) != EXPECTED_SAMPLES_PER_DOCUMENT:
            raise ContractValidationError(
                f"Staging document must retain {EXPECTED_SAMPLES_PER_DOCUMENT} sample slots: {staging_path}"
            )

        filled_samples: list[dict[str, str]] = []
        empty_slot_ids: list[str] = []
        seen_slot_ids: set[str] = set()
        for sample in samples:
            sample_mapping = _require_mapping(sample, f"{staging_path}:samples[]")
            sample_slot_id = _require_non_empty_string(sample_mapping.get("sample_slot_id"), f"{staging_path}:sample_slot_id")
            if sample_slot_id in seen_slot_ids:
                raise ContractValidationError(f"Duplicate sample_slot_id in staging document {staging_path}: {sample_slot_id}")
            seen_slot_ids.add(sample_slot_id)
            if _sample_is_filled(sample_mapping):
                filled_samples.append(
                    {
                        "sample_slot_id": sample_slot_id,
                        "sample_id": str(sample_mapping["sample_id"]),
                    }
                )
            else:
                empty_slot_ids.append(sample_slot_id)
                if next_open_slot is None:
                    next_open_slot = {
                        "staging_document_path": str(staging_path),
                        "sample_slot_id": sample_slot_id,
                    }

        filled_count = len(filled_samples)
        total_filled += filled_count
        total_slots += len(samples)
        documents.append(
            {
                "staging_document_path": str(staging_path),
                "filled_slots": filled_count,
                "empty_slots": len(empty_slot_ids),
                "empty_slot_ids": empty_slot_ids,
                "filled_sample_refs": filled_samples,
            }
        )

    if total_slots != EXPECTED_TOTAL_SLOTS:
        raise ContractValidationError(f"Staging carrier must retain exactly {EXPECTED_TOTAL_SLOTS} slots, found {total_slots}")

    return {
        "total_filled": total_filled,
        "total_slots": total_slots,
        "total_empty": total_slots - total_filled,
        "documents": documents,
        "next_open_slot": next_open_slot,
        "is_complete": total_filled == EXPECTED_TOTAL_SLOTS and all(document["filled_slots"] == EXPECTED_SAMPLES_PER_DOCUMENT for document in documents),
    }


def validate_staging_workspace(staging_dir: Path) -> dict[str, Any]:
    progress = staging_progress(staging_dir)
    seen_source_semantics: dict[tuple[str, str], tuple[Path, str, str]] = {}
    for document in progress["documents"]:
        staging_path = Path(document["staging_document_path"])
        payload = _require_mapping(load_yaml(staging_path), f"staging document {staging_path}")
        samples = payload.get("samples")
        if not isinstance(samples, list):
            raise ContractValidationError(f"Staging document must contain samples[]: {staging_path}")
        for sample in samples:
            sample_mapping = _require_mapping(sample, f"{staging_path}:samples[]")
            if not _sample_is_filled(sample_mapping):
                if sample_mapping.get("current_state") != "awaiting_real_input":
                    raise ContractValidationError(
                        f"Empty staging slot must remain awaiting_real_input: {staging_path} {sample_mapping.get('sample_slot_id')}"
                    )
                continue

            if sample_mapping.get("current_state") != "candidate_approved_for_annotation":
                raise ContractValidationError(
                    f"Filled staging slot must remain candidate_approved_for_annotation: {staging_path} {sample_mapping.get('sample_slot_id')}"
                )
            if sample_mapping.get("ready_for_formal_writeflow") is not False:
                raise ContractValidationError(
                    f"Candidate staging slots must not mark ready_for_formal_writeflow=true before formal writeflow: {staging_path}"
                )
            if sample_mapping.get("target_type") != "product":
                raise ContractValidationError(f"Staging target_type must stay product: {staging_path}")
            if sample_mapping.get("training_pool_source") != "candidate_pool":
                raise ContractValidationError(f"Staging training_pool_source must stay candidate_pool: {staging_path}")

            candidate_ref = _require_mapping(
                sample_mapping.get("candidate_prescreen_ref"),
                f"{staging_path}:candidate_prescreen_ref",
            )
            candidate_id = _require_non_empty_string(
                candidate_ref.get("candidate_id"),
                f"{staging_path}:candidate_prescreen_ref:candidate_id",
            )
            if candidate_id != sample_mapping.get("sample_id"):
                raise ContractValidationError(f"sample_id must match candidate_prescreen_ref.candidate_id: {staging_path}")
            if candidate_ref.get("human_review_status") != "approved_for_staging":
                raise ContractValidationError(
                    f"Filled staging slots must come from approved_for_staging handoff candidates: {staging_path}"
                )

            source_record_refs = sample_mapping.get("source_record_refs")
            if not isinstance(source_record_refs, list) or not source_record_refs:
                raise ContractValidationError(f"Filled staging slot must retain source_record_refs: {staging_path}")
            for index, entry in enumerate(source_record_refs, start=1):
                ref = _require_mapping(entry, f"{staging_path}:source_record_refs[{index}]")
                _require_non_empty_string(ref.get("candidate_id"), f"{staging_path}:source_record_refs[{index}].candidate_id")
                _require_non_empty_string(
                    ref.get("candidate_document_path"),
                    f"{staging_path}:source_record_refs[{index}].candidate_document_path",
                )
                _require_non_empty_string(ref.get("source_id"), f"{staging_path}:source_record_refs[{index}].source_id")
                _require_non_empty_string(ref.get("external_id"), f"{staging_path}:source_record_refs[{index}].external_id")
                _require_non_empty_string(
                    ref.get("canonical_url"),
                    f"{staging_path}:source_record_refs[{index}].canonical_url",
                )
                normalize_candidate_url(
                    ref.get("canonical_url"),
                    field_name=f"{staging_path}:source_record_refs[{index}].canonical_url",
                )
            semantic_key = _sample_identity_key(sample_mapping)
            if semantic_key is not None:
                existing = seen_source_semantics.get(semantic_key)
                if existing is not None:
                    existing_path, existing_slot_id, existing_sample_id = existing
                    raise ContractValidationError(
                        "Duplicate source URL key in staging workspace: "
                        f"{semantic_key[0]}::{semantic_key[1]} appears in "
                        f"{existing_path} {existing_slot_id} ({existing_sample_id}) and "
                        f"{staging_path} {sample_mapping.get('sample_slot_id')} ({sample_mapping.get('sample_id')})"
                    )
                seen_source_semantics[semantic_key] = (
                    staging_path,
                    str(sample_mapping.get("sample_slot_id")),
                    str(sample_mapping.get("sample_id")),
                )
    return progress


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
    normalized_canonical_url = normalize_candidate_url(
        candidate_record.get("canonical_url"),
        field_name="candidate_prescreen_record.canonical_url",
    )
    return [
        {
            "candidate_id": candidate_record["candidate_id"],
            "candidate_document_path": str(candidate_path),
            "source": candidate_record["source"],
            "source_id": candidate_record["source_id"],
            "source_window": candidate_record["source_window"],
            "external_id": candidate_record["external_id"],
            "canonical_url": normalized_canonical_url,
            "sample_key": candidate_record.get("sample_key"),
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
    candidate_record["canonical_url"] = normalize_candidate_url(
        candidate_record.get("canonical_url"),
        field_name="candidate_prescreen_record.canonical_url",
    )
    sample_id = str(candidate_record["candidate_id"])
    candidate_batch_id = str(candidate_record["candidate_batch_id"])
    source_record_refs = _source_record_refs(candidate_record, candidate_path)
    candidate_ref = _candidate_ref(candidate_record, candidate_path)
    candidate_sample_key = candidate_record.get("sample_key")
    if isinstance(candidate_sample_key, str) and candidate_sample_key.strip():
        candidate_semantic_key = ("sample_key", candidate_sample_key.strip())
    else:
        candidate_url_key = candidate_url_dedupe_key(
            candidate_record.get("source_id"),
            candidate_record.get("canonical_url"),
            source_field_name="candidate_prescreen_record.source_id",
            url_field_name="candidate_prescreen_record.canonical_url",
        )
        candidate_semantic_key = ("source_url", f"{candidate_url_key[0]}::{candidate_url_key[1]}")
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
            semantic_key = _sample_identity_key(sample)
            if semantic_key == candidate_semantic_key:
                raise ContractValidationError(
                    "Semantic duplicate source URL already present in staging: "
                    f"{candidate_semantic_key[0]}::{candidate_semantic_key[1]} at "
                    f"{staging_path} {sample.get('sample_slot_id')} ({sample.get('sample_id')})"
                )
        for sample in samples:
            if not isinstance(sample, dict):
                continue
            if not _sample_is_filled(sample) and sample.get("current_state") == "awaiting_real_input":
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
    sample_metadata["sample_key"] = candidate_record.get("sample_key")
    pool_trace = sample_metadata.get("pool_trace")
    if not isinstance(pool_trace, dict):
        raise ContractValidationError("staging sample_metadata.pool_trace must be a mapping")
    pool_trace["candidate_pool_batch_id"] = candidate_batch_id
    pool_trace["training_pool_source"] = "candidate_pool"
    pool_trace["whitelist_reason"] = candidate_record.get("whitelist_reason")
    sample["staged_from_candidate_prescreen_at"] = now_iso
    sample["staged_from_candidate_prescreen_path"] = str(candidate_path)
