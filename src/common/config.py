"""Configuration loading with predictable path precedence."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.common.constants import (
    DEFAULT_CONFIG_DIR,
    DEFAULT_FIXTURES_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MART_OUTPUT_DIR,
    DEFAULT_RAW_STORE_DIR,
    DEFAULT_SCHEMA_DIR,
    DEFAULT_TASK_STORE_PATH,
)
from src.common.errors import ConfigError


@dataclass(frozen=True)
class AppConfig:
    repo_root: Path
    config_dir: Path
    schema_dir: Path
    fixtures_dir: Path
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
