"""Replay entrypoints that connect the fixture collector, raw store, normalizer, and tasks."""

from __future__ import annotations

import json

from src.collectors.product_hunt import collect_fixture_window
from src.common.config import AppConfig
from src.common.constants import RETRY_POLICY, WINDOW_SEPARATOR
from src.common.errors import ConfigError, ProcessingError
from src.common.files import load_json, utc_now_iso
from src.marts.builder import build_mart_from_fixture
from src.normalizers.product_hunt import normalize_raw_record
from src.runtime.models import default_payload
from src.runtime.raw_store.file_store import FileRawStore
from src.runtime.tasks import FileTaskStore


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
    fixture_name: str = "product_hunt_window.json",
) -> dict[str, object]:
    window_start, window_end = parse_window(window)
    if source_code != "product_hunt":
        raise ConfigError(f"Only product_hunt fixture replay is implemented in the minimal baseline, got: {source_code}")

    source_id = "src_product_hunt"
    payload = default_payload(source_code=source_code, window_start=window_start, window_end=window_end, task_type="pull_collect")
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
        fixture_path = config.fixtures_dir / "collector" / fixture_name
        collector_output = collect_fixture_window(
            fixture_path,
            expected_source_code=source_code,
            expected_window_start=f"{window_start}T00:00:00Z" if "T" not in window_start else window_start,
            expected_window_end=f"{window_end}T00:00:00Z" if "T" not in window_end else window_end,
        )
        raw_store = FileRawStore(config.raw_store_dir)
        raw_records = raw_store.store_items(collector_output["crawl_run"], collector_output["items"])
        source_item_schema = config.schema_dir / "source_item.schema.json"
        source_items = [normalize_raw_record(record, raw_store, source_item_schema) for record in raw_records]
    except ProcessingError as exc:
        task_store.fail(task.task_id, exc.error_type, str(exc))
        raise

    task_store.succeed(task.task_id)

    return {
        "task_id": task.task_id,
        "crawl_run": collector_output["crawl_run"],
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
