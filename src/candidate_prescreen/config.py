"""Configuration helpers for the candidate prescreen workflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.candidate_prescreen.url_utils import normalize_candidate_url
from src.common.errors import ContractValidationError
from src.common.files import load_yaml


def load_candidate_prescreen_config(config_dir: Path) -> dict[str, Any]:
    payload = load_yaml(config_dir / "candidate_prescreen_workflow.yaml")
    if not isinstance(payload, dict):
        raise ContractValidationError("candidate_prescreen_workflow.yaml must be a mapping")
    return payload


def source_config(workflow_config: dict[str, Any], source_code: str) -> dict[str, Any]:
    sources = workflow_config.get("sources")
    if not isinstance(sources, list):
        raise ContractValidationError("candidate_prescreen_workflow.yaml:sources must be a list")
    for entry in sources:
        if isinstance(entry, dict) and entry.get("source_code") == source_code:
            return entry
    raise ContractValidationError(f"candidate_prescreen_workflow.yaml is missing source definition for {source_code}")


def query_slice_config(workflow_config: dict[str, Any], source_code: str, query_slice_id: str | None) -> dict[str, Any]:
    source = source_config(workflow_config, source_code)
    slices = source.get("query_slices")
    if not isinstance(slices, list) or not slices:
        raise ContractValidationError(f"candidate_prescreen_workflow.yaml:{source_code}:query_slices must be a non-empty list")
    if query_slice_id is None:
        first = slices[0]
        if not isinstance(first, dict):
            raise ContractValidationError(f"candidate_prescreen_workflow.yaml:{source_code}:query_slices[0] must be a mapping")
        return first
    for entry in slices:
        if isinstance(entry, dict) and entry.get("query_slice_id") == query_slice_id:
            return entry
    raise ContractValidationError(
        f"candidate_prescreen_workflow.yaml:{source_code}:query_slices is missing query_slice_id={query_slice_id}"
    )


def candidate_batch_id(source_code: str, window: str, query_slice_id: str | None) -> str:
    window_key = window.replace("..", "_")
    slice_key = query_slice_id or "default"
    return f"candidate_batch_{source_code}_{slice_key}_{window_key}"


def candidate_id(source_code: str, window: str, query_slice_id: str | None, external_id: str) -> str:
    raw_key = f"{source_code}:{window}:{query_slice_id or 'default'}:{external_id}"
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:12]
    slice_key = query_slice_id or "default"
    return f"cand_{source_code}_{slice_key}_{digest}"


def build_sample_key(source_id: str, canonical_url: str) -> str:
    normalized_url = normalize_candidate_url(canonical_url, field_name="candidate_prescreen.canonical_url")
    raw_key = f"{source_id}:{normalized_url}"
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"sample_{digest}"


def build_analysis_run_key(
    *,
    sample_key: str,
    cleaned_candidate_input: dict[str, Any],
    prompt_version: str,
    routing_version: str,
    relay_client_version: str,
    payload_builder_version: str,
) -> str:
    serialized_input = json.dumps(cleaned_candidate_input, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    raw_key = "::".join(
        [
            sample_key,
            serialized_input,
            prompt_version,
            routing_version,
            relay_client_version,
            payload_builder_version,
        ]
    )
    digest = hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16]
    return f"analysis_{digest}"
