import asyncio
import os
from pathlib import Path

VOICE = os.environ.get("TAMIL_MALE_VOICE", "ta-IN-ValluvarNeural")


def _spoken(value) -> str:
    value = str(value or "").strip()
    return "" if not value or value.upper() == "NOT SPECIFIED" else value


def build_tamil_script(job: dict) -> str:
    prop = job.get("property", {})
    location = _spoken(job.get("property_location")) or "கோயம்புத்தூர்"
    bhk = _spoken(prop.get("bhk"))
    property_type = _spoken(prop.get("property_type")) or "வீடு"
    sentences = [f"கோயம்புத்தூர் {location} பகுதியில் உள்ள இந்த {bhk} {property_type} பற்றிய முக்கிய தகவல்களை பார்க்கலாம்."]
    for label, key in [
        ("நில அளவு", "land_area"), ("கட்டிட பரப்பளவு", "built_up_area"),
        ("விலை", "price"), ("பார்க்கும் திசை", "facing"),
        ("சாலை அகலம்", "road_width"), ("அனுமதி", "approval"),
    ]:
        value = _spoken(prop.get(key))
        if value:
            sentences.append(f"{label}, {value}.")
    sentences.extend([
        "இந்த வீடியோவில் பயன்படுத்தப்பட்ட சில காட்சிகள் அந்த பகுதியை விளக்கும் பிரதிநிதி காட்சிகள் மட்டுமே.",
        "விலை, இடம் மற்றும் ஆவணங்களை நேரில் சரிபார்த்த பிறகே முடிவு செய்யுங்கள்.",
        "மேலும் உறுதியான விவரங்களுக்கு எஸ் பி பில்டர்ஸை தொடர்பு கொள்ளுங்கள்.",
    ])
    return " ".join(sentence for sentence in sentences if sentence)


async def _save(script: str, output: Path) -> None:
    import edge_tts

    communicator = edge_tts.Communicate(script, VOICE, rate="-5%", pitch="-2Hz")
    await communicator.save(str(output))


def create_voiceover(job: dict) -> Path:
    output = Path("assets/audio") / f"{job['video_id']}.mp3"
    output.parent.mkdir(parents=True, exist_ok=True)
    script = build_tamil_script(job)
    Path("data/voiceover_scripts").mkdir(parents=True, exist_ok=True)
    Path("data/voiceover_scripts", f"{job['video_id']}.txt").write_text(script, encoding="utf-8")
    asyncio.run(_save(script, output))
    return output
