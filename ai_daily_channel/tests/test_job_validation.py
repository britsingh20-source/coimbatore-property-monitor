import unittest

from ai_daily_channel.src.job_validation import validate_job


def valid_job():
    return {
        "job_id": "musetalk-ta-20260824",
        "language": "ta",
        "status": "pack_ready",
        "tool": {
            "name": "MuseTalk",
            "official_url": "https://github.com/TMElyralab/MuseTalk",
            "free_claim": "open_source",
            "verified_at": "2026-08-24T12:00:00+05:30",
            "evidence": [{"url": "https://github.com/TMElyralab/MuseTalk", "claim": "MIT code and commercial model use"}],
            "limitations": ["GPU recommended"],
            "card_required": False,
            "watermark": False,
            "commercial_use": "allowed",
        },
        "script": {
            "exact_text": "This is deliberately longer than forty characters for validation.",
            "segments": [{"start_hint": 0, "end_hint": 3, "text": "Hook", "delivery": "energetic"}],
        },
        "prompts": {
            "cinematic_hook": "A cinematic vertical technology scene with the approved presenter reference image, precise action, camera and transition details.",
            "ai_broll": "A conceptual vertical technology visualization directly demonstrating the narrated AI transformation without generic robots or random text.",
        },
        "production": {"screen_demo": [], "motion_graphics": [], "edit_reference": []},
        "publishing": {"destinations": {}, "title": "Title", "caption": "Caption", "hashtags": ["#AI", "#FreeAITools", "#TamilTech"]},
    }


class JobValidationTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_job(valid_job()), [])

    def test_requires_evidence(self):
        job = valid_job()
        job["tool"]["evidence"] = []
        self.assertIn("at least one evidence item is required", validate_job(job))

    def test_exactly_three_hashtags(self):
        job = valid_job()
        job["publishing"]["hashtags"] = ["#AI"]
        self.assertIn("publishing.hashtags must contain exactly three entries", validate_job(job))


if __name__ == "__main__":
    unittest.main()
