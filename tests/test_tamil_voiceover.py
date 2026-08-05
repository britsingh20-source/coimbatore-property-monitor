import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tamil_voiceover import (
    DEFAULT_PARLER_STYLE,
    _duration_target,
    _quality_report,
    _save_voice,
    build_tamil_script,
    build_voice_segments,
)


class TamilVoiceoverTests(unittest.TestCase):
    def test_script_uses_verified_fields_without_disclosure_scene(self):
        script = build_tamil_script({
            "property_location": "வடவள்ளி",
            "property": {"bhk": "3BHK", "property_type": "வீடு", "price": "65 லட்சம்"},
        })
        self.assertIn("வடவள்ளி", script)
        self.assertIn("65 லட்சம்", script)
        self.assertNotIn("பிரதிநிதி காட்சிகள்", script)
        self.assertNotIn("disclosure", {item["scene"] for item in build_voice_segments({
            "property_location": "வடவள்ளி",
            "property": {"property_type": "வீடு"},
        })})

    def test_plot_voice_is_tamilized_and_skips_missing_scenes(self):
        segments = build_voice_segments({
            "property_location": "Near Thudiyalur, NGGO Colony, Mettupalayam Road, Coimbatore, Tamil Nadu",
            "property": {
                "property_type": "Plot", "land_area": "2 cents to 4 cents",
                "built_up_area": "NOT SPECIFIED", "price": "NOT SPECIFIED",
                "road_width": "30 ft and 33 ft wide tar roads",
            },
        })
        by_scene = {item["scene"]: item["text"] for item in segments}
        self.assertIn("துடியலூர் அருகே", by_scene["location"])
        self.assertIn("2 சென்ட் முதல் 4 சென்ட் வரை", by_scene["land"])
        self.assertIn("தார் சாலைகள்", by_scene["road"])
        self.assertNotIn("builtUp", by_scene)
        self.assertNotIn("price", by_scene)

    def test_default_parler_style_encodes_requested_delivery(self):
        style = DEFAULT_PARLER_STYLE.lower()
        for detail in ("male tamil", "coimbatore", "low-pitched", "natural pauses", "no background noise"):
            self.assertIn(detail, style)

    @patch("tamil_voiceover._retime_to_target")
    @patch("tamil_voiceover._quality_report", return_value={
        "valid": True, "issues": [], "target_duration_seconds": 2.0,
    })
    @patch("tamil_voiceover._save_indic_parler")
    def test_indic_parler_is_selected_only_after_quality_passes(
        self, save_parler, _quality, _retime
    ):
        engine = _save_voice("தமிழ் சோதனை", Path("unused.mp3"), engine="indic-parler")
        self.assertEqual("indic-parler", engine)
        save_parler.assert_called_once_with("தமிழ் சோதனை", Path("unused.mp3"), attempt=0)

    @patch("tamil_voiceover._retime_to_target")
    @patch("tamil_voiceover._quality_report", return_value={
        "valid": True, "issues": [], "target_duration_seconds": 2.0,
    })
    @patch("tamil_voiceover._save_edge", new_callable=AsyncMock)
    @patch("tamil_voiceover._save_indic_parler", side_effect=RuntimeError("model unavailable"))
    def test_edge_fallback_must_be_explicitly_enabled(
        self, _save_parler, save_edge, _quality, _retime
    ):
        with patch.dict(os.environ, {
            "TTS_ALLOW_EDGE_FALLBACK": "true", "INDIC_PARLER_ATTEMPTS": "2",
        }):
            engine = _save_voice("தமிழ் சோதனை", Path("unused.mp3"), engine="indic-parler")
        self.assertEqual("edge-quality-fallback", engine)
        self.assertEqual(2, _save_parler.call_count)
        save_edge.assert_awaited_once()

    def test_truncated_price_audio_is_rejected(self):
        text = "விலை, 65 லட்சம், பேச்சுவார்த்தைக்கு உட்பட்டது."
        with patch("tamil_voiceover._duration", return_value=0.936), patch(
            "tamil_voiceover._silence_metrics", return_value=(0.0, 0.0)
        ):
            report = _quality_report(text, Path("price.mp3"))
        self.assertFalse(report["valid"])
        self.assertTrue(any("truncated" in issue for issue in report["issues"]))

    def test_long_dead_gap_is_rejected(self):
        with patch("tamil_voiceover._duration", return_value=5.0), patch(
            "tamil_voiceover._silence_metrics", return_value=(2.0, 1.5)
        ):
            report = _quality_report("ரோடு வசதி, முப்பது அடி தார் சாலை.", Path("road.mp3"))
        self.assertFalse(report["valid"])
        self.assertTrue(any("dead gap" in issue for issue in report["issues"]))

    def test_duration_target_accounts_for_numbers_and_pauses(self):
        plain = _duration_target("விலை விவரம்")
        detailed = _duration_target("விலை, 65.50 லட்சம், பேச்சுவார்த்தைக்கு உட்பட்டது")
        self.assertGreater(detailed, plain)

    @patch("tamil_voiceover._save_indic_parler", side_effect=RuntimeError("model unavailable"))
    def test_strict_indic_mode_does_not_hide_failure(self, _save_parler):
        with patch.dict(os.environ, {"TTS_ALLOW_EDGE_FALLBACK": "false"}):
            with self.assertRaisesRegex(RuntimeError, "model unavailable"):
                _save_voice("தமிழ் சோதனை", Path("unused.mp3"), engine="indic-parler")


if __name__ == "__main__":
    unittest.main()
