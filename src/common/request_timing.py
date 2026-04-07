"""Helpers for configurable request throttling and retry sleep defaults."""

from __future__ import annotations

import os
from time import monotonic, sleep
from typing import Callable, Iterable

from src.common.constants import DEFAULT_RETRY_BASE_DELAY_SECONDS
from src.common.errors import ConfigError

DEFAULT_REQUEST_INTERVAL_SECONDS = 60
DEFAULT_DISCOVERY_REQUEST_INTERVAL_SECONDS = 0

_LAST_REQUEST_AT: dict[str, float] = {}


def reset_request_timing_state() -> None:
    _LAST_REQUEST_AT.clear()


def _parse_non_negative_int(raw_value: object, *, setting_name: str) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{setting_name} must be a non-negative integer") from exc
    if value < 0:
        raise ConfigError(f"{setting_name} must be a non-negative integer")
    return value


def resolve_non_negative_seconds(
    override: int | None,
    *,
    env_names: Iterable[str],
    default: int,
    setting_name: str,
) -> int:
    if override is not None:
        return _parse_non_negative_int(override, setting_name=setting_name)
    for env_name in env_names:
        raw_value = os.environ.get(env_name)
        if raw_value:
            return _parse_non_negative_int(raw_value, setting_name=env_name)
    return default


def resolve_request_interval_seconds(override: int | None = None) -> int:
    return resolve_non_negative_seconds(
        override,
        env_names=("APO_PROVIDER_REQUEST_INTERVAL_SECONDS", "APO_LLM_RELAY_MIN_REQUEST_INTERVAL_SECONDS"),
        default=DEFAULT_REQUEST_INTERVAL_SECONDS,
        setting_name="provider_request_interval_seconds",
    )


def resolve_discovery_request_interval_seconds(override: int | None = None) -> int:
    return resolve_non_negative_seconds(
        override,
        env_names=("APO_DISCOVERY_REQUEST_INTERVAL_SECONDS", "APO_SOURCE_REQUEST_INTERVAL_SECONDS"),
        default=DEFAULT_DISCOVERY_REQUEST_INTERVAL_SECONDS,
        setting_name="discovery_request_interval_seconds",
    )


def resolve_retry_sleep_seconds(override: int | None = None) -> int:
    return resolve_non_negative_seconds(
        override,
        env_names=("APO_RETRY_SLEEP_SECONDS", "APO_FAILURE_BACKOFF_SECONDS"),
        default=DEFAULT_RETRY_BASE_DELAY_SECONDS,
        setting_name="retry_sleep_seconds",
    )


def wait_for_request_interval(
    scope: str,
    interval_seconds: int,
    *,
    sleep_fn: Callable[[float], None] = sleep,
    now_fn: Callable[[], float] = monotonic,
) -> float:
    if interval_seconds <= 0:
        _LAST_REQUEST_AT[scope] = now_fn()
        return 0.0

    current_time = now_fn()
    last_request_at = _LAST_REQUEST_AT.get(scope)
    remaining = 0.0
    if last_request_at is not None:
        remaining = max(0.0, float(interval_seconds) - (current_time - last_request_at))
    if remaining > 0:
        sleep_fn(remaining)
        current_time = now_fn()
    _LAST_REQUEST_AT[scope] = current_time
    return remaining
