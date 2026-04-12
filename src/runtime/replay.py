"""Replay entrypoints that connect the fixture collector, raw store, normalizer, and tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from src.collectors.github import collect_fixture_window as collect_github_fixture_window
from src.collectors.product_hunt import collect_fixture_window as collect_product_hunt_fixture_window
from src.common.config import AppConfig
from src.common.constants import RETRY_POLICY, WINDOW_SEPARATOR
from src.common.errors import ConfigError, ProcessingError
from src.common.files import load_json, utc_now_iso
from src.marts.builder import build_mart_from_fixture
from src.normalizers.github import normalize_raw_record as normalize_github_raw_record
from src.normalizers.product_hunt import normalize_raw_record as normalize_product_hunt_raw_record
from src.runtime.models import default_payload
from src.runtime.raw_store.file_store import FileRawStore
from src.runtime.tasks import FileTaskStore

CollectorFn = Callable[..., dict[str, Any]]
NormalizerFn = Callable[[dict[str, Any], FileRawStore, Path], dict[str, Any]]

_SOURCE_REPLAY_REGISTRY: dict[str, dict[str, object]] = {
    "product_hunt": {
        "source_id": "src_product_hunt",
        "default_fixture_name": "product_hunt_window.json",
        "collector": collect_product_hunt_fixture_window,
        "normalizer": normalize_product_hunt_raw_record,
    },
    "github": {
        "source_id": "src_github",
        "default_fixture_name": "github_qf_agent_window.json",
        "collector": collect_github_fixture_window,
        "normalizer": normalize_github_raw_record,
    },
}


def parse_window(window: str) -> tuple[str, str]:
    if WINDOW_SEPARATOR not in window:
        raise ConfigError(f"Window must use '{WINDOW_SEPARATOR}' separator, got: {window}")
    start, end = window.split(WINDOW_SEPARATOR, maxsplit=1)
    if not start or not end:
        raise ConfigError(f"Window must be non-empty on both sides: {window}")
    return start, end


def replay_source_window(
    *,
    source_code: str,
    window: str,
    config: AppConfig,
    fixture_name: str | None = None,
) -> dict[str, object]:
    window_start, window_end = parse_window(window)
    source_spec = _SOURCE_REPLAY_REGISTRY.get(source_code)
    if source_spec is None:
        supported = ", ".join(sorted(_SOURCE_REPLAY_REGISTRY))
        raise ConfigError(f"Unsupported replay source: {source_code}. Supported sources: {supported}")

    fixture_path = config.fixtures_dir / "collector" / (fixture_name or str(source_spec["default_fixture_name"]))
    source_id = str(source_spec["source_id"])

    payload = _build_replay_payload(
        source_code=source_code,
        window_start=window_start,
        window_end=window_end,
        fixture_path=fixture_path,
    )
    payload.update(
        {
            "replay_reason": "same_window_fixture_replay",
            "replay_basis": "deterministic_fixture",
            "requested_at": utc_now_iso(),
        }
    )

    task_store = FileTaskStore(config.task_store_path)
    task = task_store.create_replay_task(
        source_id=source_id,
        task_type="pull_collect",
        task_scope="per_source_window",
        window_start=window_start,
        window_end=window_end,
        payload_json=payload,
        max_attempts=RETRY_POLICY["network_error"]["default_max_retries"],
    )

    task_store.claim(task.task_id, worker_id="local-cli")
    task_store.start(task.task_id)
    task_store.heartbeat(task.task_id, worker_id="local-cli")

    try:
        collector_output = _collect_source_window(
            source_code=source_code,
            fixture_path=fixture_path,
            window_start=window_start,
            window_end=window_end,
            payload=payload,
            collector=source_spec["collector"],
        )
        raw_store = FileRawStore(config.raw_store_dir)
        raw_records = raw_store.store_items(collector_output["crawl_run"], collector_output["items"])
        source_item_schema = config.schema_dir / "source_item.schema.json"
        normalizer = source_spec["normalizer"]
        source_items = [normalizer(record, raw_store, source_item_schema) for record in raw_records]
    except ProcessingError as exc:
        task_store.fail(task.task_id, exc.error_type, str(exc))
        raise

    task_store.succeed(task.task_id)
    crawl_run = dict(collector_output["crawl_run"])
    crawl_run["run_status"] = "success"
    crawl_run["finished_at"] = utc_now_iso()
    crawl_run["error_summary"] = None
    crawl_run["watermark_after"] = _compute_watermark_after(
        source_code=source_code,
        items=collector_output["items"],
        watermark_before=crawl_run["watermark_before"],
    )

    return {
        "task_id": task.task_id,
        "crawl_run": crawl_run,
        "raw_records": raw_records,
        "source_items": source_items,
    }


def build_mart_window(config: AppConfig, fixture_name: str = "effective_results_window.json") -> dict[str, object]:
    fixture_path = config.fixtures_dir / "marts" / fixture_name
    try:
        fixture = load_json(fixture_path)
    except json.JSONDecodeError as exc:
        raise ProcessingError("parse_failure", str(exc)) from exc

    task_store = FileTaskStore(config.task_store_path)
    payload = default_payload(
        source_code="mart_builder",
        window_start=fixture["window_start"],
        window_end=fixture["window_end"],
        task_type="build_mart_window",
    )
    payload.update(
        {
            "replay_reason": "same_window_fixture_rebuild",
            "replay_basis": "effective_result_fixture",
            "effective_result_policy": "effective_resolved_only",
            "main_stat_source_predicate": "enabled = true and primary_role = supply_primary",
            "requested_at": utc_now_iso(),
        }
    )

    task = task_store.create_replay_task(
        source_id=None,
        task_type="build_mart_window",
        task_scope="metric_window_batch",
        window_start=fixture["window_start"],
        window_end=fixture["window_end"],
        payload_json=payload,
        max_attempts=RETRY_POLICY["storage_write_failed"]["default_max_retries"],
    )
    task_store.claim(task.task_id, worker_id="local-cli")
    task_store.start(task.task_id)
    task_store.heartbeat(task.task_id, worker_id="local-cli")

    try:
        output_path = config.mart_output_dir / "mart_window.json"
        mart = build_mart_from_fixture(fixture_path, config.config_dir / "source_registry.yaml", output_path)
    except ProcessingError as exc:
        task_store.fail(task.task_id, exc.error_type, str(exc))
        raise
    except (KeyError, TypeError, ValueError) as exc:
        task_store.fail(task.task_id, "json_schema_validation_failed", str(exc))
        raise ProcessingError("json_schema_validation_failed", str(exc)) from exc

    task_store.succeed(task.task_id)
    return {"task_id": task.task_id, "mart": mart}


def build_default_mart(config: AppConfig) -> dict[str, object]:
    return build_mart_window(config)["mart"]


def _build_replay_payload(
    *,
    source_code: str,
    window_start: str,
    window_end: str,
    fixture_path: Path,
) -> dict[str, Any]:
    payload = default_payload(source_code=source_code, window_start=window_start, window_end=window_end, task_type="pull_collect")
    if source_code != "github":
        return payload

    try:
        fixture = load_json(fixture_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProcessingError("parse_failure", f"GitHub replay fixture is not readable JSON: {fixture_path}") from exc
    request_params = fixture.get("request_params")
    if not isinstance(request_params, dict):
        raise ProcessingError("parse_failure", f"GitHub replay fixture must include request_params: {fixture_path}")

    selection_rule_version = request_params.get("selection_rule_version")
    query_slice_id = request_params.get("query_slice_id")
    if not selection_rule_version or not query_slice_id:
        raise ProcessingError(
            "parse_failure",
            f"GitHub replay fixture must include selection_rule_version and query_slice_id: {fixture_path}",
        )

    payload["selection_rule_version"] = selection_rule_version
    payload["query_slice_id"] = query_slice_id
    return payload


def _collect_source_window(
    *,
    source_code: str,
    fixture_path: Path,
    window_start: str,
    window_end: str,
    payload: dict[str, Any],
    collector: object,
) -> dict[str, Any]:
    expected_window_start = f"{window_start}T00:00:00Z" if "T" not in window_start else window_start
    expected_window_end = f"{window_end}T00:00:00Z" if "T" not in window_end else window_end
    collector_fn = collector if callable(collector) else None
    if collector_fn is None:
        raise ConfigError(f"Collector for source {source_code} is not callable")

    if source_code == "github":
        return collector_fn(
            fixture_path,
            expected_source_code=source_code,
            expected_window_start=expected_window_start,
            expected_window_end=expected_window_end,
            expected_query_slice_id=payload.get("query_slice_id"),
            expected_selection_rule_version=payload.get("selection_rule_version"),
        )

    return collector_fn(
        fixture_path,
        expected_source_code=source_code,
        expected_window_start=expected_window_start,
        expected_window_end=expected_window_end,
    )


def _compute_watermark_after(
    *,
    source_code: str,
    items: list[dict[str, Any]],
    watermark_before: dict[str, Any],
) -> dict[str, Any]:
    if source_code == "product_hunt":
        time_field_name = "published_at"
        marker_field_name = "window_key"
    elif source_code == "github":
        time_field_name = "pushed_at"
        marker_field_name = "time_field"
    else:
        raise ConfigError(f"Unsupported replay source for watermark calculation: {source_code}")

    best_item = max(items, key=lambda item: (str(item.get(time_field_name) or ""), str(item.get("external_id") or "")))
    best_time_value = best_item.get(time_field_name)
    best_external_id = best_item.get("external_id")
    if not isinstance(best_time_value, str) or not isinstance(best_external_id, str):
        raise ProcessingError(
            "parse_failure",
            f"{source_code} replay items must include {time_field_name} and external_id for watermark_after",
        )

    return {
        marker_field_name: watermark_before.get(marker_field_name, time_field_name),
        time_field_name: best_time_value,
        "external_id": best_external_id,
    }
