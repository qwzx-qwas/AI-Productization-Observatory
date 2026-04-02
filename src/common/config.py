"""Configuration loading with predictable path precedence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from src.common.constants import (
    DEFAULT_CANDIDATE_WORKSPACE_DIR,
    DEFAULT_CONFIG_DIR,
    DEFAULT_FIXTURES_DIR,
    DEFAULT_GOLD_SET_DIR,
    DEFAULT_GOLD_SET_STAGING_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MART_OUTPUT_DIR,
    DEFAULT_RAW_STORE_DIR,
    DEFAULT_SCHEMA_DIR,
    DEFAULT_TASK_STORE_PATH,
)
from src.common.errors import ConfigError


_SENSITIVE_ENV_NAME_PARTS = ("KEY", "TOKEN", "SECRET", "CREDENTIAL", "PASSWORD")
_SECRET_LOG_PLACEHOLDER = "[REDACTED]"


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    config_dir: Path
    schema_dir: Path
    fixtures_dir: Path
    gold_set_dir: Path
    candidate_workspace_dir: Path
    gold_set_staging_dir: Path
    raw_store_dir: Path
    task_store_path: Path
    mart_output_dir: Path
    log_level: str

    @classmethod
    def from_env(cls, repo_root: Path | None = None) -> "AppConfig":
        root = (repo_root or Path.cwd()).resolve()
        return cls(
            repo_root=root,
            config_dir=cls._resolve_dir(root, "APO_CONFIG_DIR", DEFAULT_CONFIG_DIR),
            schema_dir=cls._resolve_dir(root, "APO_SCHEMA_DIR", DEFAULT_SCHEMA_DIR),
            fixtures_dir=cls._resolve_dir(root, "APO_FIXTURES_DIR", DEFAULT_FIXTURES_DIR),
            gold_set_dir=cls._resolve_dir(root, "APO_GOLD_SET_DIR", DEFAULT_GOLD_SET_DIR),
            candidate_workspace_dir=cls._resolve_dir(
                root,
                "APO_CANDIDATE_WORKSPACE_DIR",
                DEFAULT_CANDIDATE_WORKSPACE_DIR,
                must_exist=False,
            ),
            gold_set_staging_dir=cls._resolve_dir(
                root,
                "APO_GOLD_SET_STAGING_DIR",
                DEFAULT_GOLD_SET_STAGING_DIR,
            ),
            raw_store_dir=cls._resolve_dir(root, "APO_RAW_STORE_DIR", DEFAULT_RAW_STORE_DIR, must_exist=False),
            task_store_path=cls._resolve_path(root, "APO_TASK_STORE_PATH", DEFAULT_TASK_STORE_PATH),
            mart_output_dir=cls._resolve_dir(root, "APO_MART_OUTPUT_DIR", DEFAULT_MART_OUTPUT_DIR, must_exist=False),
            log_level=os.environ.get("APO_LOG_LEVEL", DEFAULT_LOG_LEVEL),
        )

    @staticmethod
    def _resolve_dir(repo_root: Path, env_name: str, default: Path, must_exist: bool = True) -> Path:
        value = Path(os.environ.get(env_name, str(default)))
        path = value if value.is_absolute() else repo_root / value
        if must_exist and not path.exists():
            raise ConfigError(f"{env_name} points to missing directory: {path}")
        return path

    @staticmethod
    def _resolve_path(repo_root: Path, env_name: str, default: Path) -> Path:
        value = Path(os.environ.get(env_name, str(default)))
        return value if value.is_absolute() else repo_root / value


def require_environment_variables(names: Iterable[str]) -> None:
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        joined = ", ".join(sorted(missing))
        raise ConfigError(f"Missing required environment variables: {joined}")


def is_sensitive_environment_variable(name: str) -> bool:
    normalized = name.upper()
    return any(part in normalized for part in _SENSITIVE_ENV_NAME_PARTS)


def require_environment_variable(name: str, *, local_env_file: str = ".env", template_file: str = ".env.example") -> str:
    value = os.environ.get(name)
    if value:
        return value

    setup_hint = f"Copy {template_file} to {local_env_file}, fill in your own local value, and export it before running."
    if is_sensitive_environment_variable(name):
        raise ConfigError(
            f"{name} is required but not set. API credentials are private and must stay in local-only {local_env_file}. "
            f"{setup_hint} Never commit real secrets to this public repository."
        )
    raise ConfigError(f"{name} is required but not set. {setup_hint}")


def redact_sensitive_value(value: str) -> str:
    if not value:
        return "<unset>"
    return _SECRET_LOG_PLACEHOLDER


def summarize_resolved_settings(settings: Mapping[str, str]) -> str:
    parts = []
    for name, value in settings.items():
        rendered_value = redact_sensitive_value(value) if is_sensitive_environment_variable(name) else value
        parts.append(f"{name}={rendered_value}")
    return ", ".join(parts)


_CONFIG_ENV_TO_FIELD = {
    "APO_CONFIG_DIR": "config_dir",
    "APO_SCHEMA_DIR": "schema_dir",
    "APO_FIXTURES_DIR": "fixtures_dir",
    "APO_GOLD_SET_DIR": "gold_set_dir",
    "APO_CANDIDATE_WORKSPACE_DIR": "candidate_workspace_dir",
    "APO_GOLD_SET_STAGING_DIR": "gold_set_staging_dir",
    "APO_RAW_STORE_DIR": "raw_store_dir",
    "APO_TASK_STORE_PATH": "task_store_path",
    "APO_MART_OUTPUT_DIR": "mart_output_dir",
    "APO_LOG_LEVEL": "log_level",
}


def resolve_required_settings(config: AppConfig, names: Iterable[str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    missing_env: list[str] = []

    for name in names:
        field_name = _CONFIG_ENV_TO_FIELD.get(name)
        if field_name is None:
            value = os.environ.get(name)
            if value:
                resolved[name] = value
            else:
                missing_env.append(name)
            continue

        value = getattr(config, field_name)
        resolved[name] = str(value)

    if missing_env:
        joined = ", ".join(sorted(missing_env))
        raise ConfigError(
            f"Missing required environment variables: {joined}. "
            "Copy .env.example to .env, fill in your local values, and export them before running."
        )

    return resolved
