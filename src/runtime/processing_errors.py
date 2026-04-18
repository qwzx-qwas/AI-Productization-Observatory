"""File-backed processing_error registry derived from runtime task failures."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from src.common.files import dump_json, ensure_parent, load_json, utc_now_iso
from src.common.errors import ContractValidationError

if os.name == "nt":
    import msvcrt
else:
    import fcntl


_TASK_TYPE_TO_MODULE_NAME = {
    "pull_collect": "pull_collector",
    "normalize_raw": "normalizer",
    "resolve_entity_batch": "entity_resolver",
    "build_observation_batch": "observation_builder",
    "extract_evidence_batch": "evidence_extractor",
    "profile_product_batch": "product_profiler",
    "classify_taxonomy_batch": "taxonomy_classifier",
    "score_product_batch": "score_engine",
    "build_review_packet": "review_packet_builder",
    "build_mart_window": "mart_builder",
}


def default_processing_error_store_path(task_store_path: Path) -> Path:
    return task_store_path.with_name("processing_errors.json")


class FileProcessingErrorStore:
    """Persists technical failures as canonical processing_error facts."""

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

    def _load_errors_unlocked(self) -> list[dict[str, Any]]:
        if not self.store_path.exists():
            return []
        try:
            payload = load_json(self.store_path)
        except json.JSONDecodeError as exc:
            raise ContractValidationError(f"processing_error store is not valid JSON: {self.store_path}") from exc
        if not isinstance(payload, list):
            raise ContractValidationError(f"processing_error store must contain a JSON list: {self.store_path}")
        return payload

    def _write_errors_unlocked(self, errors: list[dict[str, Any]]) -> None:
        dump_json(self.store_path, errors)

    def all_errors(self) -> list[dict[str, Any]]:
        with self._exclusive_lock():
            return self._load_errors_unlocked()

    def record_failure(
        self,
        task: dict[str, Any],
        *,
        error_type: str,
        error_message: str,
        retry_count: int,
        resolution_status: str,
        failed_at: str | None = None,
        next_retry_at: str | None = None,
    ) -> dict[str, Any]:
        timestamp = failed_at or utc_now_iso()
        with self._exclusive_lock():
            errors = self._load_errors_unlocked()
            record = self._upsert_failure(
                errors,
                task=task,
                error_type=error_type,
                error_message=error_message,
                retry_count=retry_count,
                resolution_status=resolution_status,
                failed_at=timestamp,
                next_retry_at=next_retry_at,
            )
            self._write_errors_unlocked(errors)
            return record

    def resolve_for_task(self, task: dict[str, Any], *, resolved_at: str | None = None) -> dict[str, Any] | None:
        timestamp = resolved_at or utc_now_iso()
        with self._exclusive_lock():
            errors = self._load_errors_unlocked()
            error_id = _error_id_for_task(task["task_id"])
            for record in errors:
                if record.get("error_id") != error_id:
                    continue
                record["resolution_status"] = "resolved"
                record["next_retry_at"] = None
                record["updated_at"] = timestamp
                self._write_errors_unlocked(errors)
                return dict(record)
            return None

    def _upsert_failure(
        self,
        errors: list[dict[str, Any]],
        *,
        task: dict[str, Any],
        error_type: str,
        error_message: str,
        retry_count: int,
        resolution_status: str,
        failed_at: str,
        next_retry_at: str | None,
    ) -> dict[str, Any]:
        error_id = _error_id_for_task(task["task_id"])
        for record in errors:
            if record.get("error_id") != error_id:
                continue
            record.update(
                {
                    "error_type": error_type,
                    "error_message": error_message,
                    "retry_count": retry_count,
                    "last_failed_at": failed_at,
                    "next_retry_at": next_retry_at,
                    "resolution_status": resolution_status,
                    "updated_at": failed_at,
                }
            )
            return dict(record)

        record = {
            "error_id": error_id,
            "module_name": _TASK_TYPE_TO_MODULE_NAME.get(task["task_type"], task["task_type"]),
            "run_id": task["task_id"],
            "source_id": task.get("source_id"),
            "raw_id": task.get("payload_json", {}).get("raw_id"),
            "source_item_id": task.get("payload_json", {}).get("source_item_id"),
            "target_type": task.get("target_type") or task.get("payload_json", {}).get("target_type"),
            "target_id": task.get("target_id") or task.get("payload_json", {}).get("target_id"),
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "first_failed_at": failed_at,
            "last_failed_at": failed_at,
            "next_retry_at": next_retry_at,
            "resolution_status": resolution_status,
            "created_at": failed_at,
            "updated_at": failed_at,
        }
        errors.append(record)
        return dict(record)


def _error_id_for_task(task_id: str) -> str:
    return f"perr_{task_id}"
