from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.collectors.github import collect_fixture_window
from src.common.errors import ProcessingError
from tests.helpers import REPO_ROOT


class GitHubCollectorUnitTests(unittest.TestCase):
    def test_collect_fixture_window_preserves_replayable_request_params(self) -> None:
        fixture_path = REPO_ROOT / "fixtures" / "collector" / "github_qf_agent_window.json"

        result = collect_fixture_window(
            fixture_path,
            expected_window_start="2026-03-01T00:00:00Z",
            expected_window_end="2026-03-08T00:00:00Z",
            expected_query_slice_id="qf_agent",
            expected_selection_rule_version="github_qsv1",
        )

        crawl_run = result["crawl_run"]
        self.assertEqual(crawl_run["source_id"], "src_github")
        self.assertEqual(crawl_run["request_params"]["selection_rule_version"], "github_qsv1")
        self.assertEqual(crawl_run["request_params"]["query_slice_id"], "qf_agent")
        self.assertEqual(crawl_run["request_params"]["time_field"], "pushed_at")
        self.assertEqual(crawl_run["item_count"], 2)

    def test_collect_fixture_window_rejects_missing_github_request_contract_fields(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixture_path = Path(tmp_dir) / "github_bad_fixture.json"
            payload = json.loads((REPO_ROOT / "fixtures" / "collector" / "github_qf_agent_window.json").read_text(encoding="utf-8"))
            del payload["request_params"]["query_slice_id"]
            fixture_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

            with self.assertRaises(ProcessingError) as ctx:
                collect_fixture_window(fixture_path)

        self.assertEqual(ctx.exception.error_type, "parse_failure")
        self.assertIn("query_slice_id", str(ctx.exception))
