import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


EDGE_VOICE = os.environ.get("TAMIL_MALE_VOICE", "ta-IN-ValluvarNeural")
PARLER_MODEL = os.environ.get("INDIC_PARLER_MODEL", "ai4bharat/indic-parler-tts")
DEFAULT_PARLER_STYLE = (
    "A young adult male Tamil property presenter speaks in a natural Coimbatore conversational "
    "style. His voice is slightly low-pitched, warm, confident and energetic without sounding "
    "like an announcer. He uses smooth modulation, short natural pauses between facts, clear "
    "Tamil pronunciation, steady medium-fast pacing, and gently emphasizes location, land size, "
    "price and road access. The recording is very clear and close-mic, with no background noise, "
    "no music, no reverberation and consistent loudness."
)
_PARLER_RUNTIME = None


def _spoken(value) -> str:
    value = str(value or "").strip()
    return "" if not value or value.upper() == "NOT SPECIFIED" else value


def _tamilize(value: str) -> str:
    replacements = [
        (r"\bNear\b", "அருகில்"), (r"\bThudiyalur\b", "துடியலூர்"),
        (r"\bNGGO\b", "என் ஜி ஜி ஓ"), (r"\bColony\b", "காலனி"),
        (r"\bMettupalayam Road\b", "மேட்டுப்பாளையம் சாலை"),
        (r"\bPattanam\b", "பட்டணம்"), (r"\bCoimbatore\b", "கோயம்புத்தூர்"),
        (r"\bTamil Nadu\b", ""), (r"\bcents?\b", "சென்ட்"),
        (r"\bsq\.?\s*ft\.?\b|\bsqft\b", "சதுர அடி"), (r"\bft\b", "அடி"),
        (r"\bNorth\b", "வடக்கு"), (r"\bSouth\b", "தெற்கு"),
        (r"\bEast\b", "கிழக்கு"), (r"\bWest\b", "மேற்கு"),
        (r"\bPlot\b", "வீட்டு மனை"), (r"\bHouse\b", "தனி வீடு"),
        (r"\bVilla\b", "வில்லா"), (r"\bDTCP\b", "டி டி சி பி"),
        (r"\bwide tar roads?\b", "அகல தார் சாலைகள்"),
        (r"\bto\b", "முதல்"), (r"\band\b", "மற்றும்"),
    ]
    result = str(value)
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    result = re.sub(r"(\d+\s+சென்ட்)\s+முதல்\s+(\d+\s+சென்ட்)(?!\s+வரை)", r"\1 முதல் \2 வரை", result)
    result = result.replace("அருகில் துடியலூர்", "துடியலூர் அருகே")
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
        "text": f"கோயம்புத்தூரில், {location} ஏரியாவில் இருக்கும் இந்த {title} பற்றி பார்க்கலாம்.",
    }]
    fact_lines = [
        ("land", "land_area", "லேண்ட் ஏரியா, {value}."),
        ("builtUp", "built_up_area", "பில்ட் அப் ஏரியா, {value}."),
        ("price", "price", "விலை, {value}."),
        ("facing", "facing", "ஃபேசிங், {value}."),
        ("road", "road_width", "ரோடு வசதி, {value}."),
        ("approval", "approval", "அப்ரூவல், {value}."),
    ]
    for scene, key, sentence in fact_lines:
        value = _spoken(prop.get(key))
        if value:
            segments.append({"scene": scene, "text": sentence.format(value=_tamilize(value))})
    segments.extend([
        {"scene": "verify", "text": "லொக்கேஷன், அளவு, விலை, டாக்குமெண்ட்ஸ் எல்லாமே சைட் விசிட்டில் கிளியராக செக் பண்ணிக்கலாம்."},
        {"scene": "cta", "text": "மேலும் டீட்டெயில்ஸ் மற்றும் சைட் விசிட்டுக்கு, கோயம்புத்தூர் வீடு பில்டர்ஸை இப்பவே கால் பண்ணுங்க."},
    ])
    return segments


def build_tamil_script(job: dict) -> str:
    return " ".join(segment["text"] for segment in build_voice_segments(job))


def _parler_style() -> str:
    return os.environ.get("INDIC_PARLER_STYLE", "").strip() or DEFAULT_PARLER_STYLE


def _load_parler():
    global _PARLER_RUNTIME
    if _PARLER_RUNTIME is not None:
        return _PARLER_RUNTIME

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is required for the gated ai4bharat/indic-parler-tts model")

    import torch
    from parler_tts import ParlerTTSForConditionalGeneration
    from transformers import AutoTokenizer

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    model_kwargs = {"token": token, "low_cpu_mem_usage": True}
    if device.startswith("cuda"):
        model_kwargs["torch_dtype"] = torch.float16

    model = ParlerTTSForConditionalGeneration.from_pretrained(PARLER_MODEL, **model_kwargs).to(device)
    tokenizer = AutoTokenizer.from_pretrained(
        model.config.text_encoder._name_or_path, token=token
    )
    model.eval()
    _PARLER_RUNTIME = (torch, model, tokenizer, device)
    return _PARLER_RUNTIME


def _save_indic_parler(text: str, output: Path) -> None:
    import soundfile as sf

    torch, model, tokenizer, device = _load_parler()
    description = tokenizer(_parler_style(), return_tensors="pt").to(device)
    prompt = tokenizer(text, return_tensors="pt").to(device)

    # Stable per-line sampling keeps an autopilot rerender reproducible.
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)

    with torch.inference_mode():
        generated = model.generate(
            input_ids=description.input_ids,
            prompt_input_ids=prompt.input_ids,
            do_sample=True,
            temperature=1.0,
        )
    samples = generated.detach().cpu().float().numpy().squeeze()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        temp_wav = Path(handle.name)
    try:
        sf.write(temp_wav, samples, model.config.sampling_rate)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(temp_wav),
            "-codec:a", "libmp3lame", "-b:a", "192k", str(output),
        ], check=True)
    finally:
        temp_wav.unlink(missing_ok=True)


async def _save_edge(text: str, output: Path) -> None:
    import edge_tts

    communicator = edge_tts.Communicate(
        text, EDGE_VOICE, rate="+8%", pitch="-1Hz", volume="+8%"
    )
    await communicator.save(str(output))


def _save_voice(text: str, output: Path, engine: str | None = None) -> str:
    selected = (engine or os.environ.get("TTS_ENGINE", "edge")).strip().lower()
    if selected == "indic-parler":
        try:
            _save_indic_parler(text, output)
            return "indic-parler"
        except Exception:
            allow_fallback = os.environ.get("TTS_ALLOW_EDGE_FALLBACK", "false").lower() == "true"
            if not allow_fallback:
                raise
            print("WARNING: Indic Parler-TTS failed; using explicit Edge fallback.")
            asyncio.run(_save_edge(text, output))
            return "edge-fallback"
    if selected == "edge":
        asyncio.run(_save_edge(text, output))
        return "edge"
    raise ValueError(f"Unsupported TTS_ENGINE: {selected}")


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
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=5", "-codec:a", "libmp3lame",
        "-b:a", "192k", str(normalized),
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
        engine = _save_voice(segment["text"], output)
        _normalize(output)
        manifest.append({
            **segment,
            "file": output.name,
            "duration_seconds": round(_duration(output), 3),
            "tts_engine": engine,
            "voice_style": _parler_style() if engine == "indic-parler" else EDGE_VOICE,
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
