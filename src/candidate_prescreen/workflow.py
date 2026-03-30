"""End-to-end candidate prescreen workflow helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.candidate_prescreen.config import candidate_batch_id, candidate_id, load_candidate_prescreen_config
from src.candidate_prescreen.discovery import discover_candidates, discovery_metadata
from src.candidate_prescreen.relay import screen_candidate
from src.candidate_prescreen.staging import handoff_candidate_to_staging
from src.common.config import AppConfig
from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from src.common.schema import validate_instance


def _schema_path(config: AppConfig) -> Path:
    return config.schema_dir / "candidate_prescreen_record.schema.json"


def _candidate_doc_path(config: AppConfig, source: str, window: str, candidate_identifier: str) -> Path:
    return config.candidate_workspace_dir / source / window.replace("..", "_") / f"{candidate_identifier}.yaml"


def _source_summary(item: dict[str, Any]) -> str:
    summary = item.get("summary")
    if isinstance(summary, str):
        return summary
    return ""


def _raw_excerpt(item: dict[str, Any]) -> str:
    excerpt = item.get("raw_evidence_excerpt")
    if isinstance(excerpt, str):
        return excerpt
    return ""


def _candidate_input(item: dict[str, Any], metadata: dict[str, Any], window: str) -> dict[str, Any]:
    return {
        "source": metadata["source_id"].replace("src_", ""),
        "source_id": metadata["source_id"],
        "source_window": window,
        "time_field": metadata["time_field"],
        "external_id": str(item["external_id"]),
        "canonical_url": item["canonical_url"],
        "title": item["title"],
        "summary": _source_summary(item),
        "raw_evidence_excerpt": _raw_excerpt(item),
        "query_family": metadata["query_family"],
        "query_slice_id": metadata["query_slice_id"],
        "selection_rule_version": metadata["selection_rule_version"],
    }


def _empty_prescreen_record(
    candidate_input: dict[str, Any],
    *,
    batch_id: str,
    candidate_identifier: str,
    metadata: dict[str, Any],
    llm_defaults: dict[str, Any],
    discovery_mode: str,
) -> dict[str, Any]:
    now_iso = utc_now_iso()
    return {
        "document_type": "candidate_prescreen_record",
        "document_version": "candidate_prescreen_v1",
        "candidate_id": candidate_identifier,
        "candidate_batch_id": batch_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "source": candidate_input["source"],
        "source_id": candidate_input["source_id"],
        "source_window": candidate_input["source_window"],
        "time_field": candidate_input["time_field"],
        "external_id": candidate_input["external_id"],
        "canonical_url": candidate_input["canonical_url"],
        "title": candidate_input["title"],
        "summary": candidate_input["summary"],
        "raw_evidence_excerpt": candidate_input["raw_evidence_excerpt"],
        "query_family": candidate_input["query_family"],
        "query_slice_id": candidate_input["query_slice_id"],
        "selection_rule_version": candidate_input["selection_rule_version"],
        "source_trace": {
            "discovery_mode": discovery_mode,
            "selection_basis": metadata["selection_basis"],
            "source_item_ref": {
                "source": candidate_input["source"],
                "source_id": candidate_input["source_id"],
                "source_window": candidate_input["source_window"],
                "external_id": candidate_input["external_id"],
                "canonical_url": candidate_input["canonical_url"],
            },
        },
        "llm_prescreen": {
            "status": "failed",
            "in_observatory_scope": None,
            "reason": None,
            "source_evidence_summary": [],
            "uncertainty_points": [],
            "recommend_candidate_pool": None,
            "recommended_action": None,
            "taxonomy_hints": {
                "primary_category_code": None,
                "secondary_category_code": None,
                "primary_persona_code": None,
                "delivery_form_code": None,
            },
            "assessment_hints": {
                "evidence_strength": None,
                "build_evidence_band": None,
                "need_clarity_band": None,
                "unresolved_risk": None,
            },
            "channel_metadata": {
                "prompt_version": llm_defaults["prompt_version"],
                "routing_version": llm_defaults["routing_version"],
                "relay_client_version": llm_defaults["relay_client_version"],
                "model": None,
                "transport": llm_defaults["relay_transport"],
                "request_id": None,
            },
            "error_type": None,
            "error_message": None,
        },
        "whitelist_reason": None,
        "human_review_status": "pending_first_pass",
        "human_review_notes": None,
        "human_reviewed_at": None,
        "staging_handoff": {
            "status": "not_started",
            "staging_document_path": None,
            "sample_slot_id": None,
            "sample_id": None,
            "blocking_items": [],
            "last_attempted_at": None,
        },
    }


def _validate_candidate_record(config: AppConfig, record: dict[str, Any]) -> None:
    validate_instance(record, _schema_path(config))


def run_candidate_prescreen(
    config: AppConfig,
    *,
    source_code: str,
    window: str,
    query_slice_id: str | None,
    limit: int,
    discovery_fixture_path: Path | None,
    llm_fixture_path: Path | None,
) -> list[Path]:
    workflow_config = load_candidate_prescreen_config(config.config_dir)
    llm_defaults = workflow_config["llm_prescreen"]
    discovery_mode = "fixture" if discovery_fixture_path is not None else "live"
    items = discover_candidates(
        workflow_config,
        source_code=source_code,
        window=window,
        query_slice_id=query_slice_id,
        limit=limit,
        fixture_path=discovery_fixture_path,
        timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
    )
    metadata = discovery_metadata(
        workflow_config,
        source_code=source_code,
        window=window,
        query_slice_id=query_slice_id,
        discovery_mode=discovery_mode,
    )
    batch_id = candidate_batch_id(source_code, window, metadata["query_slice_id"])
    written_paths: list[Path] = []
    for item in items:
        candidate_input = _candidate_input(item, metadata, window)
        candidate_identifier = candidate_id(source_code, window, metadata["query_slice_id"], candidate_input["external_id"])
        record = _empty_prescreen_record(
            candidate_input,
            batch_id=batch_id,
            candidate_identifier=candidate_identifier,
            metadata=metadata,
            llm_defaults=llm_defaults,
            discovery_mode=discovery_mode,
        )
        try:
            llm_result = screen_candidate(
                candidate_input,
                prompt_version=str(llm_defaults["prompt_version"]),
                routing_version=str(llm_defaults["routing_version"]),
                relay_transport=str(llm_defaults["relay_transport"]),
                relay_client_version=str(llm_defaults["relay_client_version"]),
                fixture_path=llm_fixture_path,
                timeout_seconds=int(llm_defaults["timeout_seconds_default"]),
                max_retries=int(llm_defaults["max_retries_default"]),
            )
        except ProcessingError as exc:
            record["llm_prescreen"]["status"] = "failed"
            record["llm_prescreen"]["error_type"] = exc.error_type
            record["llm_prescreen"]["error_message"] = str(exc)
        else:
            record["llm_prescreen"]["status"] = "succeeded"
            record["llm_prescreen"]["in_observatory_scope"] = llm_result["in_observatory_scope"]
            record["llm_prescreen"]["reason"] = llm_result["reason"]
            record["llm_prescreen"]["source_evidence_summary"] = llm_result["source_evidence_summary"]
            record["llm_prescreen"]["uncertainty_points"] = llm_result["uncertainty_points"]
            record["llm_prescreen"]["recommend_candidate_pool"] = llm_result["recommend_candidate_pool"]
            record["llm_prescreen"]["recommended_action"] = llm_result["recommended_action"]
            record["llm_prescreen"]["taxonomy_hints"] = llm_result["taxonomy_hints"]
            record["llm_prescreen"]["assessment_hints"] = llm_result["assessment_hints"]
            record["llm_prescreen"]["channel_metadata"] = llm_result["channel_metadata"]
            record["llm_prescreen"]["error_type"] = None
            record["llm_prescreen"]["error_message"] = None
        record["updated_at"] = utc_now_iso()
        output_path = _candidate_doc_path(config, source_code, window, candidate_identifier)
        _validate_candidate_record(config, record)
        dump_yaml(output_path, record)
        written_paths.append(output_path)
    return written_paths


def validate_candidate_workspace(config: AppConfig) -> int:
    if config.candidate_workspace_dir == config.gold_set_dir or config.gold_set_dir in config.candidate_workspace_dir.parents:
        raise ContractValidationError("candidate workspace must stay outside gold_set/")
    if not config.candidate_workspace_dir.exists():
        return 0
    candidate_ids: set[str] = set()
    count = 0
    for path in sorted(config.candidate_workspace_dir.rglob("*.yaml")):
        if path.name.startswith("."):
            continue
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            raise ContractValidationError(f"Candidate prescreen document must be a mapping: {path}")
        _validate_candidate_record(config, payload)
        candidate_identifier = payload["candidate_id"]
        if candidate_identifier in candidate_ids:
            raise ContractValidationError(f"Duplicate candidate_id in candidate workspace: {candidate_identifier}")
        candidate_ids.add(candidate_identifier)
        count += 1
    return count


def handoff_candidates_to_staging(
    config: AppConfig,
    *,
    candidate_ids: list[str] | None,
) -> list[tuple[Path, str, str]]:
    results: list[tuple[Path, str, str]] = []
    selected = set(candidate_ids or [])
    for path in sorted(config.candidate_workspace_dir.rglob("*.yaml")):
        payload = load_yaml(path)
        if not isinstance(payload, dict):
            continue
        _validate_candidate_record(config, payload)
        candidate_identifier = str(payload["candidate_id"])
        if selected and candidate_identifier not in selected:
            continue
        if payload["human_review_status"] != "approved_for_staging":
            continue
        staging_document_path, slot_id = handoff_candidate_to_staging(
            payload,
            candidate_path=path,
            staging_dir=config.gold_set_staging_dir,
        )
        payload["staging_handoff"] = {
            "status": "written",
            "staging_document_path": staging_document_path,
            "sample_slot_id": slot_id,
            "sample_id": candidate_identifier,
            "blocking_items": [],
            "last_attempted_at": utc_now_iso(),
        }
        payload["updated_at"] = utc_now_iso()
        _validate_candidate_record(config, payload)
        dump_yaml(path, payload)
        results.append((path, staging_document_path, slot_id))
    return results
