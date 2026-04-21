from __future__ import annotations

import json
import os
import shutil
import urllib.parse
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.candidate_prescreen.fill_controller import LiveDiscoveryCursor, fill_gold_set_staging_until_complete, run_one_fill_iteration
from src.candidate_prescreen.workflow import (
    handoff_candidates_to_staging,
    run_candidate_prescreen,
    validate_candidate_workspace,
)
from src.collectors.github import collect_fixture_window as collect_github_fixture_window
from src.common.errors import ContractValidationError, ProcessingError
from src.common.files import dump_yaml, load_yaml, utc_now_iso
from src.runtime.raw_store.file_store import FileRawStore
from src.runtime.replay import replay_source_window
from src.runtime.tasks import FileTaskStore
from src.cli import validate_gold_set
from tests.helpers import REPO_ROOT, temp_config


def _prefill_remaining_slots(staging_dir: Path, *, keep_empty_slots: int) -> None:
    template_sample = None
    template_candidate_ref = None
    template_source_ref = None
    empty_counter = 0
    synthetic_counter = 0
    for staging_path in sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml")):
        payload = load_yaml(staging_path)
        samples = payload["samples"]
        for sample in samples:
            if sample.get("sample_id") and template_sample is None:
                template_sample = dict(sample)
                template_candidate_ref = dict(sample["candidate_prescreen_ref"])
                template_source_ref = dict(sample["source_record_refs"][0])
            if sample.get("sample_id"):
                continue
            empty_counter += 1
            if empty_counter <= keep_empty_slots:
                continue
            synthetic_counter += 1
            slot_index = sample["slot_index"]
            sample_slot_id = sample["sample_slot_id"]
            sample.update(dict(template_sample))
            sample["slot_index"] = slot_index
            sample["sample_slot_id"] = sample_slot_id
            synthetic_sample_id = f"prefill_candidate_{synthetic_counter:03d}"
            sample["sample_id"] = synthetic_sample_id
            sample["candidate_prescreen_ref"] = dict(template_candidate_ref)
            sample["candidate_prescreen_ref"]["candidate_id"] = synthetic_sample_id
            sample["source_record_refs"] = [dict(template_source_ref)]
            sample["source_record_refs"][0]["candidate_id"] = synthetic_sample_id
            sample["source_record_refs"][0]["external_id"] = f"prefill_external_{synthetic_counter:03d}"
            sample["source_record_refs"][0]["canonical_url"] = f"https://example.com/prefill/{synthetic_counter:03d}"
        dump_yaml(staging_path, payload)


def _prepare_stub_gold_set_dir(target: Path) -> Path:
    gold_set_dir = target / "gold_set"
    shutil.copytree(REPO_ROOT / "gold_set", gold_set_dir)
    readme_path = gold_set_dir / "README.md"
    content = readme_path.read_text(encoding="utf-8").replace("status = implemented", "status = stub")
    readme_path.write_text(content, encoding="utf-8")
    for entry in (gold_set_dir / "gold_set_300").iterdir():
        if entry.is_dir():
            shutil.rmtree(entry)
    return gold_set_dir


def _github_live_repo_item(
    *,
    repo_id: int,
    name: str,
    full_name: str,
    pushed_at: str,
    description: str = "AI repository used for live collector integration testing.",
) -> dict[str, object]:
    return {
        "id": repo_id,
        "full_name": full_name,
        "name": name,
        "html_url": f"https://github.com/{full_name}",
        "description": description,
        "homepage": f"https://example.com/{name}",
        "owner": {"login": full_name.split("/", 1)[0]},
        "topics": ["agent", "automation"],
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 7,
        "watchers_count": 42,
        "pushed_at": pushed_at,
        "archived": False,
    }


