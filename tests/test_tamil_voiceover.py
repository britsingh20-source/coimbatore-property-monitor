import unittest

from tamil_voiceover import build_tamil_script


class TamilVoiceoverTests(unittest.TestCase):
    def test_script_uses_verified_fields_and_disclosure(self):
        script = build_tamil_script({
            "property_location": "வடவள்ளி",
            "property": {"bhk": "3BHK", "property_type": "வீடு", "price": "65 லட்சம்"},
        })
        self.assertIn("வடவள்ளி", script)
        self.assertIn("65 லட்சம்", script)
        self.assertIn("பிரதிநிதி காட்சிகள்", script)


if __name__ == "__main__":
    unittest.main()
