from __future__ import annotations

import json
import urllib.error
import unittest
from unittest.mock import patch

from src.candidate_prescreen.relay import (
    PAYLOAD_BUILDER_VERSION,
    README_EXCERPT_MAX_CHARS,
    _build_relay_input,
    relay_preflight,
    screen_candidate,
)
from src.common.errors import ProcessingError
from src.common.request_timing import reset_request_timing_state, wait_for_request_interval


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


class CandidatePrescreenRelayUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_request_timing_state()

    def test_build_relay_input_trims_excerpt_to_normalized_excerpt_contract(self) -> None:
        noisy_excerpt = "\n".join(
            [
                "[![build](https://img.shields.io/badge/build-passing-brightgreen)](https://example.com)",
                "<div align=\"center\"><img src=\"https://example.com/logo.png\" /></div>",
                "# Product Name",
                "A concise summary for human review.",
                "```bash",
                "curl https://example.com/install.sh | bash",
                "```",
                "<p align=\"center\"><strong>Built for support teams</strong></p>",
                "https://example.com/docs",
                "Audience and workflow details that should stay.",
            ]
        )

        built = _build_relay_input(
            {
                "source": "github",
                "source_window": "2026-03-01..2026-03-08",
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": " Product Name ",
                "summary": " Human-first summary. ",
                "raw_evidence_excerpt": noisy_excerpt,
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "time_field": "pushed_at",
                "source_id": "src_github",
            }
        )

        self.assertEqual(built["title"], "Product Name")
        self.assertEqual(built["summary"], "Human-first summary.")
        self.assertNotIn("img.shields.io", built["raw_evidence_excerpt"])
        self.assertNotIn("curl https://example.com/install.sh", built["raw_evidence_excerpt"])
        self.assertNotIn("https://example.com/docs", built["raw_evidence_excerpt"])
        self.assertIn("Product Name", built["raw_evidence_excerpt"])
        self.assertIn("Built for support teams", built["raw_evidence_excerpt"])
        self.assertIn("Audience and workflow details that should stay.", built["raw_evidence_excerpt"])

    def test_build_relay_input_caps_excerpt_at_frozen_limit(self) -> None:
        long_excerpt = "Section one.\n\n" + ("A" * (README_EXCERPT_MAX_CHARS + 200))

        built = _build_relay_input(
            {
                "source": "github",
                "source_window": "2026-03-01..2026-03-08",
                "external_id": "123",
                "canonical_url": "https://github.com/example/product",
                "title": "Product Name",
                "summary": "summary",
                "raw_evidence_excerpt": long_excerpt,
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "time_field": "pushed_at",
            }
        )

        self.assertLessEqual(len(built["raw_evidence_excerpt"]), README_EXCERPT_MAX_CHARS)
        self.assertEqual(built["raw_evidence_excerpt"], "Section one.")

    def test_screen_candidate_sends_payload_builder_version_and_clean_input(self) -> None:
        candidate_input = {
            "source": "github",
            "source_id": "src_github",
            "source_window": "2026-03-01..2026-03-08",
            "time_field": "pushed_at",
            "external_id": "123",
            "canonical_url": "https://github.com/example/product",
            "title": "Product Name",
            "summary": "AI support workspace.",
            "raw_evidence_excerpt": "[![badge](https://img.shields.io/badge/x-y)](https://example.com)\n\nUseful product evidence.",
            "query_family": "ai_applications_and_products",
            "query_slice_id": "qf_agent",
            "selection_rule_version": "github_qsv1",
        }
        captured_request: dict[str, object] = {}

        def _fake_urlopen(request, timeout, context):
            captured_request["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeRelayResponse({"result": {}})

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            with patch("src.candidate_prescreen.relay.urllib.request.urlopen", side_effect=_fake_urlopen):
                result = screen_candidate(
                    candidate_input,
                    prompt_version="candidate_prescreener_v1",
                    routing_version="route_candidate_prescreener_v1",
                    relay_transport="http_json_relay",
                    relay_client_version="relay_candidate_prescreener_v1",
                    prompt_contract={"prompt_spec_ref": "10_prompt_specs/candidate_prescreener_v1.md"},
                    fixture_path=None,
                    timeout_seconds=30,
                    max_retries=0,
                )

        payload = captured_request["body"]
        self.assertEqual(payload["payload_builder_version"], PAYLOAD_BUILDER_VERSION)
        self.assertEqual(payload["input"]["source"], "github")
        self.assertEqual(payload["input"]["time_field"], "pushed_at")
        self.assertEqual(payload["input"]["raw_evidence_excerpt"], "Useful product evidence.")
        self.assertEqual(result["channel_metadata"]["request_id"], "req_test_123")

    def test_screen_candidate_supports_openai_compatible_api(self) -> None:
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
        captured_request: dict[str, object] = {}

        def _fake_urlopen(request, timeout, context):
            captured_request["url"] = request.full_url
            captured_request["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeRelayResponse({"choices": [{"message": {"content": "{}"}}]})

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://api.third-party.example/v1"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "openai_compatible"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch("src.candidate_prescreen.relay.urllib.request.urlopen", side_effect=_fake_urlopen):
                result = screen_candidate(
                    candidate_input,
                    prompt_version="candidate_prescreener_v1",
                    routing_version="route_candidate_prescreener_v1",
                    relay_transport="http_json_relay",
                    relay_client_version="relay_candidate_prescreener_v1",
                    prompt_contract={"prompt_spec_ref": "10_prompt_specs/candidate_prescreener_v1.md"},
                    fixture_path=None,
                    timeout_seconds=30,
                    max_retries=0,
                )

        payload = captured_request["body"]
        self.assertEqual(captured_request["url"], "https://api.third-party.example/v1/chat/completions")
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertIn("candidate_input", payload["messages"][1]["content"])
        self.assertEqual(result["channel_metadata"]["request_id"], "req_test_123")

    def test_screen_candidate_supports_raw_authorization_header(self) -> None:
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
        captured_request: dict[str, object] = {}

        def _fake_urlopen(request, timeout, context):
            captured_request["authorization"] = request.headers.get("Authorization")
            return _FakeRelayResponse({"choices": [{"message": {"content": "{}"}}]})

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://api.third-party.example/v1"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "openai_compatible"
            mock_from_env.return_value.auth_style = "raw"
            mock_from_env.return_value.message_content_style = "string"
            with patch("src.candidate_prescreen.relay.urllib.request.urlopen", side_effect=_fake_urlopen):
                screen_candidate(
                    candidate_input,
                    prompt_version="candidate_prescreener_v1",
                    routing_version="route_candidate_prescreener_v1",
                    relay_transport="http_json_relay",
                    relay_client_version="relay_candidate_prescreener_v1",
                    prompt_contract={"prompt_spec_ref": "10_prompt_specs/candidate_prescreener_v1.md"},
                    fixture_path=None,
                    timeout_seconds=30,
                    max_retries=0,
                )

        self.assertEqual(captured_request["authorization"], "test-token")

    def test_screen_candidate_supports_parts_list_message_content(self) -> None:
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
        captured_request: dict[str, object] = {}

        def _fake_urlopen(request, timeout, context):
            captured_request["body"] = json.loads(request.data.decode("utf-8"))
            return _FakeRelayResponse({"choices": [{"message": {"content": "{}"}}]})

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://api.third-party.example/v1"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "openai_compatible"
            mock_from_env.return_value.auth_style = "raw"
            mock_from_env.return_value.message_content_style = "parts_list"
            with patch("src.candidate_prescreen.relay.urllib.request.urlopen", side_effect=_fake_urlopen):
                screen_candidate(
                    candidate_input,
                    prompt_version="candidate_prescreener_v1",
                    routing_version="route_candidate_prescreener_v1",
                    relay_transport="http_json_relay",
                    relay_client_version="relay_candidate_prescreener_v1",
                    prompt_contract={"prompt_spec_ref": "10_prompt_specs/candidate_prescreener_v1.md"},
                    fixture_path=None,
                    timeout_seconds=30,
                    max_retries=0,
                )

        payload = captured_request["body"]
        self.assertEqual(payload["messages"][0]["content"][0]["type"], "text")
        self.assertEqual(payload["messages"][1]["content"][0]["type"], "text")

    def test_screen_candidate_waits_between_retryable_attempts(self) -> None:
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
        slept: list[float] = []

        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "relay_json"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch(
                "src.candidate_prescreen.relay.urllib.request.urlopen",
                side_effect=[
                    urllib.error.URLError("temporary relay outage"),
                    _FakeRelayResponse({"result": {}}),
                ],
            ):
                result = screen_candidate(
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
                    retry_sleep_seconds=12,
                    sleep_fn=slept.append,
                )

        self.assertEqual(slept, [12])
        self.assertEqual(result["channel_metadata"]["request_id"], "req_test_123")

    def test_wait_for_request_interval_sleeps_until_interval_boundary(self) -> None:
        slept: list[float] = []

        first_now = iter([0.0])
        second_now = iter([5.0, 60.0])

        wait_for_request_interval("candidate_prescreen_relay", 60, sleep_fn=slept.append, now_fn=lambda: next(first_now))
        waited = wait_for_request_interval("candidate_prescreen_relay", 60, sleep_fn=slept.append, now_fn=lambda: next(second_now))

        self.assertEqual(waited, 55.0)
        self.assertEqual(slept, [55.0])

    def test_relay_preflight_resolves_openai_compatible_host(self) -> None:
        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://api.third-party.example/v1"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "openai_compatible"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch("src.candidate_prescreen.relay.socket.getaddrinfo", return_value=[object()]) as getaddrinfo_mock:
                status = relay_preflight(
                    default_timeout_seconds=30,
                    default_client_version="relay_candidate_prescreener_v1",
                )

        getaddrinfo_mock.assert_called_once_with("api.third-party.example", 443, proto=6)
        self.assertEqual(status["request_url"], "https://api.third-party.example/v1/chat/completions")
        self.assertEqual(status["host"], "api.third-party.example")
        self.assertEqual(status["model"], "test-model")

    def test_relay_preflight_raises_processing_error_when_host_cannot_resolve(self) -> None:
        with patch("src.candidate_prescreen.relay.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://broken-relay.example/v1"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_prescreener_v1"
            mock_from_env.return_value.api_style = "openai_compatible"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch(
                "src.candidate_prescreen.relay.socket.getaddrinfo",
                side_effect=OSError("Name or service not known"),
            ):
                with self.assertRaises(ProcessingError) as ctx:
                    relay_preflight(
                        default_timeout_seconds=30,
                        default_client_version="relay_candidate_prescreener_v1",
                    )

        self.assertEqual(ctx.exception.error_type, "network_error")
