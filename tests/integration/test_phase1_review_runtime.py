from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from tests.helpers import REPO_ROOT


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _ambiguous_source_item() -> dict[str, object]:
    return {
        "source_item_id": "src_item_review_1",
        "raw_id": "raw_review_1",
        "source_id": "src_product_hunt",
        "external_id": "ph_review_1",
        "canonical_url": "https://example.com/omni-assistant",
        "linked_homepage_url": "https://example.com/omni-assistant",
        "linked_repo_url": None,
        "title": "Omni Assistant",
        "author_name": "Acme",
        "published_at": "2026-03-01T00:00:00Z",
        "raw_text_excerpt": (
            "Built with GPT workflows in a weekend. General AI assistant for any writing or research task. "
            "All-in-one AI for everyone."
        ),
        "current_summary": "General AI assistant for everyone.",
        "current_metrics_json": {"vote_count": 41},
        "first_observed_at": "2026-03-01T00:00:00Z",
        "latest_observed_at": "2026-03-01T00:00:00Z",
        "normalization_version": "product_hunt_v1",
    }


class Phase1ReviewRuntimeIntegrationTests(unittest.TestCase):
    def run_cli(self, *args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "src.cli", *args],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_trigger_taxonomy_review_persists_issue_and_queue_entry(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            source_item_path = root / "source_item.json"
            record_path = root / "taxonomy_record.json"
            _write_json(source_item_path, _ambiguous_source_item())

            install = self.run_cli("install", env=env)
            self.assertEqual(install.returncode, 0, msg=install.stderr)

            triggered = self.run_cli(
                "trigger-taxonomy-review",
                "--source-item-path",
                str(source_item_path),
                "--record-path",
                str(record_path),
                env=env,
            )
            self.assertEqual(triggered.returncode, 0, msg=triggered.stderr)
            trigger_summary = json.loads(triggered.stdout)
            self.assertTrue(trigger_summary["review_triggered"])
            self.assertEqual(trigger_summary["category_code"], "unresolved")
            self.assertTrue(record_path.exists())

            queue = self.run_cli("review-queue", "--open-only", env=env)
            self.assertEqual(queue.returncode, 0, msg=queue.stderr)
            queue_entries = json.loads(queue.stdout)
            self.assertEqual(len(queue_entries), 1)
            self.assertEqual(queue_entries[0]["review_issue_id"], trigger_summary["review_issue_id"])
            self.assertEqual(queue_entries[0]["queue_bucket"], "taxonomy_conflict")

    def test_resolve_taxonomy_review_cli_updates_record_and_clears_open_queue(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            source_item_path = root / "source_item.json"
            record_path = root / "taxonomy_record.json"
            _write_json(source_item_path, _ambiguous_source_item())

            self.assertEqual(self.run_cli("install", env=env).returncode, 0)
            triggered = self.run_cli(
                "trigger-taxonomy-review",
                "--source-item-path",
                str(source_item_path),
                "--record-path",
                str(record_path),
                env=env,
            )
            review_issue_id = json.loads(triggered.stdout)["review_issue_id"]

            resolved = self.run_cli(
                "resolve-taxonomy-review",
                "--record-path",
                str(record_path),
                "--review-issue-id",
                review_issue_id,
                "--resolution-action",
                "mark_unresolved",
                "--resolution-notes",
                "Human review confirms the current effective taxonomy should remain unresolved.",
                "--reviewer",
                "local_project_user",
                env=env,
            )
            self.assertEqual(resolved.returncode, 0, msg=resolved.stderr)
            resolution_summary = json.loads(resolved.stdout)
            self.assertEqual(resolution_summary["status"], "resolved")
            self.assertEqual(resolution_summary["effective_category_code"], "unresolved")

            updated_record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(updated_record["effective_taxonomy"]["category_code"], "unresolved")
            self.assertTrue(updated_record["unresolved_registry_entry"]["is_effective_unresolved"])

            queue = self.run_cli("review-queue", "--open-only", env=env)
            self.assertEqual(json.loads(queue.stdout), [])

    def test_resolve_taxonomy_review_cli_enforces_maker_checker_for_p0_override(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            source_item_path = root / "source_item.json"
            record_path = root / "taxonomy_record.json"
            _write_json(source_item_path, _ambiguous_source_item())

            self.assertEqual(self.run_cli("install", env=env).returncode, 0)
            triggered = self.run_cli(
                "trigger-taxonomy-review",
                "--source-item-path",
                str(source_item_path),
                "--record-path",
                str(record_path),
                "--priority-code",
                "P0",
                env=env,
            )
            review_issue_id = json.loads(triggered.stdout)["review_issue_id"]

            missing_approval = self.run_cli(
                "resolve-taxonomy-review",
                "--record-path",
                str(record_path),
                "--review-issue-id",
                review_issue_id,
                "--resolution-action",
                "override_auto_result",
                "--resolution-notes",
                "Human reviewer wants to override unresolved to knowledge.",
                "--reviewer",
                "local_project_user",
                "--override-category-code",
                "JTBD_KNOWLEDGE",
                env=env,
            )
            self.assertEqual(missing_approval.returncode, 2)
            self.assertIn("require approver and approved_at", missing_approval.stderr)

            approved = self.run_cli(
                "resolve-taxonomy-review",
                "--record-path",
                str(record_path),
                "--review-issue-id",
                review_issue_id,
                "--resolution-action",
                "override_auto_result",
                "--resolution-notes",
                "Maker-checker approved override to knowledge.",
                "--reviewer",
                "local_project_user",
                "--override-category-code",
                "JTBD_KNOWLEDGE",
                "--approver",
                "local_project_user",
                "--approved-at",
                "2026-04-12T10:00:00Z",
                env=env,
            )
            self.assertEqual(approved.returncode, 0, msg=approved.stderr)
            approval_summary = json.loads(approved.stdout)
            self.assertTrue(approval_summary["maker_checker_required"])
            self.assertEqual(approval_summary["effective_category_code"], "JTBD_KNOWLEDGE")

    def test_trigger_entity_review_persists_entity_merge_uncertainty(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            source_item_path = root / "entity_source_item.json"
            existing_products_path = root / "existing_products.json"
            _write_json(
                source_item_path,
                {
                    "source_item_id": "src_item_entity_1",
                    "raw_id": "raw_entity_1",
                    "source_id": "src_product_hunt",
                    "external_id": "ph_entity_1",
                    "canonical_url": "https://example.com/copilot",
                    "linked_homepage_url": "https://example.com/copilot",
                    "linked_repo_url": None,
                    "title": "Copilot",
                    "author_name": "Acme",
                    "first_observed_at": "2026-03-01T00:00:00Z",
                    "latest_observed_at": "2026-03-01T00:00:00Z",
                    "normalization_version": "product_hunt_v1",
                },
            )
            existing_products_path.write_text(
                json.dumps(
                    [
                        {"product_id": "prod_1", "canonical_homepage_url": "https://example.com/copilot", "normalized_name": "copilot"},
                        {"product_id": "prod_2", "canonical_homepage_url": "https://example.com/copilot", "normalized_name": "copilot"},
                    ],
                    indent=2,
                    ensure_ascii=True,
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(self.run_cli("install", env=env).returncode, 0)
            triggered = self.run_cli(
                "trigger-entity-review",
                "--source-item-path",
                str(source_item_path),
                "--existing-products-path",
                str(existing_products_path),
                "--priority-code",
                "P0",
                env=env,
            )
            self.assertEqual(triggered.returncode, 0, msg=triggered.stderr)
            summary = json.loads(triggered.stdout)
            self.assertTrue(summary["review_triggered"])
            self.assertEqual(summary["issue_type"], "entity_merge_uncertainty")

            queue = self.run_cli("review-queue", "--open-only", env=env)
            queue_entries = json.loads(queue.stdout)
            self.assertEqual(queue_entries[0]["queue_bucket"], "high_impact_merge")

    def test_trigger_score_review_persists_score_conflict_issue(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            env = os.environ.copy()
            env.update(
                {
                    "APO_RAW_STORE_DIR": str(root / "raw_store"),
                    "APO_TASK_STORE_PATH": str(root / "task_store" / "tasks.json"),
                    "APO_MART_OUTPUT_DIR": str(root / "marts"),
                }
            )
            score_snapshot_path = root / "score_snapshot.json"
            _write_json(
                score_snapshot_path,
                {
                    "product_id": "prod_score_1",
                    "score_run_id": "score_run_prod_score_1",
                    "source_item_id": "src_item_score_1",
                    "source_url": "https://example.com/prod_score_1",
                    "current_auto_result": {
                        "score_type": "attention_score",
                        "band": None,
                        "normalized_value": None,
                        "rationale": "benchmark_sample_insufficient",
                    },
                    "conflict_point": "Attention output stayed null after benchmark sampling and needs explicit review follow-up.",
                    "recommended_action": "needs_more_evidence",
                },
            )

            self.assertEqual(self.run_cli("install", env=env).returncode, 0)
            triggered = self.run_cli(
                "trigger-score-review",
                "--score-snapshot-path",
                str(score_snapshot_path),
                "--issue-type",
                "score_conflict",
                env=env,
            )
            self.assertEqual(triggered.returncode, 0, msg=triggered.stderr)
            summary = json.loads(triggered.stdout)
            self.assertTrue(summary["review_triggered"])
            self.assertEqual(summary["issue_type"], "score_conflict")

            queue = self.run_cli("review-queue", "--open-only", env=env)
            queue_entries = json.loads(queue.stdout)
            self.assertEqual(queue_entries[0]["queue_bucket"], "score_conflict")


if __name__ == "__main__":
    unittest.main()
