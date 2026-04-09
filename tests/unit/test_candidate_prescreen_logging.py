from __future__ import annotations

import io
import json
import logging
import shutil
import unittest
import urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.config import load_candidate_prescreen_config
from src.candidate_prescreen.discovery import discover_candidates
from src.candidate_prescreen.fill_controller import fill_gold_set_staging_until_complete
from src.candidate_prescreen.relay import screen_candidate
from src.common.logging_utils import JsonFormatter
from tests.helpers import REPO_ROOT, temp_config


class _FakeRelayResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = {"X-Request-Id": "req_test_123"}

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeRelayResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _StructuredLogCapture:
    def __init__(self) -> None:
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(JsonFormatter())
        self.root = logging.getLogger()
        self.previous_handlers = list(self.root.handlers)
        self.previous_level = self.root.level

    def __enter__(self) -> "_StructuredLogCapture":
        self.root.handlers = [self.handler]
        self.root.setLevel(logging.INFO)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.root.handlers = self.previous_handlers
        self.root.setLevel(self.previous_level)

    def payloads(self) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in self.stream.getvalue().splitlines()
            if line.strip()
        ]


class CandidatePrescreenLoggingUnitTests(unittest.TestCase):
    def test_discovery_logs_source_and_run_context_without_meaningless_nulls(self) -> None:
        workflow_config = load_candidate_prescreen_config(REPO_ROOT / "configs")
        with _StructuredLogCapture() as capture:
            discover_candidates(
                workflow_config,
                source_code="github",
                window="2026-03-01..2026-03-08",
                query_slice_id="qf_agent",
                limit=1,
                fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                run_id="fill_run_test",
            )

        candidate_gate_entry = next(payload for payload in capture.payloads() if payload.get("event") == "candidate_gate")
        self.assertEqual(candidate_gate_entry["source_id"], "src_github")
        self.assertEqual(candidate_gate_entry["run_id"], "fill_run_test")
        self.assertNotIn("error_type", candidate_gate_entry)
        self.assertNotIn("retry_count", candidate_gate_entry)

    def test_relay_retry_log_includes_source_and_run_context(self) -> None:
        candidate_input = {
            "source": "github",
            "source_id": "src_github",
            "source_window": "2026-03-01..2026-03-08",
            "time_field": "pushed_at",
            "external_id": "123",
            "canonical_url": "https://github.com/example/product",
            "title": "Product Name",
            "summary": "AI support workspace.",
            "raw_evidence_excerpt": "Useful product evidence.",
            "query_family": "ai_applications_and_products",
            "query_slice_id": "qf_agent",
            "selection_rule_version": "github_qsv1",
        }

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "relay_json"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with _StructuredLogCapture() as capture, patch(
                "src.candidate_prescreen.relay.urllib.request.urlopen",
                side_effect=[
                    urllib.error.URLError("temporary relay outage"),
                    _FakeRelayResponse({"result": {}}),
                ],
            ):
                screen_candidate(
                    candidate_input,
                    prompt_version="candidate_prescreener_v1",
                    routing_version="route_candidate_prescreener_v1",
                    relay_transport="http_json_relay",
                    relay_client_version="relay_candidate_prescreener_v1",
                    prompt_contract={"prompt_spec_ref": "10_prompt_specs/candidate_prescreener_v1.md"},
                    fixture_path=None,
                    timeout_seconds=30,
                    max_retries=1,
                    request_interval_seconds=0,
                    retry_sleep_seconds=1,
                    sleep_fn=lambda _: None,
                    run_id="fill_run_test",
                )

        retry_entry = next(payload for payload in capture.payloads() if payload.get("wait_kind") == "retry_backoff")
        self.assertEqual(retry_entry["source_id"], "src_github")
        self.assertEqual(retry_entry["run_id"], "fill_run_test")
        self.assertEqual(retry_entry["error_type"], "network_error")
        self.assertNotIn("retry_count", retry_entry)

    def test_fill_logs_include_run_and_source_without_null_error_fields(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                complete_progress = {
                    "total_filled": 300,
                    "total_slots": 300,
                    "total_empty": 0,
                    "is_complete": True,
                    "next_open_slot": None,
                    "documents": [],
                }
                with _StructuredLogCapture() as capture, patch(
                    "src.candidate_prescreen.fill_controller.validate_staging_workspace",
                    return_value=complete_progress,
                ):
                    fill_gold_set_staging_until_complete(
                        config,
                        source_code="github",
                        initial_window="2026-03-29..2026-04-02",
                        query_slice_id="qf_agent",
                    )

        initialize_entry = next(payload for payload in capture.payloads() if payload.get("event") == "initialize")
        self.assertEqual(initialize_entry["source_id"], "src_github")
        self.assertTrue(str(initialize_entry["run_id"]).startswith("fill_run_"))
        self.assertNotIn("error_type", initialize_entry)
        self.assertNotIn("retry_count", initialize_entry)
