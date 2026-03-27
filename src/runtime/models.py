"""Task and replay models for the local file-backed runtime skeleton."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.common.constants import DEFAULT_LEASE_TIMEOUT_SECONDS
from src.common.files import utc_now_iso


@dataclass
class TaskRecord:
    task_id: str
    task_type: str
    task_scope: str
    source_id: str | None
    target_type: str | None
    target_id: str | None
    window_start: str | None
    window_end: str | None
    payload_json: dict[str, Any]
    status: str
    attempt_count: int = 0
    max_attempts: int = 3
    scheduled_at: str = field(default_factory=utc_now_iso)
    available_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    parent_task_id: str | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_payload(source_code: str, window_start: str, window_end: str) -> dict[str, Any]:
    return {
        "source_code": source_code,
        "run_unit": "per_source + per_window",
        "window_key": "published_at" if source_code == "product_hunt" else None,
        "window_start": window_start,
        "window_end": window_end,
        "lease_timeout_seconds": DEFAULT_LEASE_TIMEOUT_SECONDS,
    }