class FixturePipelineIntegrationTests(unittest.TestCase):
    def test_replay_builds_raw_records_and_source_items(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )

            self.assertEqual(len(result["raw_records"]), 2)
            self.assertEqual(len(result["source_items"]), 2)

            first_raw = result["raw_records"][0]
            raw_payload_path = config.raw_store_dir / first_raw["raw_payload_ref"]
            self.assertTrue(raw_payload_path.exists())

            first_item = result["source_items"][0]
            self.assertEqual(first_item["source_id"], "src_product_hunt")
            self.assertEqual(first_item["external_id"], "ph_1001")
            self.assertEqual(first_item["title"], "Desk Research Copilot")
            self.assertEqual(first_item["raw_id"], first_raw["raw_id"])

    def test_expected_fixture_shape_matches_normalized_output(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            expected_path = config.fixtures_dir / "normalizer" / "product_hunt_expected_source_item.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            actual = result["source_items"][0]

            self.assertEqual(actual["source_id"], expected["source_id"])
            self.assertEqual(actual["title"], expected["title"])
            self.assertEqual(actual["canonical_url"], expected["canonical_url"])
            self.assertEqual(actual["current_metrics_json"], expected["current_metrics_json"])

    def test_expected_fixture_bundle_matches_normalized_outputs(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            expected_path = config.fixtures_dir / "normalizer" / "product_hunt_expected_source_items.json"
            expected_items = json.loads(expected_path.read_text(encoding="utf-8"))
            actual_items = {item["external_id"]: item for item in result["source_items"]}

            self.assertEqual({item["external_id"] for item in expected_items}, set(actual_items))
            for expected in expected_items:
                actual = actual_items[expected["external_id"]]
                self.assertEqual(actual["source_id"], expected["source_id"])
                self.assertEqual(actual["title"], expected["title"])
                self.assertEqual(actual["canonical_url"], expected["canonical_url"])
                self.assertEqual(actual["current_metrics_json"], expected["current_metrics_json"])
                self.assertEqual(actual["linked_homepage_url"], expected["linked_homepage_url"])

    def test_raw_store_dedupes_duplicate_payloads_by_source_external_hash(self) -> None:
        with temp_config() as config:
            collector_fixture = json.loads((config.fixtures_dir / "collector" / "product_hunt_window.json").read_text(encoding="utf-8"))
            crawl_run = {
                "crawl_run_id": "crawl-run-1",
                "source_id": collector_fixture["source_id"],
                "window_start": collector_fixture["window_start"],
                "watermark_before": collector_fixture["watermark_before"],
                "request_params": collector_fixture["request_params"],
                "collected_at": "2026-03-08T00:00:00Z",
            }
            duplicate_item = collector_fixture["items"][0]

            raw_store = FileRawStore(config.raw_store_dir)
            records = raw_store.store_items(crawl_run, [duplicate_item, duplicate_item])

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["fetched_at"], "2026-03-08T00:00:00Z")
            self.assertIn("window_start=2026-03-01", records[0]["raw_payload_ref"])

    def test_github_collector_fixture_builds_replayable_raw_records(self) -> None:
        with temp_config() as config:
            collector_output = collect_github_fixture_window(
                config.fixtures_dir / "collector" / "github_qf_agent_window.json",
                expected_window_start="2026-03-01T00:00:00Z",
                expected_window_end="2026-03-08T00:00:00Z",
                expected_query_slice_id="qf_agent",
                expected_selection_rule_version="github_qsv1",
            )

            raw_store = FileRawStore(config.raw_store_dir)
            records = raw_store.store_items(collector_output["crawl_run"], collector_output["items"])

            self.assertEqual(len(records), 2)
            self.assertEqual(records[0]["source_id"], "src_github")
            self.assertEqual(records[0]["request_params"]["selection_rule_version"], "github_qsv1")
            self.assertEqual(records[0]["request_params"]["query_slice_id"], "qf_agent")
            self.assertEqual(records[0]["request_params"]["page_or_cursor_start"], 1)
            self.assertEqual(records[0]["watermark_before"]["time_field"], "pushed_at")

    def test_github_replay_builds_source_items_with_raw_traceability(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="github",
                window="2026-03-01..2026-03-08",
                config=config,
            )

            self.assertEqual(len(result["raw_records"]), 2)
            self.assertEqual(len(result["source_items"]), 2)
            self.assertEqual(result["crawl_run"]["watermark_after"]["time_field"], "pushed_at")
            self.assertEqual(result["crawl_run"]["watermark_after"]["external_id"], "987654322")

            first_raw = result["raw_records"][0]
            first_item = result["source_items"][0]
            self.assertEqual(first_raw["fetch_url"], "https://github.com/acme/support-agent-workbench")
            self.assertEqual(first_item["source_id"], "src_github")
            self.assertEqual(first_item["external_id"], "987654321")
            self.assertEqual(first_item["title"], "support-agent-workbench")
            self.assertEqual(first_item["raw_id"], first_raw["raw_id"])
            self.assertEqual(first_item["current_metrics_json"]["star_count"], 144)
            self.assertEqual(first_item["author_handle"], "acme")

    def test_github_expected_fixture_bundle_matches_normalized_outputs(self) -> None:
        with temp_config() as config:
            result = replay_source_window(
                source_code="github",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            expected_path = config.fixtures_dir / "normalizer" / "github_expected_source_items.json"
            expected_items = json.loads(expected_path.read_text(encoding="utf-8"))
            actual_items = {item["external_id"]: item for item in result["source_items"]}

            self.assertEqual({item["external_id"] for item in expected_items}, set(actual_items))
            for expected in expected_items:
                actual = actual_items[expected["external_id"]]
                self.assertEqual(actual["source_id"], expected["source_id"])
                self.assertEqual(actual["title"], expected["title"])
                self.assertEqual(actual["canonical_url"], expected["canonical_url"])
                self.assertEqual(actual["linked_homepage_url"], expected["linked_homepage_url"])
                self.assertEqual(actual["current_metrics_json"], expected["current_metrics_json"])
                self.assertEqual(actual["topics"], expected["topics"])
                self.assertEqual(actual["item_status"], expected["item_status"])

    def test_github_live_replay_builds_raw_records_and_source_items(self) -> None:
        search_requests: list[str] = []
        live_items = [
            _github_live_repo_item(
                repo_id=987654321,
                name="support-agent-workbench",
                full_name="acme/support-agent-workbench",
                pushed_at="2026-03-05T12:34:56Z",
                description="AI assistant workspace for support teams that triages inbox tickets and drafts replies.",
            ),
            _github_live_repo_item(
                repo_id=987654322,
                name="sales-agent-console",
                full_name="acme/sales-agent-console",
                pushed_at="2026-03-06T09:20:11Z",
                description="Copilot console for pipeline follow-up, call prep, and CRM note generation.",
            ),
        ]
        readmes = {
            "acme/support-agent-workbench": "# Support Agent Workbench\n\nREADME for live replay validation.",
            "acme/sales-agent-console": "# Sales Agent Console\n\nREADME for live replay validation.",
        }

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del headers, timeout_seconds, request_interval_seconds, sleep_fn
            search_requests.append(url)
            return {"total_count": 2, "incomplete_results": False, "items": live_items}

        with temp_config() as config:
            with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                    with patch("src.collectors.github._read_github_readme", side_effect=lambda full_name, *_args: readmes[full_name]):
                        result = replay_source_window(
                            source_code="github",
                            window="2026-03-01..2026-03-08",
                            config=config,
                            use_live=True,
                            query_slice_id="qf_agent",
                        )

            self.assertEqual(len(result["raw_records"]), 2)
            self.assertEqual(len(result["source_items"]), 2)
            self.assertEqual(result["crawl_run"]["request_params"]["selection_rule_version"], "github_qsv1")
            self.assertEqual(result["crawl_run"]["request_params"]["query_slice_id"], "qf_agent")
            self.assertEqual(result["crawl_run"]["watermark_before"]["pushed_at"], "2026-03-01T00:00:00Z")
            self.assertEqual(result["crawl_run"]["watermark_after"]["external_id"], "987654322")

            parsed = urllib.parse.urlparse(search_requests[0])
            query_text = urllib.parse.parse_qs(parsed.query)["q"][0]
            self.assertIn("pushed:2026-03-01..2026-03-08", query_text)

            task = FileTaskStore(config.task_store_path).all_tasks()[-1]
            self.assertEqual(task["payload_json"]["request_params"]["query_slice_id"], "qf_agent")
            self.assertEqual(task["payload_json"]["watermark_after"]["external_id"], "987654322")

    def test_github_live_same_window_rerun_reuses_existing_raw_records(self) -> None:
        live_items = [
            _github_live_repo_item(
                repo_id=987654321,
                name="support-agent-workbench",
                full_name="acme/support-agent-workbench",
                pushed_at="2026-03-05T12:34:56Z",
            ),
            _github_live_repo_item(
                repo_id=987654322,
                name="sales-agent-console",
                full_name="acme/sales-agent-console",
                pushed_at="2026-03-06T09:20:11Z",
            ),
        ]

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del url, headers, timeout_seconds, request_interval_seconds, sleep_fn
            return {"total_count": 2, "incomplete_results": False, "items": live_items}

        with temp_config() as config:
            with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                    with patch("src.collectors.github._read_github_readme", return_value=""):
                        first = replay_source_window(
                            source_code="github",
                            window="2026-03-01..2026-03-08",
                            config=config,
                            use_live=True,
                            query_slice_id="qf_agent",
                        )
                        second = replay_source_window(
                            source_code="github",
                            window="2026-03-01..2026-03-08",
                            config=config,
                            use_live=True,
                            query_slice_id="qf_agent",
                        )

            self.assertEqual(
                [record["raw_id"] for record in first["raw_records"]],
                [record["raw_id"] for record in second["raw_records"]],
            )

            raw_index = json.loads((config.raw_store_dir / "raw_records.json").read_text(encoding="utf-8"))
            self.assertEqual(len(raw_index), 2)

    def test_github_live_replay_filters_items_that_drift_outside_leaf_window(self) -> None:
        live_items = [
            _github_live_repo_item(
                repo_id=987654321,
                name="support-agent-workbench",
                full_name="acme/support-agent-workbench",
                pushed_at="2026-03-05T12:34:56Z",
            ),
            _github_live_repo_item(
                repo_id=987654399,
                name="late-workflow-repo",
                full_name="acme/late-workflow-repo",
                pushed_at="2026-03-09T08:58:59Z",
            ),
        ]

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del url, headers, timeout_seconds, request_interval_seconds, sleep_fn
            return {"total_count": 2, "incomplete_results": False, "items": live_items}

        with temp_config() as config:
            with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                    with patch("src.collectors.github._read_github_readme", return_value=""):
                        result = replay_source_window(
                            source_code="github",
                            window="2026-03-05..2026-03-05",
                            config=config,
                            use_live=True,
                            query_slice_id="qf_ai_workflow",
                        )

            self.assertEqual(len(result["raw_records"]), 1)
            self.assertEqual(len(result["source_items"]), 1)
            self.assertEqual(result["raw_records"][0]["external_id"], "987654321")
            self.assertEqual(result["crawl_run"]["watermark_after"]["external_id"], "987654321")

            raw_index = json.loads((config.raw_store_dir / "raw_records.json").read_text(encoding="utf-8"))
            self.assertEqual(len(raw_index), 1)

    def test_github_live_retryable_failure_persists_partial_raw_and_resumes_from_checkpoint(self) -> None:
        page_one_items = [
            _github_live_repo_item(
                repo_id=100000 + index,
                name=f"agent-app-{index:03d}",
                full_name=f"acme/agent-app-{index:03d}",
                pushed_at=f"2026-03-{5 + ((index // 24) % 4):02d}T{index % 24:02d}:00:00Z",
            )
            for index in range(100)
        ]
        page_two_item = _github_live_repo_item(
            repo_id=100100,
            name="agent-app-100",
            full_name="acme/agent-app-100",
            pushed_at="2026-03-08T23:59:59Z",
        )
        page_two_failed = {"value": False}

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del headers, timeout_seconds, request_interval_seconds, sleep_fn
            parsed = urllib.parse.urlparse(url)
            page = int(urllib.parse.parse_qs(parsed.query)["page"][0])
            if page == 1:
                return {"total_count": 101, "incomplete_results": False, "items": page_one_items}
            if not page_two_failed["value"]:
                page_two_failed["value"] = True
                raise ProcessingError("network_error", "simulated page 2 timeout")
            return {"total_count": 101, "incomplete_results": False, "items": [page_two_item]}

        with temp_config() as config:
            with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                    with patch("src.collectors.github._read_github_readme", return_value=""):
                        with self.assertRaises(ProcessingError) as first_error:
                            replay_source_window(
                                source_code="github",
                                window="2026-03-01..2026-03-08",
                                config=config,
                                use_live=True,
                                query_slice_id="qf_agent",
                            )

                        self.assertEqual(first_error.exception.error_type, "network_error")
                        store = FileTaskStore(config.task_store_path)
                        failed_task = store.all_tasks()[-1]
                        self.assertEqual(failed_task["status"], "failed_retryable")
                        self.assertEqual(failed_task["payload_json"]["resume_state"]["pending_windows"][0]["page"], 2)
                        self.assertEqual(failed_task["payload_json"]["durable_logical_watermark"]["external_id"], "100095")

                        raw_index_after_failure = json.loads((config.raw_store_dir / "raw_records.json").read_text(encoding="utf-8"))
                        self.assertEqual(len(raw_index_after_failure), 100)

                        resumed = replay_source_window(
                            source_code="github",
                            window="2026-03-01..2026-03-08",
                            config=config,
                            use_live=True,
                            query_slice_id="qf_agent",
                        )

            self.assertEqual(resumed["crawl_run"]["request_params"]["page_or_cursor_start"], 2)
            self.assertEqual(resumed["crawl_run"]["watermark_after"]["external_id"], "100100")

            tasks = FileTaskStore(config.task_store_path).all_tasks()
            self.assertEqual(tasks[-1]["payload_json"]["resume_from_task_id"], failed_task["task_id"])
            raw_index_after_resume = json.loads((config.raw_store_dir / "raw_records.json").read_text(encoding="utf-8"))
            self.assertEqual(len(raw_index_after_resume), 101)

    def test_github_live_failpoint_persists_partial_raw_and_resume_state(self) -> None:
        page_one_items = [
            _github_live_repo_item(
                repo_id=100000 + index,
                name=f"workflow-app-{index:03d}",
                full_name=f"acme/workflow-app-{index:03d}",
                pushed_at=f"2026-03-05T{index % 24:02d}:00:00Z",
            )
            for index in range(100)
        ]

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del headers, timeout_seconds, request_interval_seconds, sleep_fn
            parsed = urllib.parse.urlparse(url)
            page = int(urllib.parse.parse_qs(parsed.query)["page"][0])
            if page == 1:
                return {"total_count": 101, "incomplete_results": False, "items": page_one_items}
            self.fail("configured page-2 failpoint should prevent the second search request")

        with temp_config() as config:
            with patch.dict(os.environ, {"APO_GITHUB_LIVE_FAIL_ON_PAGE": "2"}, clear=False):
                with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                    with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                        with patch("src.collectors.github._read_github_readme", return_value=""):
                            with self.assertRaises(ProcessingError) as ctx:
                                replay_source_window(
                                    source_code="github",
                                    window="2026-03-05..2026-03-05",
                                    config=config,
                                    use_live=True,
                                    query_slice_id="qf_ai_workflow",
                                )

            self.assertEqual(ctx.exception.error_type, "network_error")
            failed_task = FileTaskStore(config.task_store_path).all_tasks()[-1]
            self.assertEqual(failed_task["status"], "failed_retryable")
            self.assertEqual(failed_task["payload_json"]["resume_state"]["pending_windows"][0]["page"], 2)
            self.assertEqual(failed_task["payload_json"]["durable_logical_watermark"]["external_id"], "100095")

            raw_index_after_failure = json.loads((config.raw_store_dir / "raw_records.json").read_text(encoding="utf-8"))
            self.assertEqual(len(raw_index_after_failure), 100)

    def test_github_live_marks_terminal_failure_on_invalid_normalized_output(self) -> None:
        invalid_item = _github_live_repo_item(
            repo_id=222001,
            name="invalid-agent-app",
            full_name="acme/invalid-agent-app",
            pushed_at="2026-03-05T12:34:56Z",
        )
        invalid_item["pushed_at"] = ["not", "a", "timestamp"]

        def fake_json_request(url: str, *, headers: dict[str, str], timeout_seconds: int, request_interval_seconds: int, sleep_fn= None) -> dict[str, object]:
            del url, headers, timeout_seconds, request_interval_seconds, sleep_fn
            return {"total_count": 1, "incomplete_results": False, "items": [invalid_item]}

        with temp_config() as config:
            with patch("src.collectors.github.require_environment_variable", return_value="test-token"):
                with patch("src.collectors.github._json_request", side_effect=fake_json_request):
                    with patch("src.collectors.github._read_github_readme", return_value=""):
                        with self.assertRaises(ProcessingError) as ctx:
                            replay_source_window(
                                source_code="github",
                                window="2026-03-01..2026-03-08",
                                config=config,
                                use_live=True,
                                query_slice_id="qf_agent",
                            )

            self.assertEqual(ctx.exception.error_type, "json_schema_validation_failed")
            task = FileTaskStore(config.task_store_path).all_tasks()[-1]
            self.assertEqual(task["status"], "failed_terminal")
            self.assertEqual(task["last_error_type"], "json_schema_validation_failed")
            self.assertEqual(task["payload_json"]["request_params"]["query_slice_id"], "qf_agent")

    def test_replay_marks_terminal_failure_on_invalid_normalized_output(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "collector").mkdir(parents=True, exist_ok=True)

            collector_fixture = json.loads((REPO_ROOT / "fixtures" / "collector" / "product_hunt_window.json").read_text(encoding="utf-8"))
            collector_fixture["items"][0]["name"] = ["not", "a", "string"]
            (fixtures_dir / "collector" / "product_hunt_window.json").write_text(
                json.dumps(collector_fixture, indent=2, ensure_ascii=True) + "\n",
                encoding="utf-8",
            )

            with temp_config(fixtures_dir=fixtures_dir) as config:
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

                self.assertEqual(ctx.exception.error_type, "json_schema_validation_failed")
                store = FileTaskStore(config.task_store_path)
                task = store.all_tasks()[-1]
                self.assertEqual(task["status"], "failed_terminal")
                self.assertEqual(task["last_error_type"], "json_schema_validation_failed")

    def test_replay_marks_terminal_failure_on_unparseable_fixture(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            fixtures_dir = Path(tmp_dir)
            (fixtures_dir / "collector").mkdir(parents=True, exist_ok=True)
            (fixtures_dir / "collector" / "product_hunt_window.json").write_text("{ invalid json\n", encoding="utf-8")

            with temp_config(fixtures_dir=fixtures_dir) as config:
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

                self.assertEqual(ctx.exception.error_type, "parse_failure")
                store = FileTaskStore(config.task_store_path)
                task = store.all_tasks()[-1]
                self.assertEqual(task["status"], "failed_terminal")
                self.assertEqual(task["last_error_type"], "parse_failure")

    def test_replay_marks_retryable_failure_on_raw_store_write_error(self) -> None:
        with temp_config() as config:
            with patch.object(
                FileRawStore,
                "store_items",
                side_effect=ProcessingError("storage_write_failed", "simulated raw store outage"),
            ):
                with self.assertRaises(ProcessingError) as ctx:
                    replay_source_window(
                        source_code="product_hunt",
                        window="2026-03-01..2026-03-08",
                        config=config,
                    )

            self.assertEqual(ctx.exception.error_type, "storage_write_failed")
            store = FileTaskStore(config.task_store_path)
            task = store.all_tasks()[-1]
            self.assertEqual(task["status"], "failed_retryable")
            self.assertEqual(task["last_error_type"], "storage_write_failed")

    def test_same_window_rerun_reuses_existing_raw_records(self) -> None:
        with temp_config() as config:
            first = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )
            second = replay_source_window(
                source_code="product_hunt",
                window="2026-03-01..2026-03-08",
                config=config,
            )

            self.assertEqual(
                [record["raw_id"] for record in first["raw_records"]],
                [record["raw_id"] for record in second["raw_records"]],
            )

            raw_index_path = config.raw_store_dir / "raw_records.json"
            raw_index = json.loads(raw_index_path.read_text(encoding="utf-8"))
            self.assertEqual(len(raw_index), 2)

    def test_candidate_prescreen_writes_workspace_documents_from_fixtures(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            gold_set_dir = _prepare_stub_gold_set_dir(root)
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(
                candidate_workspace_dir=candidate_workspace,
                gold_set_staging_dir=staging_dir,
                gold_set_dir=gold_set_dir,
            ) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=2,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                self.assertEqual(len(paths), 2)
                self.assertEqual(validate_candidate_workspace(config), 2)

                first_record = load_yaml(paths[0])
                self.assertEqual(first_record["human_review_status"], "pending_first_pass")
                self.assertIsNone(first_record["human_review_note_template_key"])
                self.assertEqual(first_record["llm_prescreen"]["status"], "succeeded")
                self.assertEqual(first_record["llm_prescreen"]["channel_metadata"]["prompt_version"], "candidate_prescreener_v1")
                self.assertEqual(first_record["llm_prescreen"]["taxonomy_hints"]["primary_persona_code"], "support_agent")
                self.assertEqual(first_record["llm_prescreen"]["persona_candidates"][0]["persona_code"], "support_agent")
                self.assertEqual(first_record["llm_prescreen"]["taxonomy_hints"]["main_category_candidate"]["category_code"], "JTBD_SALES_SUPPORT")
                self.assertEqual(first_record["llm_prescreen"]["handoff_readiness_hint"]["suggested_action"], "candidate_pool")
                self.assertEqual(first_record["llm_prescreen"]["evidence_anchors"][0]["anchor_rank"], 1)
                self.assertTrue(paths[0].is_relative_to(candidate_workspace))

    def test_candidate_handoff_to_staging_keeps_gold_set_stub_boundary(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            gold_set_dir = _prepare_stub_gold_set_dir(root)
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(
                candidate_workspace_dir=candidate_workspace,
                gold_set_staging_dir=staging_dir,
                gold_set_dir=gold_set_dir,
            ) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="product_hunt",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="ph_published_launches",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "product_hunt_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                record = load_yaml(paths[0])
                record["human_review_status"] = "approved_for_staging"
                record["human_review_note_template_key"] = "approved"
                record["human_review_notes"] = "clear end-user product signal; evidence sufficient for staging; Product Hunt launch copy is specific enough for staging."
                record["human_reviewed_at"] = utc_now_iso()
                record["whitelist_reason"] = "manual_first_pass_whitelist"
                dump_yaml(paths[0], record)

                results = handoff_candidates_to_staging(config, candidate_ids=[record["candidate_id"]])
                self.assertEqual(len(results), 1)

                staging_payload = load_yaml(Path(results[0][1]))
                samples = staging_payload["samples"]
                matching = [sample for sample in samples if sample["sample_id"] == record["candidate_id"]]
                self.assertEqual(len(matching), 1)
                staged = matching[0]
                self.assertEqual(staged["current_state"], "candidate_approved_for_annotation")
                self.assertEqual(staged["training_pool_source"], "candidate_pool")
                self.assertEqual(staged["whitelist_reason"], "manual_first_pass_whitelist")
                self.assertEqual(staged["review_closed"], None)
                self.assertFalse(staged["local_project_user_annotation"]["provided"])
                self.assertEqual(staged["candidate_prescreen_ref"]["candidate_id"], record["candidate_id"])

                status, sample_count = validate_gold_set(config)
                self.assertEqual(status, "stub")
                self.assertEqual(sample_count, 0)

    def test_candidate_handoff_to_staging_blocks_duplicate_normalized_url(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                first_record = load_yaml(paths[0])
                first_record["human_review_status"] = "approved_for_staging"
                first_record["human_review_note_template_key"] = "approved"
                first_record["human_review_notes"] = "clear end-user product signal; evidence sufficient for staging"
                first_record["human_reviewed_at"] = utc_now_iso()
                dump_yaml(paths[0], first_record)

                duplicate_path = candidate_workspace / "github" / "2026-03-08_2026-03-15" / "cand_github_qf_agent_duplicate_url.yaml"
                duplicate_record = dict(first_record)
                duplicate_record["candidate_id"] = "cand_github_qf_agent_duplicate_url"
                duplicate_record["candidate_batch_id"] = "candidate_batch_github_qf_agent_2026-03-08_2026-03-15"
                duplicate_record["source_window"] = "2026-03-08..2026-03-15"
                duplicate_record["external_id"] = "different_external_id_same_url"
                duplicate_record["canonical_url"] = str(first_record["canonical_url"]).replace("https://", "HTTPS://").rstrip("/") + "/#fragment"
                duplicate_record["staging_handoff"] = {
                    "status": "not_started",
                    "staging_document_path": None,
                    "sample_slot_id": None,
                    "sample_id": None,
                    "blocking_items": [],
                    "last_attempted_at": None,
                }
                duplicate_path.parent.mkdir(parents=True, exist_ok=True)
                dump_yaml(duplicate_path, duplicate_record)

                results = handoff_candidates_to_staging(config, candidate_ids=None)

                self.assertEqual(len(results), 1)
                duplicate_after = load_yaml(duplicate_path)
                self.assertEqual(duplicate_after["staging_handoff"]["status"], "blocked")
                self.assertIn(
                    "Semantic duplicate source URL already present in staging",
                    duplicate_after["staging_handoff"]["blocking_items"][0],
                )

    def test_run_one_fill_iteration_consumes_existing_workspace_candidate_first(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                workflow_config = load_yaml(REPO_ROOT / "configs" / "candidate_prescreen_workflow.yaml")
                cursor = LiveDiscoveryCursor.from_workflow(
                    workflow_config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                )
                summary = run_one_fill_iteration(
                    config,
                    cursor=cursor,
                    live_limit=1,
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                self.assertIsNotNone(summary["handoff"])
                self.assertEqual(summary["handoff"]["status"], "written")
                self.assertIsNone(summary["live_discovery"])
                candidate_record = load_yaml(paths[0])
                self.assertEqual(candidate_record["human_review_status"], "approved_for_staging")
                self.assertEqual(candidate_record["staging_handoff"]["status"], "written")
                self.assertEqual(summary["progress_after"]["total_filled"], summary["progress_before"]["total_filled"] + 1)

    def test_run_one_fill_iteration_blocks_and_keeps_failed_candidate_traceable_after_terminal_prescreen_failure(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            with temp_config(candidate_workspace_dir=candidate_workspace, gold_set_staging_dir=staging_dir) as config:
                paths = run_candidate_prescreen(
                    config,
                    source_code="github",
                    window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )
                existing_record = load_yaml(paths[0])
                existing_record["llm_prescreen"]["status"] = "failed"
                existing_record["llm_prescreen"]["error_type"] = "schema_drift"
                existing_record["llm_prescreen"]["error_message"] = "preexisting review contract failure"
                dump_yaml(paths[0], existing_record)

                workflow_config = load_yaml(REPO_ROOT / "configs" / "candidate_prescreen_workflow.yaml")
                cursor = LiveDiscoveryCursor.from_workflow(
                    workflow_config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                )
                with patch("src.candidate_prescreen.fill_controller.run_candidate_prescreen") as run_prescreen_mock:
                    summary = run_one_fill_iteration(
                        config,
                        cursor=cursor,
                        live_limit=1,
                        discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                        llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                    )

                run_prescreen_mock.assert_not_called()
                self.assertIsNone(summary["handoff"])
                self.assertEqual(summary["progress_after"]["total_filled"], summary["progress_before"]["total_filled"])
                self.assertEqual(summary["live_discovery"]["failure"]["error_type"], "schema_drift")
                self.assertEqual(summary["live_discovery"]["failure"]["failed_step"], "existing_workspace_llm_review")
                failure_result = summary["review_results"][0]
                self.assertEqual(failure_result["review_status"], "pending_first_pass")
                self.assertEqual(failure_result["review_source"], "terminal_prescreen_failure")
                self.assertEqual(validate_candidate_workspace(config), 1)
                refreshed_record = load_yaml(paths[0])
                self.assertEqual(refreshed_record["llm_prescreen"]["status"], "failed")
                self.assertEqual(refreshed_record["llm_prescreen"]["error_type"], "schema_drift")

    def test_fill_gold_set_staging_until_complete_stops_at_300_without_writing_formal_gold_set(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            candidate_workspace = root / "candidate_workspace"
            staging_dir = root / "staging"
            gold_set_dir = _prepare_stub_gold_set_dir(root)
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)
            _prefill_remaining_slots(staging_dir, keep_empty_slots=1)

            with temp_config(
                candidate_workspace_dir=candidate_workspace,
                gold_set_staging_dir=staging_dir,
                gold_set_dir=gold_set_dir,
            ) as config:
                summary = fill_gold_set_staging_until_complete(
                    config,
                    source_code="github",
                    initial_window="2026-03-01..2026-03-08",
                    query_slice_id="qf_agent",
                    live_limit=1,
                    discovery_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "github_qf_agent_window.json",
                    llm_fixture_path=REPO_ROOT / "fixtures" / "candidate_prescreen" / "llm_prescreen_responses.json",
                )

                self.assertEqual(summary["status"], "completed")
                self.assertEqual(summary["total_filled"], 300)
                self.assertTrue(Path(summary["audit_log_path"]).exists())
                audit_log_text = Path(summary["audit_log_path"]).read_text(encoding="utf-8")
                self.assertIn("\"event\": \"initialize\"", audit_log_text)
                self.assertIn("\"event\": \"completed\"", audit_log_text)

                status, sample_count = validate_gold_set(config)
                self.assertEqual(status, "stub")
                self.assertEqual(sample_count, 0)
