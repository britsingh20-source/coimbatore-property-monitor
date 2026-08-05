import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from select_render_jobs import select_ids
from video_pipeline import automatic_approval_ready


class AutomaticApprovalTests(unittest.TestCase):
    def test_complete_target_property_is_ready(self):
        self.assertTrue(automatic_approval_ready({
            "property_type": "House",
            "land_area": "2.75 cents",
            "built_up_area": "1050 sqft",
            "source_facts": ["fact"],
        }))

    def test_sparse_property_requires_review(self):
        self.assertFalse(automatic_approval_ready({
            "property_type": "House",
            "land_area": "NOT SPECIFIED",
            "source_facts": ["fact"],
        }))


class RenderSelectionTests(unittest.TestCase):
    def _job(self, directory: Path, video_id: str, status: str):
        (directory / f"{video_id}.json").write_text(json.dumps({
            "video_id": video_id,
            "status": status,
        }), encoding="utf-8")

    def test_push_renders_only_changed_auto_approved_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp)
            self._job(jobs, "new", "auto_approved")
            self._job(jobs, "old", "auto_approved")
            self._job(jobs, "review", "needs_review")
            with patch("select_render_jobs.changed_job_ids", return_value={"new", "review"}):
                selected = select_ids("push", jobs, jobs / "approved.txt", "before", "after")
            self.assertEqual(selected, ["new"])

    def test_manual_dispatch_includes_renderable_and_explicit_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp)
            self._job(jobs, "auto", "auto_approved")
            self._job(jobs, "fixture", "approval_pending")
            approved = jobs / "approved.txt"
            approved.write_text("fixture\n", encoding="utf-8")
            self.assertEqual(select_ids("workflow_dispatch", jobs, approved, "", "HEAD"), ["auto", "fixture"])


if __name__ == "__main__":
    unittest.main()
