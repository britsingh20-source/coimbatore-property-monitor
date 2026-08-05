import json
import tempfile
import unittest
from pathlib import Path

from select_render_jobs import parse_requested_ids, select_ids


class SelectRenderJobsTests(unittest.TestCase):
    def _fixture(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        jobs = root / "jobs"
        jobs.mkdir()
        for video_id, status in (
            ("new-one", "auto_approved"),
            ("new-two", "approved"),
            ("review-only", "needs_review"),
            ("historical", "auto_approved"),
        ):
            (jobs / f"{video_id}.json").write_text(
                json.dumps({"video_id": video_id, "status": status}),
                encoding="utf-8",
            )
        approved = root / "approved.txt"
        approved.write_text("historical\n", encoding="utf-8")
        return temporary, jobs, approved

    def test_parse_requested_ids_accepts_json_and_csv(self):
        self.assertEqual({"one", "two"}, parse_requested_ids('["one", "two"]'))
        self.assertEqual({"one", "two"}, parse_requested_ids("one,two\n"))

    def test_repository_dispatch_is_exact_and_status_gated(self):
        temporary, jobs, approved = self._fixture()
        with temporary:
            selected = select_ids(
                "repository_dispatch",
                jobs,
                approved,
                "",
                "HEAD",
                '["new-two", "review-only", "missing"]',
            )
        self.assertEqual(["new-two"], selected)

    def test_manual_run_does_not_render_every_historical_job(self):
        temporary, jobs, approved = self._fixture()
        with temporary:
            selected = select_ids("workflow_dispatch", jobs, approved, "", "HEAD")
        self.assertEqual(["historical"], selected)

    def test_manual_requested_ids_override_approval_file(self):
        temporary, jobs, approved = self._fixture()
        with temporary:
            selected = select_ids(
                "workflow_dispatch", jobs, approved, "", "HEAD", "new-one,new-two"
            )
        self.assertEqual(["new-one", "new-two"], selected)

    def test_unknown_event_is_fail_closed(self):
        temporary, jobs, approved = self._fixture()
        with temporary:
            selected = select_ids("schedule", jobs, approved, "", "HEAD")
        self.assertEqual([], selected)


if __name__ == "__main__":
    unittest.main()
