"""File-backed raw snapshot storage with deterministic key naming and dedupe."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from src.common.errors import ProcessingError
from src.common.files import utc_now_iso


class FileRawStore:
    """Stores raw payloads as gzip-compressed JSON while preserving stable audit refs."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir

    def store_items(self, crawl_run: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for item in items:
            try:
                payload_text = json.dumps(item, sort_keys=True, ensure_ascii=True)
            except TypeError as exc:
                raise ProcessingError("parse_failure", f"Raw payload is not JSON serialisable: {exc}") from exc

            external_id = item["external_id"]
            source_id = crawl_run["source_id"]
            content_hash = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
            raw_id = hashlib.sha256(f"{source_id}:{external_id}:{content_hash}".encode("utf-8")).hexdigest()[:20]
            object_key = (
                f"{source_id}/window_start={crawl_run['window_start'][:10]}/"
                f"{external_id}/{content_hash}.json.gz"
            )
            object_path = self.root_dir / object_key
            object_path.parent.mkdir(parents=True, exist_ok=True)

            if not object_path.exists():
                try:
                    with gzip.open(object_path, "wt", encoding="utf-8") as handle:
                        handle.write(payload_text)
                except OSError as exc:
                    raise ProcessingError("storage_write_failed", f"Failed to write raw object {object_path}: {exc}") from exc

            records.append(
                {
                    "raw_id": raw_id,
                    "crawl_run_id": crawl_run["crawl_run_id"],
                    "source_id": source_id,
                    "external_id": external_id,
                    "content_hash": content_hash,
                    "raw_payload_ref": object_key,
                    "watermark_before": crawl_run["watermark_before"],
                    "request_params": crawl_run["request_params"],
                    "collected_at": crawl_run["collected_at"],
                    "stored_at": utc_now_iso(),
                }
            )
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
