"""Structured logging helpers aligned with the error policy observability fields."""

from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON for deterministic local replay traces."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "message": record.getMessage(),
            "level": record.levelname,
            "module_name": getattr(record, "module_name", record.name),
            "source_id": getattr(record, "source_id", None),
            "run_id": getattr(record, "run_id", None),
            "task_id": getattr(record, "task_id", None),
            "error_type": getattr(record, "error_type", None),
            "retry_count": getattr(record, "retry_count", None),
            "resolution_status": getattr(record, "resolution_status", None),
        }
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


def get_logger(module_name: str, **context: Any) -> logging.LoggerAdapter[logging.Logger]:
    logger = logging.getLogger(module_name)
    return logging.LoggerAdapter(logger, {"module_name": module_name, **context})
