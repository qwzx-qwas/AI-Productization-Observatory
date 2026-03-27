"""Project-wide constants centralised for replayable defaults."""

from __future__ import annotations

from pathlib import Path

DEFAULT_CONFIG_DIR = Path("configs")
DEFAULT_SCHEMA_DIR = Path("schemas")
DEFAULT_FIXTURES_DIR = Path("fixtures")
DEFAULT_RAW_STORE_DIR = Path(".runtime/raw_store")
DEFAULT_TASK_STORE_PATH = Path(".runtime/task_store/tasks.json")
DEFAULT_MART_OUTPUT_DIR = Path(".runtime/marts")
DEFAULT_LOG_LEVEL = "INFO"

DEFAULT_LEASE_TIMEOUT_SECONDS = 30
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 10
WINDOW_SEPARATOR = ".."

DEFAULT_NORMALIZATION_VERSION = "product_hunt_v1"
DEFAULT_MART_VERSION = "mart_window_v1"

NON_RETRYABLE_ERROR_TYPES = {
    "schema_drift",
    "json_schema_validation_failed",
    "parse_failure",
    "resume_state_invalid",
}

RETRY_POLICY = {
    "api_429": {"retryable": True, "default_max_retries": 5},
    "timeout": {"retryable": True, "default_max_retries": 5},
    "provider_timeout": {"retryable": True, "default_max_retries": 5},
    "network_error": {"retryable": True, "default_max_retries": 5},
    "dependency_unavailable": {"retryable": True, "default_max_retries": 3},
    "storage_write_failed": {"retryable": True, "default_max_retries": 3},
    "schema_drift": {"retryable": False, "default_max_retries": 0},
    "json_schema_validation_failed": {"retryable": False, "default_max_retries": 0},
    "parse_failure": {"retryable": False, "default_max_retries": 0},
    "resume_state_invalid": {"retryable": False, "default_max_retries": 0},
}
