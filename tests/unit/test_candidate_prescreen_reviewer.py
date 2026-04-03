from __future__ import annotations

import io
import unittest
from pathlib import Path
from socket import timeout as SocketTimeout
from tempfile import TemporaryDirectory
from unittest.mock import patch
import urllib.error

from src.candidate_prescreen.reviewer import review_candidate_with_llm
from src.common.errors import ProcessingError
from src.common.files import dump_json


class _FakeReviewerResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.headers = {"X-Request-Id": "req_review_test_123"}

    def read(self) -> bytes:
        return io.BytesIO(str(self._payload).encode("utf-8")).getvalue()

    def __enter__(self) -> "_FakeReviewerResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _TimeoutOnReadResponse(_FakeReviewerResponse):
    def read(self) -> bytes:
        raise SocketTimeout("timed out")


class CandidatePrescreenReviewerUnitTests(unittest.TestCase):
    def _candidate_record(self) -> dict[str, object]:
        return {
            "candidate_id": "cand_test_001",
            "source": "github",
            "source_window": "2026-03-01..2026-03-08",
            "external_id": "123",
            "canonical_url": "https://github.com/example/product",
            "title": "Example Product",
            "summary": "AI support workspace for customer operations teams.",
            "raw_evidence_excerpt": "Routes and summarizes customer support tickets.",
            "query_family": "ai_applications_and_products",
            "query_slice_id": "qf_agent",
            "selection_rule_version": "github_qsv1",
            "human_review_status": "pending_first_pass",
            "llm_prescreen": {
                "status": "failed",
                "decision_snapshot": None,
                "scope_boundary_note": None,
                "reason": None,
                "review_focus_points": [],
                "uncertainty_points": [],
            },
        }

    def test_review_candidate_with_fixture_normalizes_allowed_statuses(self) -> None:
        candidate_record = self._candidate_record()
        with TemporaryDirectory() as tmp_dir:
            fixture_path = Path(tmp_dir) / "review_fixture.json"
            dump_json(
                fixture_path,
                {
                    "responses": {
                        "cand_test_001": {
                            "suggested_review_status": "approved",
                            "rationale": "Clear end-user support workflow evidence is present.",
                            "evidence_sufficiency": "strong",
                            "boundary_notes": ["Internal-tooling boundary is not the primary signal here."],
                        }
                    }
                },
            )

            decision = review_candidate_with_llm(
                candidate_record,
                fixture_path=fixture_path,
                timeout_seconds=30,
                max_retries=0,
            )

            self.assertEqual(decision.suggested_review_status, "approved_for_staging")
            self.assertEqual(decision.evidence_sufficiency, "sufficient")
            self.assertEqual(decision.boundary_notes, ["Internal-tooling boundary is not the primary signal here."])
            self.assertIsNone(decision.channel_metadata["request_id"])

    def test_review_candidate_http_502_maps_to_dependency_unavailable(self) -> None:
        candidate_record = self._candidate_record()

        with patch("src.candidate_prescreen.reviewer.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_first_pass_reviewer_v1"
            mock_from_env.return_value.api_style = "relay_json"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch(
                "src.candidate_prescreen.relay.urllib.request.urlopen",
                side_effect=urllib.error.HTTPError(
                    url="https://relay.example.test",
                    code=502,
                    msg="Bad Gateway",
                    hdrs={},
                    fp=io.BytesIO(b"bad gateway"),
                ),
            ):
                with self.assertRaises(ProcessingError) as ctx:
                    review_candidate_with_llm(
                        candidate_record,
                        fixture_path=None,
                        timeout_seconds=30,
                        max_retries=0,
                    )

        self.assertEqual(ctx.exception.error_type, "dependency_unavailable")
        self.assertIn("HTTP 502", str(ctx.exception))
        self.assertIn("upstream unavailable", str(ctx.exception))

    def test_review_candidate_timeout_before_response_headers_maps_to_timeout(self) -> None:
        candidate_record = self._candidate_record()

        with patch("src.candidate_prescreen.reviewer.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_first_pass_reviewer_v1"
            mock_from_env.return_value.api_style = "relay_json"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch("src.candidate_prescreen.relay.urllib.request.urlopen", side_effect=SocketTimeout("timed out")):
                with self.assertRaises(ProcessingError) as ctx:
                    review_candidate_with_llm(
                        candidate_record,
                        fixture_path=None,
                        timeout_seconds=30,
                        max_retries=0,
                    )

        self.assertEqual(ctx.exception.error_type, "timeout")
        self.assertIn("before receiving response headers", str(ctx.exception))

    def test_review_candidate_read_stall_maps_to_provider_timeout(self) -> None:
        candidate_record = self._candidate_record()

        with patch("src.candidate_prescreen.reviewer.RelayConfig.from_env") as mock_from_env:
            mock_from_env.return_value.base_url = "https://relay.example.test"
            mock_from_env.return_value.token = "test-token"
            mock_from_env.return_value.model = "test-model"
            mock_from_env.return_value.timeout_seconds = 30
            mock_from_env.return_value.client_version = "relay_candidate_first_pass_reviewer_v1"
            mock_from_env.return_value.api_style = "relay_json"
            mock_from_env.return_value.auth_style = "bearer"
            mock_from_env.return_value.message_content_style = "string"
            with patch(
                "src.candidate_prescreen.relay.urllib.request.urlopen",
                return_value=_TimeoutOnReadResponse({"result": {}}),
            ):
                with self.assertRaises(ProcessingError) as ctx:
                    review_candidate_with_llm(
                        candidate_record,
                        fixture_path=None,
                        timeout_seconds=30,
                        max_retries=0,
                    )

        self.assertEqual(ctx.exception.error_type, "provider_timeout")
        self.assertIn("while reading response body", str(ctx.exception))
