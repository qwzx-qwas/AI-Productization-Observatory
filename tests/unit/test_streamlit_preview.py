from __future__ import annotations

import sys
import tomllib
import unittest
from unittest.mock import patch

from src.common.errors import ConfigError
from src.frontend.streamlit_preview import _import_streamlit, main, render_phase2_4_streamlit_preview
from src.runtime.replay import build_default_mart
from src.service.preview_adapter import build_phase2_4_preview_model
from tests.helpers import REPO_ROOT, temp_config


class _FakeStreamlitNode:
    def __init__(self, calls: list[tuple[str, tuple[object, ...], dict[str, object]]]) -> None:
        self.calls = calls

    def __enter__(self) -> "_FakeStreamlitNode":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def __getattr__(self, name: str) -> object:
        def recorder(*args: object, **kwargs: object) -> object:
            self.calls.append((name, args, kwargs))
            if name == "columns":
                return [_FakeStreamlitNode(self.calls) for _ in range(int(args[0]))]
            if name == "tabs":
                labels = args[0] if args else []
                return [_FakeStreamlitNode(self.calls) for _ in labels]  # type: ignore[union-attr]
            return None

        return recorder


class StreamlitPreviewTests(unittest.TestCase):
    def test_streamlit_renderer_uses_preview_model_without_mutation_controls(self) -> None:
        with temp_config() as config:
            mart = build_default_mart(config)
            preview = build_phase2_4_preview_model(
                config=config,
                mart=mart,
                product_id="prod_003",
                task_status="blocked",
                request_id="streamlit_preview",
            )
            fake_streamlit = _FakeStreamlitNode([])

            render_phase2_4_streamlit_preview(preview, fake_streamlit)

            call_names = [name for name, _args, _kwargs in fake_streamlit.calls]
            self.assertIn("set_page_config", call_names)
            self.assertIn("tabs", call_names)
            self.assertIn("json", call_names)
            for mutation_control in ("button", "form", "form_submit_button", "text_input", "file_uploader"):
                self.assertNotIn(mutation_control, call_names)

            json_payloads = [args[0] for name, args, _kwargs in fake_streamlit.calls if name == "json"]
            self.assertTrue(any(isinstance(payload, dict) and "blocked_actions" in payload for payload in json_payloads))
            self.assertTrue(preview["contract_checks"]["all_passed"])
            self.assertFalse(preview["framework_policy"]["production_dashboard_framework_frozen"])
            self.assertFalse(preview["cutover_guardrails"]["runtime_cutover_executed"])
            self.assertFalse(preview["cutover_guardrails"]["production_db_readiness_claimed"])

    def test_streamlit_import_is_optional_until_preview_entrypoint_is_invoked(self) -> None:
        with patch.dict(sys.modules, {"streamlit": None}):
            with self.assertRaisesRegex(ConfigError, "optional Phase2-4 read-only preview surface"):
                _import_streamlit()

    def test_streamlit_entrypoint_reports_missing_optional_dependency_without_traceback(self) -> None:
        with patch.dict(sys.modules, {"streamlit": None}):
            with patch("sys.stderr") as stderr:
                exit_code = main([])

        self.assertEqual(exit_code, 2)
        stderr_output = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn("optional Phase2-4 read-only preview surface", stderr_output)

    def test_streamlit_entrypoint_parser_delegates_preview_only_args(self) -> None:
        with patch("src.frontend.streamlit_preview.run_phase2_4_streamlit_preview") as run_preview:
            exit_code = main(
                [
                    "--mart-path",
                    "fixtures/marts/effective_results_window.json",
                    "--product-id",
                    "prod_003",
                    "--open-review-only",
                    "--task-id",
                    "task_123",
                    "--task-status",
                    "blocked",
                    "--request-id",
                    "streamlit_cli",
                ]
            )

        self.assertEqual(exit_code, 0)
        run_preview.assert_called_once_with(
            mart_path="fixtures/marts/effective_results_window.json",
            product_id="prod_003",
            open_review_only=True,
            task_id="task_123",
            task_status="blocked",
            request_id="streamlit_cli",
        )

    def test_streamlit_dependency_is_preview_optional_extra_only(self) -> None:
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        base_dependencies = pyproject["project"]["dependencies"]
        optional_dependencies = pyproject["project"]["optional-dependencies"]

        self.assertFalse(any(dependency.startswith("streamlit") for dependency in base_dependencies))
        self.assertIn("phase2-4-preview", optional_dependencies)
        self.assertTrue(any(dependency.startswith("streamlit") for dependency in optional_dependencies["phase2-4-preview"]))


if __name__ == "__main__":
    unittest.main()
