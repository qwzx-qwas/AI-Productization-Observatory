"""Structured logging helpers aligned with the error policy observability fields."""

from __future__ import annotations

import json
import logging
from typing import Any


class JsonFormatter(logging.Formatter):
    """Render log records as one-line JSON for deterministic local replay traces."""

    @staticmethod
    def _message_payload(record: logging.LogRecord) -> dict[str, Any]:
        if isinstance(record.msg, dict):
            return dict(record.msg)
        if isinstance(record.msg, str):
            message_text = record.msg.strip()
            if message_text.startswith("{") and message_text.endswith("}"):
                try:
                    parsed = json.loads(message_text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    return parsed
        return {"message": record.getMessage()}

    def format(self, record: logging.LogRecord) -> str:
        payload = {key: value for key, value in self._message_payload(record).items() if value is not None}
        payload["level"] = record.levelname
        contextual_fields: dict[str, Any] = {
            "module_name": getattr(record, "module_name", record.name),
            "source_id": getattr(record, "source_id", None),
            "run_id": getattr(record, "run_id", None),
            "task_id": getattr(record, "task_id", None),
            "error_type": getattr(record, "error_type", None),
            "retry_count": getattr(record, "retry_count", None),
            "resolution_status": getattr(record, "resolution_status", None),
        }
        for key, value in contextual_fields.items():
            if value is None or key in payload:
                continue
            payload[key] = value
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
