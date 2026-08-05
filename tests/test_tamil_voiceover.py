import unittest

from tamil_voiceover import build_tamil_script, build_voice_segments


class TamilVoiceoverTests(unittest.TestCase):
    def test_script_uses_verified_fields_and_disclosure(self):
        script = build_tamil_script({
            "property_location": "வடவள்ளி",
            "property": {"bhk": "3BHK", "property_type": "வீடு", "price": "65 லட்சம்"},
        })
        self.assertIn("வடவள்ளி", script)
        self.assertIn("65 லட்சம்", script)
        self.assertIn("பிரதிநிதி காட்சிகள்", script)

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


if __name__ == "__main__":
    unittest.main()
