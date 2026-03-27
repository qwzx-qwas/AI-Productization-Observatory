"""Shared helpers for test environment setup."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterator
from unittest.mock import patch

from src.common.config import AppConfig

REPO_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def temp_config() -> Iterator[AppConfig]:
    with TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        env = {
            "APO_RAW_STORE_DIR": str(root / "raw_store"),
            "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
            "APO_MART_OUTPUT_DIR": str(root / "marts"),
        }
        with patch.dict(os.environ, env, clear=False):
            yield AppConfig.from_env(REPO_ROOT)
