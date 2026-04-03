from __future__ import annotations

import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.candidate_prescreen.staging import summarize_staging_progress
from tests.helpers import REPO_ROOT


class CandidatePrescreenStagingUnitTests(unittest.TestCase):
    def test_summarize_staging_progress_reports_next_empty_slot(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            staging_dir = Path(tmp_dir) / "staging"
            shutil.copytree(REPO_ROOT / "docs" / "gold_set_300_real_asset_staging", staging_dir)

            progress = summarize_staging_progress(staging_dir)

            self.assertEqual(progress.total_filled, 42)
            self.assertEqual(progress.total_slots, 300)
            self.assertEqual(progress.file_count, 20)
            self.assertFalse(progress.is_complete)
            self.assertIsNotNone(progress.next_empty_slot)
            self.assertEqual(progress.next_empty_slot.sample_slot_id, "GS300-043")
