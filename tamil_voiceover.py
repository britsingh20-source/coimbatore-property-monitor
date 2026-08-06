import asyncio
import json
import os
import re
import subprocess
from pathlib import Path


EDGE_VOICE = os.environ.get("TAMIL_MALE_VOICE", "ta-IN-ValluvarNeural")


def _spoken(value) -> str:
    value = str(value or "").strip()
    return "" if not value or value.upper() == "NOT SPECIFIED" else value


def _tamilize(value: str) -> str:
    replacements = [
        (r"\bNear\b", "பக்கத்துல"), (r"\bThudiyalur\b", "துடியலூர்"),
        (r"\bNGGO\b", "என் ஜி ஜி ஓ"), (r"\bColony\b", "காலனி"),
        (r"\bMettupalayam Road\b", "மேட்டுப்பாளையம் ரோடு"),
        (r"\bPattanam\b", "பட்டணம்"), (r"\bCoimbatore\b", "கோயம்புத்தூர்"),
        (r"\bTamil Nadu\b", ""), (r"\bcents?\b", "சென்ட்"),
        (r"\bsq\.?\s*ft\.?\b|\bsqft\b", "சதுர அடி"), (r"\bft\b", "அடி"),
        (r"\bNorth\b", "வடக்கு"), (r"\bSouth\b", "தெற்கு"),
        (r"\bEast\b", "கிழக்கு"), (r"\bWest\b", "மேற்கு"),
        (r"\bPlot\b", "சைட்"), (r"\bHouse\b", "தனி வீடு"),
        (r"\bVilla\b", "வில்லா"), (r"\bDTCP\b", "டி டி சி பி"),
        (r"\bwide tar roads?\b", "அகலமான தார் ரோடு"),
        (r"\bto\b", "முதல்"), (r"\band\b", "மற்றும்"),
    ]
    result = str(value)
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    result = re.sub(r"(\d+\s+சென்ட்)\s+முதல்\s+(\d+\s+சென்ட்)(?!\s+வரை)", r"\1 முதல் \2 வரை", result)
    result = result.replace("பக்கத்துல துடியலூர்", "துடியலூர் பக்கத்துல")
    return re.sub(r"\s+,", ",", re.sub(r"\s+", " ", result)).strip(" ,")


def build_voice_segments(job: dict) -> list[dict]:
    prop = job.get("property", {})
    location = _tamilize(_spoken(job.get("property_location")) or "கோயம்புத்தூர்")
    location = re.sub(r",?\s*கோயம்புத்தூர்\s*$", "", location).strip(" ,") or "கோயம்புத்தூர்"
    property_type = _tamilize(_spoken(prop.get("property_type")) or "வீடு")
    bhk = _spoken(prop.get("bhk"))
    title = " ".join(value for value in (bhk, property_type) if value)

    segments = [{
        "scene": "location",
        "text": f"கோயம்புத்தூர்ல {location} ஏரியாவுல இருக்கிற இந்த {title} பாருங்க, நல்ல லொக்கேஷன்ல இருக்கு.",
    }]
    fact_lines = [
        ("land", "land_area", "மொத்த லேண்ட் ஏரியா {value},"),
        ("builtUp", "built_up_area", "பில்ட் அப் ஏரியா {value},"),
        ("price", "price", "இந்த ப்ராப்பர்ட்டி விலை {value},"),
        ("facing", "facing", "ஃபேசிங் {value},"),
        ("road", "road_width", "முன்னாடி ரோடு வசதி {value},"),
        ("approval", "approval", "அப்ரூவல் {value},"),
    ]
    for scene, key, sentence in fact_lines:
        value = _spoken(prop.get(key))
        if value:
            segments.append({"scene": scene, "text": sentence.format(value=_tamilize(value))})
    segments.extend([
        {"scene": "verify", "text": "லொக்கேஷன், அளவு, விலை, டாக்குமெண்ட் எல்லாத்தையும் சைட் விசிட்ட்ல நாம கிளியரா செக் பண்ணிக்கலாம்,"},
        {"scene": "cta", "text": "டீட்டெயில்ஸ் வேணும்னா கோயம்புத்தூர் வீடு பில்டர்ஸ்க்கு இப்பவே கால் பண்ணுங்க."},
    ])
    return segments


def build_tamil_script(job: dict) -> str:
    return " ".join(segment["text"] for segment in build_voice_segments(job))


async def _save_edge(text: str, output: Path) -> None:
    import edge_tts

    communicator = edge_tts.Communicate(
        text, EDGE_VOICE, rate="+8%", pitch="-1Hz", volume="+50%"
    )
    await communicator.save(str(output))


def _save_voice(text: str, output: Path) -> None:
    asyncio.run(_save_edge(text, output))


def _duration(path: Path) -> float:
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], check=True, capture_output=True, text=True)
    return float(result.stdout.strip())


def _normalize(path: Path) -> None:
    normalized = path.with_name(f"{path.stem}-normalized.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
        "-af", "loudnorm=I=-11:TP=-1:LRA=4",
        "-codec:a", "libmp3lame", "-b:a", "192k", str(normalized),
    ], check=True)
    normalized.replace(path)


def create_voiceover(job: dict) -> Path:
    video_id = job["video_id"]
    output_dir = Path("assets/audio") / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*.mp3"):
        existing.unlink()
    segments = build_voice_segments(job)
    manifest = []
    for index, segment in enumerate(segments, start=1):
        output = output_dir / f"{index:02d}-{segment['scene']}.mp3"
        _save_voice(segment["text"], output)
        _normalize(output)
        manifest.append({
            **segment,
            "file": output.name,
            "duration_seconds": round(_duration(output), 3),
            "tts_engine": "edge",
            "voice_style": EDGE_VOICE,
        })
    script_dir = Path("data/voiceover_scripts")
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / f"{video_id}.txt").write_text(
        "\n".join(f"[{item['scene']}] {item['text']}" for item in manifest), encoding="utf-8"
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_dir
