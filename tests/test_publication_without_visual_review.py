"""Exercise publication with isolated platform clients; never contact social APIs."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[1] / "r2_social_autopilot.py"


class PublicationTests(unittest.TestCase):
    def namespace(self, names, **values):
        tree = ast.parse(SOURCE.read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        namespace = dict(values)
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(SOURCE), "exec"), namespace)
        return namespace

    def test_held_video_publishes_missing_destinations_without_visual_review(self):
        key = "social-ready/example.mp4"
        receipt = {"status": "published", "result": {"media_id": "existing-reel"}}
        state = {"objects": {key: {"etag": "same", "status": "quarantined_visual_policy", "platforms": {"instagram_reel": receipt}}}}
        reel, story, youtube = Mock(), Mock(return_value={"media_id": "new-story"}), Mock(return_value={"video_id": "new-short"})
        visual = Mock(side_effect=AssertionError("Visual review must not run"))
        client = Mock()
        client.download_file.side_effect = lambda bucket, key, path: Path(path).write_bytes(b"x" * 100001)
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / "example.json"
            job.write_text("{}")
            def local_path(path):
                return job.parent if str(path) == "data/video_jobs" else Path(path)
            ns = self.namespace(
                {"_publish_one"}, Path=local_path, json=json, tempfile=tempfile,
                _resolve_video_id=Mock(return_value="example"), build_social_content=Mock(return_value={"caption": "caption", "title": "title", "youtube_description": "description"}),
                _save_state=Mock(), _save_queue=Mock(), _visual_compliance_check=visual,
                prepare_youtube_short=Mock(return_value={"source": {"width": 1080, "height": 1920}, "output": {"width": 1080, "height": 1920}, "layout": "portrait"}),
                publish_instagram_reel=reel, publish_instagram_story=story, publish_youtube_short=youtube,
                PUBLIC_PLATFORMS=("instagram_reel", "instagram_story", "youtube_short"),
                _available=Mock(return_value=True), DRY_RUN=False, RETRY_CREDENTIAL_BLOCKED=False,
            )
            self.assertTrue(ns["_publish_one"](key, "same", client, "bucket", state, {"prompts": []}))
        visual.assert_not_called()
        reel.assert_not_called()
        story.assert_called_once()
        youtube.assert_called_once()
        self.assertIs(state["objects"][key]["platforms"]["instagram_reel"], receipt)

    def test_scan_releases_visual_holds_and_skips_completed_uploads(self):
        held, complete = "social-ready/held.mp4", "social-ready/complete.mp4"
        platforms = ("instagram_reel", "instagram_story", "youtube_short")
        state = {"objects": {held: {"status": "quarantined_visual_policy", "platforms": {}}, complete: {"platforms": {p: {"status": "published"} for p in platforms}}}}
        client = Mock()
        client.list_objects_v2.return_value = {"Contents": [{"Key": key, "ETag": "same", "LastModified": index} for index, key in enumerate((held, complete))]}
        publish = Mock(return_value=True)
        ns = self.namespace(
            {"main"}, _required=Mock(return_value="bucket"), _r2=Mock(return_value=client),
            _load_state=Mock(return_value=state), _load_queue=Mock(return_value={"prompts": []}),
            _save_state=Mock(), _save_queue=Mock(), _publish_one=publish,
            PREFIX="social-ready/", RECHECK_QUARANTINED=False, MAX_PER_RUN=5, PUBLIC_PLATFORMS=platforms,
        )
        ns["main"]()
        publish.assert_called_once_with(held, "same", client, "bucket", state, {"prompts": []})


if __name__ == "__main__":
    unittest.main()
