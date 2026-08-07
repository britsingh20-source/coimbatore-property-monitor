import asyncio
import json
import os
import re
import subprocess
from pathlib import Path


EDGE_VOICE = os.environ.get("TAMIL_MALE_VOICE", "ta-IN-ValluvarNeural")
VOICE_RATE = os.environ.get("TAMIL_VOICE_RATE", "+4%")
VOICE_PITCH = os.environ.get("TAMIL_VOICE_PITCH", "-1Hz")
DIALOGUE_GAP_SECONDS = 1.5


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
        "text": f"கோயம்புத்தூர்ல {location} ஏரியாவுல இருக்கிற இந்த {title} பாருங்க, லொக்கேஷன் நல்லா இருக்கு.",
    }]
    fact_lines = [
        ("land", "land_area", "மொத்த லேண்ட் ஏரியா {value} இருக்கு."),
        ("builtUp", "built_up_area", "பில்ட் அப் ஏரியா பாத்தீங்கனா {value} வருது."),
        ("price", "price", "இதோட விலை {value}."),
        ("facing", "facing", "வீடு {value} ஃபேசிங்."),
        ("road", "road_width", "முன்னாடி ரோடு வசதி {value} இருக்கு."),
        ("approval", "approval", "அப்ரூவல் பாத்தீங்கனா {value} இருக்கு."),
    ]
    for scene, key, sentence in fact_lines:
        value = _spoken(prop.get(key))
        if value:
            segments.append({"scene": scene, "text": sentence.format(value=_tamilize(value))})
    segments.extend([
        {"scene": "verify", "text": "லொக்கேஷன், அளவு, விலை, டாக்குமெண்ட் எல்லாத்தையும் சைட் விசிட்டுக்கு வரும்போது நாம கிளியரா செக் பண்ணிக்கலாம்."},
        {"scene": "cta", "text": "வீடு பிடிச்சிருந்தா, இன்னும் டீட்டெயில்ஸ் மற்றும் சைட் விசிட்டுக்கு கோயம்புத்தூர் வீடு பில்டர்ஸ்க்கு கால் பண்ணுங்க."},
    ])
    return segments


def build_tamil_script(job: dict) -> str:
    return " ".join(segment["text"] for segment in build_voice_segments(job))


async def _save_edge(text: str, output: Path) -> None:
    import edge_tts

    # Keep one stable prosody across the entire reel. Changing rate/pitch per scene
    # made the voice sound like separate robotic clips even with the same speaker.
    communicator = edge_tts.Communicate(
        text,
        EDGE_VOICE,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
        volume="+50%",
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
        "-af",
        "highpass=f=70,lowpass=f=14500,"
        "acompressor=threshold=-18dB:ratio=2.2:attack=15:release=180:makeup=1.5,"
        "loudnorm=I=-11:TP=-1:LRA=5",
        "-ar", "48000", "-ac", "1",
        "-codec:a", "libmp3lame", "-b:a", "192k", str(normalized),
    ], check=True)
    normalized.replace(path)


def _build_master_track(video_id: str, files: list[Path]) -> Path:
    """Create one narration file so Remotion never starts/stops the voice per scene."""
    master = Path("assets/audio") / f"{video_id}.mp3"
    silence = files[0].parent / "_dialogue-gap.mp3"
    concat_file = files[0].parent / "_narration-concat.txt"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
        "-t", str(DIALOGUE_GAP_SECONDS),
        "-codec:a", "libmp3lame", "-b:a", "192k", str(silence),
    ], check=True)
    concat_items: list[Path] = []
    for index, source in enumerate(files):
        concat_items.append(source)
        if index < len(files) - 1:
            concat_items.append(silence)
    concat_file.write_text(
        "\n".join(f"file '{item.resolve().as_posix()}'" for item in concat_items),
        encoding="utf-8",
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-ar", "48000", "-ac", "1",
        "-codec:a", "libmp3lame", "-b:a", "192k", str(master),
    ], check=True)
    silence.unlink(missing_ok=True)
    concat_file.unlink(missing_ok=True)
    return master


def create_voiceover(job: dict) -> Path:
    video_id = job["video_id"]
    output_dir = Path("assets/audio") / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing in output_dir.glob("*.mp3"):
        existing.unlink()
    master_existing = Path("assets/audio") / f"{video_id}.mp3"
    master_existing.unlink(missing_ok=True)
    segments = build_voice_segments(job)
    manifest = []
    audio_files: list[Path] = []
    for index, segment in enumerate(segments, start=1):
        output = output_dir / f"{index:02d}-{segment['scene']}.mp3"
        _save_voice(segment["text"], output)
        _normalize(output)
        audio_files.append(output)
        manifest.append({
            **segment,
            "file": output.name,
            "duration_seconds": round(_duration(output), 3),
            "tts_engine": "edge",
            "voice_style": EDGE_VOICE,
            "prosody": {"rate": VOICE_RATE, "pitch": VOICE_PITCH},
            "reference_style": "conversational Coimbatore Tamil; continuous presenter flow",
        })
    if audio_files:
        _build_master_track(video_id, audio_files)
    script_dir = Path("data/voiceover_scripts")
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / f"{video_id}.txt").write_text(
        "\n".join(f"[{item['scene']}] {item['text']}" for item in manifest), encoding="utf-8"
    )
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_dir
