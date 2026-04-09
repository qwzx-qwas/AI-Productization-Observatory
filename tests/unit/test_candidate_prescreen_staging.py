from __future__ import annotations

import copy
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.candidate_prescreen.staging import (
    dedupe_staging_semantic_duplicates,
    handoff_candidate_to_staging,
    staging_progress,
    validate_staging_workspace,
)
from src.common.errors import ContractValidationError
from src.common.files import dump_yaml, load_yaml
from tests.helpers import REPO_ROOT


def _filled_and_empty_slot(staging_dir: Path) -> tuple[Path, dict[str, object], Path, dict[str, object]]:
    filled_entry: tuple[Path, dict[str, object]] | None = None
    empty_entry: tuple[Path, dict[str, object]] | None = None
    for staging_path in sorted(staging_dir.glob("gold_set_300_staging_batch_*.yaml")):
        payload = load_yaml(staging_path)
        samples = payload["samples"]
        for sample in samples:
            if sample.get("sample_id") and filled_entry is None:
                filled_entry = (staging_path, sample)
            if not sample.get("sample_id") and empty_entry is None:
                empty_entry = (staging_path, sample)
            if filled_entry is not None and empty_entry is not None:
                return filled_entry[0], filled_entry[1], empty_entry[0], empty_entry[1]
    raise AssertionError("Expected at least one filled slot and one empty slot in staging fixture")


def _inject_semantic_duplicate(staging_dir: Path) -> dict[str, object]:
    source_path, source_sample, target_path, target_sample = _filled_and_empty_slot(staging_dir)
    target_payload = load_yaml(target_path)
    target_samples = target_payload["samples"]
    source_clone = copy.deepcopy(source_sample)
    duplicate_sample_id = f"{source_sample['sample_id']}_duplicate"
    duplicate_slot_id = str(target_sample["sample_slot_id"])
    duplicate_slot_index = target_sample["slot_index"]
    source_clone["sample_id"] = duplicate_sample_id
    source_clone["sample_slot_id"] = duplicate_slot_id
    source_clone["slot_index"] = duplicate_slot_index
    source_clone["candidate_prescreen_ref"]["candidate_id"] = duplicate_sample_id
    source_clone["source_record_refs"][0]["candidate_id"] = duplicate_sample_id
    source_clone["sample_metadata"]["sample_id"] = duplicate_sample_id
    source_clone["staged_from_candidate_prescreen_path"] = str(
        Path(source_clone["staged_from_candidate_prescreen_path"]).with_name(f"{duplicate_sample_id}.yaml")
    )
    for index, sample in enumerate(target_samples):
        if sample.get("sample_slot_id") == duplicate_slot_id:
            target_samples[index] = source_clone
            break
    dump_yaml(target_path, target_payload)
    return {
        "source_path": source_path,
        "source_slot_id": str(source_sample["sample_slot_id"]),
        "target_path": target_path,
        "target_slot_id": duplicate_slot_id,
        "duplicate_sample_id": duplicate_sample_id,
    }


def _copy_clean_staging_dir(staging_dir: Path) -> None:
    shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)
    dedupe_staging_semantic_duplicates(staging_dir)


