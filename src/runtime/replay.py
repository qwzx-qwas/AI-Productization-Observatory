"""Replay entrypoints that connect the fixture collector, raw store, normalizer, and tasks."""

from __future__ import annotations

from src.collectors.product_hunt import collect_fixture_window
from src.common.config import AppConfig
from src.common.constants import RETRY_POLICY, WINDOW_SEPARATOR
from src.common.errors import ConfigError, ProcessingError
from src.common.files import utc_now_iso
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
    payload = default_payload(source_code=source_code, window_start=window_start, window_end=window_end)
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

    claimed = task_store.claim_next(worker_id="local-cli")
    if not claimed or claimed["task_id"] != task.task_id:
        raise ProcessingError("dependency_unavailable", f"Unable to claim replay task {task.task_id}")
    task_store.start(task.task_id)
    task_store.heartbeat(task.task_id, worker_id="local-cli")

    fixture_path = config.fixtures_dir / "collector" / fixture_name
    collector_output = collect_fixture_window(fixture_path)
    raw_store = FileRawStore(config.raw_store_dir)
    raw_records = raw_store.store_items(collector_output["crawl_run"], collector_output["items"])
    source_item_schema = config.schema_dir / "source_item.schema.json"
    source_items = [normalize_raw_record(record, raw_store, source_item_schema) for record in raw_records]
    task_store.succeed(task.task_id)

    return {
        "task_id": task.task_id,
        "crawl_run": collector_output["crawl_run"],
        "raw_records": raw_records,
        "source_items": source_items,
    }


def build_default_mart(config: AppConfig) -> dict[str, object]:
    fixture_path = config.fixtures_dir / "marts" / "effective_results_window.json"
    output_path = config.mart_output_dir / "mart_window.json"
    return build_mart_from_fixture(fixture_path, config.config_dir / "source_registry.yaml", output_path)
