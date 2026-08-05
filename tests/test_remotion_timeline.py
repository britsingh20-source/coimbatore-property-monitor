import json
import os
import tempfile
import unittest
from pathlib import Path

import prepare_remotion_job


class RemotionTimelineTests(unittest.TestCase):
    def test_plot_timeline_matches_available_voice_scenes(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                os.chdir(temporary)
                video_id = "plot-test"
                Path("data/video_jobs").mkdir(parents=True)
                Path(f"assets/properties/{video_id}").mkdir(parents=True)
                Path(f"assets/properties/{video_id}/01.jpg").write_bytes(b"image")
                for scene in ("land", "road"):
                    folder = Path(f"assets/videos/{video_id}") / scene
                    folder.mkdir(parents=True)
                    (folder / "01.mp4").write_bytes(b"video")
                audio_dir = Path("assets/audio") / video_id
                audio_dir.mkdir(parents=True)
                manifest = []
                for index, scene in enumerate(("location", "land", "road", "verify", "cta"), start=1):
                    filename = f"{index:02d}-{scene}.mp3"
                    (audio_dir / filename).write_bytes(b"audio")
                    manifest.append({"scene": scene, "file": filename, "duration_seconds": 2.0})
                (audio_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                job_path = Path("data/video_jobs/plot-test.json")
                job_path.write_text(json.dumps({
                    "video_id": video_id,
                    "property_location": "Near Thudiyalur, NGGO Colony, Mettupalayam Road, Coimbatore, Tamil Nadu",
                    "property": {"property_type": "Plot", "land_area": "2 to 4 cents", "road_width": "30 ft"},
                }), encoding="utf-8")
                old_public, old_props = prepare_remotion_job.PUBLIC, prepare_remotion_job.PROPS
                prepare_remotion_job.PUBLIC = Path("professional_video/public/render")
                prepare_remotion_job.PROPS = Path("data/remotion_props")
                try:
                    props_path = prepare_remotion_job.prepare(job_path)
                finally:
                    prepare_remotion_job.PUBLIC, prepare_remotion_job.PROPS = old_public, old_props
                props = json.loads(props_path.read_text(encoding="utf-8"))
                self.assertEqual(props["templateVariant"], "plot")
                self.assertEqual(props["locationLabel"], "NGGO Colony")
                self.assertEqual(set(props["sceneMedia"]), {"land", "road"})
                self.assertIn("stock-road-01.mp4", props["sceneMedia"]["road"][0])
                self.assertNotEqual(props["sceneMedia"]["road"], props["sceneMedia"]["land"])
                self.assertEqual(props["sceneOrder"], [item["scene"] for item in manifest])
                self.assertEqual(len(props["voiceSegments"]), len(manifest))
                self.assertEqual(props["durationInFrames"], sum(props["sceneDurations"].values()))
            finally:
                os.chdir(original)


if __name__ == "__main__":
    unittest.main()