class CandidatePrescreenStagingUnitTests(unittest.TestCase):
    def test_validate_staging_workspace_rejects_duplicate_source_semantic_key(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            _inject_semantic_duplicate(staging_dir)

            with self.assertRaises(ContractValidationError) as ctx:
                validate_staging_workspace(staging_dir)

            self.assertIn("Duplicate source URL key in staging workspace", str(ctx.exception))

    def test_dedupe_staging_semantic_duplicates_clears_duplicate_slot_and_restores_valid_workspace(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            before_progress = staging_progress(staging_dir)
            duplicate_info = _inject_semantic_duplicate(staging_dir)

            summary = dedupe_staging_semantic_duplicates(staging_dir)

            self.assertEqual(summary["duplicate_group_count"], 1)
            self.assertEqual(summary["cleared_slot_count"], 1)
            self.assertEqual(summary["staging_total_filled"], before_progress["total_filled"])
            progress = validate_staging_workspace(staging_dir)
            self.assertEqual(progress["total_filled"], before_progress["total_filled"])
            source_payload = load_yaml(duplicate_info["source_path"])
            target_payload = load_yaml(duplicate_info["target_path"])
            source_sample = next(sample for sample in source_payload["samples"] if sample["sample_slot_id"] == duplicate_info["source_slot_id"])
            target_sample = next(sample for sample in target_payload["samples"] if sample["sample_slot_id"] == duplicate_info["target_slot_id"])
            candidate_states = [bool(source_sample.get("sample_id")), bool(target_sample.get("sample_id"))]
            self.assertEqual(sum(candidate_states), 1)
            cleared_sample = source_sample if not source_sample.get("sample_id") else target_sample
            self.assertEqual(cleared_sample["current_state"], "awaiting_real_input")
            self.assertIsNone(cleared_sample["sample_id"])
            self.assertEqual(cleared_sample["source_record_refs"], [])

    def test_handoff_candidate_to_staging_prioritizes_sample_key_duplicate_guard(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            staging_path, source_sample, _, _ = _filled_and_empty_slot(staging_dir)
            payload = load_yaml(staging_path)
            for sample in payload["samples"]:
                if sample.get("sample_slot_id") != source_sample["sample_slot_id"]:
                    continue
                sample["sample_metadata"]["sample_key"] = "sample_locked_duplicate"
                sample["source_record_refs"][0]["sample_key"] = "sample_locked_duplicate"
                break
            dump_yaml(staging_path, payload)
            source_ref = source_sample["source_record_refs"][0]
            candidate_record = {
                "candidate_id": "cand_sample_key_duplicate_guard",
                "candidate_batch_id": "candidate_batch_github_qf_agent_2026-04-06",
                "sample_key": "sample_locked_duplicate",
                "human_review_status": "approved_for_staging",
                "human_review_notes": "Approved in first-pass review.",
                "human_reviewed_at": "2026-04-06T09:10:00Z",
                "source": "github",
                "source_id": source_ref["source_id"],
                "source_window": "2026-04-01..2026-04-06",
                "external_id": "different_external_id_same_sample_key",
                "canonical_url": "https://github.com/example/completely-different-product",
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "whitelist_reason": None,
                "llm_prescreen": {
                    "recommended_action": "candidate_pool",
                },
            }

            with self.assertRaises(ContractValidationError) as ctx:
                handoff_candidate_to_staging(
                    candidate_record,
                    candidate_path=Path(tmp_dir) / "candidate.yaml",
                    staging_dir=staging_dir,
                )

            self.assertIn("Semantic duplicate source URL already present in staging", str(ctx.exception))

    def test_handoff_candidate_to_staging_rejects_semantic_duplicate_source_url_with_legacy_fallback(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            _, source_sample, _, _ = _filled_and_empty_slot(staging_dir)
            source_ref = source_sample["source_record_refs"][0]
            duplicate_url_variant = str(source_ref["canonical_url"]).replace("https://", "HTTPS://").rstrip("/") + "/#fragment"
            candidate_record = {
                "candidate_id": "cand_semantic_duplicate_guard",
                "candidate_batch_id": "candidate_batch_github_qf_agent_2026-04-06",
                "human_review_status": "approved_for_staging",
                "human_review_notes": "Approved in first-pass review.",
                "human_reviewed_at": "2026-04-06T09:10:00Z",
                "source": "github",
                "source_id": source_ref["source_id"],
                "source_window": "2026-04-01..2026-04-06",
                "external_id": "different_external_id_same_url",
                "canonical_url": duplicate_url_variant,
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "whitelist_reason": None,
                "llm_prescreen": {
                    "recommended_action": "candidate_pool",
                },
            }

            with self.assertRaises(ContractValidationError) as ctx:
                handoff_candidate_to_staging(
                    candidate_record,
                    candidate_path=Path(tmp_dir) / "candidate.yaml",
                    staging_dir=staging_dir,
                )

            self.assertIn("Semantic duplicate source URL already present in staging", str(ctx.exception))

    def test_handoff_candidate_to_staging_rejects_blank_canonical_url(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            _copy_clean_staging_dir(staging_dir)
            candidate_record = {
                "candidate_id": "cand_invalid_url_guard",
                "candidate_batch_id": "candidate_batch_github_qf_agent_2026-04-06",
                "human_review_status": "approved_for_staging",
                "human_review_notes": "Approved in first-pass review.",
                "human_reviewed_at": "2026-04-06T09:10:00Z",
                "source": "github",
                "source_id": "src_github",
                "source_window": "2026-04-01..2026-04-06",
                "external_id": "url-missing",
                "canonical_url": "   ",
                "query_family": "ai_applications_and_products",
                "query_slice_id": "qf_agent",
                "selection_rule_version": "github_qsv1",
                "whitelist_reason": None,
                "llm_prescreen": {
                    "recommended_action": "candidate_pool",
                },
            }

            with self.assertRaises(ContractValidationError) as ctx:
                handoff_candidate_to_staging(
                    candidate_record,
                    candidate_path=Path(tmp_dir) / "candidate.yaml",
                    staging_dir=staging_dir,
                )

            self.assertIn("candidate_prescreen_record.canonical_url must be a non-empty string", str(ctx.exception))
