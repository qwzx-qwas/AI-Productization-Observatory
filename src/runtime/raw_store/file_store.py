"""File-backed raw snapshot storage with deterministic key naming and dedupe."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from src.common.errors import ProcessingError
from src.common.files import dump_json, ensure_parent, load_json, utc_now_iso

if os.name == "nt":
    import msvcrt
else:
    import fcntl


class FileRawStore:
    """Stores raw payloads as gzip-compressed JSON while preserving stable audit refs."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    @property
    def lock_path(self) -> Path:
        return self.root_dir / ".raw_store.lock"

    @property
    def record_index_path(self) -> Path:
        return self.root_dir / "raw_records.json"

    def _load_record_index_unlocked(self) -> list[dict[str, Any]]:
        if not self.record_index_path.exists():
            return []
        try:
            payload = load_json(self.record_index_path)
        except json.JSONDecodeError as exc:
            raise ProcessingError("storage_write_failed", f"Raw record index is not valid JSON: {self.record_index_path}") from exc
        if not isinstance(payload, list):
            raise ProcessingError("storage_write_failed", f"Raw record index must be a JSON list: {self.record_index_path}")
        return payload

    def _write_record_index_unlocked(self, records: list[dict[str, Any]]) -> None:
        dump_json(self.record_index_path, records)

    def _resolve_fetch_url(self, item: dict[str, Any]) -> str | None:
        for field_name in ("product_url", "html_url", "url", "canonical_url"):
            value = item.get(field_name)
            if isinstance(value, str) and value:
                return value
        return None

    def _find_existing_record(
        self,
        records: list[dict[str, Any]],
        *,
        source_id: str,
        external_id: str,
        content_hash: str,
    ) -> dict[str, Any] | None:
        for record in records:
            if (
                record.get("source_id") == source_id
                and record.get("external_id") == external_id
                and record.get("content_hash") == content_hash
            ):
                return dict(record)
        return None

    def _exclusive_lock(self):
        ensure_parent(self.lock_path)
        return self.lock_path.open("a+", encoding="utf-8")

    def store_items(self, crawl_run: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        seen_dedupe_keys: set[tuple[str, str, str]] = set()

        with self._exclusive_lock() as handle:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                indexed_records = self._load_record_index_unlocked()
                for item in items:
                    try:
                        payload_text = json.dumps(item, sort_keys=True, ensure_ascii=True)
                    except TypeError as exc:
                        raise ProcessingError("parse_failure", f"Raw payload is not JSON serialisable: {exc}") from exc

                    source_id = crawl_run["source_id"]
                    try:
                        external_id = item["external_id"]
                    except KeyError as exc:
                        raise ProcessingError("parse_failure", f"Raw payload is missing external_id: {item}") from exc
                    content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
                    dedupe_key = (source_id, external_id, content_hash)
                    if dedupe_key in seen_dedupe_keys:
                        continue
                    seen_dedupe_keys.add(dedupe_key)

                    existing = self._find_existing_record(
                        indexed_records,
                        source_id=source_id,
                        external_id=external_id,
                        content_hash=content_hash,
                    )
                    if existing is not None:
                        records.append(existing)
                        continue

                    raw_id = hashlib.sha256(f"{source_id}:{external_id}:{content_hash}".encode("utf-8")).hexdigest()[:20]
                    object_key = (
                        f"{source_id}/window_start={crawl_run['window_start'][:10]}/"
                        f"{external_id}/{content_hash}.json.gz"
                    )
                    object_path = self.root_dir / object_key
                    object_path.parent.mkdir(parents=True, exist_ok=True)

                    if not object_path.exists():
                        try:
                            with gzip.open(object_path, "wt", encoding="utf-8") as object_handle:
                                object_handle.write(payload_text)
                        except OSError as exc:
                            raise ProcessingError(
                                "storage_write_failed",
                                f"Failed to write raw object {object_path}: {exc}",
                            ) from exc

                    record = {
                        "raw_id": raw_id,
                        "crawl_run_id": crawl_run["crawl_run_id"],
                        "source_id": source_id,
                        "external_id": external_id,
                        "fetch_url": self._resolve_fetch_url(item),
                        "fetched_at": crawl_run["collected_at"],
                        "content_hash": content_hash,
                        "raw_payload_ref": object_key,
                        "http_status": None,
                        "watermark_before": crawl_run["watermark_before"],
                        "request_params": crawl_run["request_params"],
                        "collected_at": crawl_run["collected_at"],
                        "stored_at": utc_now_iso(),
                    }
                    indexed_records.append(record)
                    records.append(record)

                self._write_record_index_unlocked(indexed_records)
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return records

    def load_payload(self, raw_payload_ref: str) -> dict[str, Any]:
        object_path = self.root_dir / raw_payload_ref
        try:
            with gzip.open(object_path, "rt", encoding="utf-8") as handle:
                return json.loads(handle.read())
        except FileNotFoundError as exc:
            raise ProcessingError("storage_write_failed", f"Missing raw payload ref: {raw_payload_ref}") from exc
        except OSError as exc:
            raise ProcessingError("parse_failure", f"Failed to read raw payload ref: {raw_payload_ref}") from exc
