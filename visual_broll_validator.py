import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types


MODEL = os.environ.get("GEMINI_BROLL_MODEL", os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash"))
MIN_VISUAL_SCORE = int(os.environ.get("BROLL_VISUAL_MIN_SCORE", "72"))
MAX_BATCH_CLIPS = int(os.environ.get("BROLL_VISUAL_BATCH", "8"))

# These are visual failures, not merely ranking penalties. A clip with any of
# these traits is unsuitable for a credibility-first residential property Reel.
HARD_FLAG_FIELDS = (
    "people_dominant",
    "food_or_cooking",
    "flag_or_political_symbol",
    "religious",
    "commercial",
    "hotel_or_resort",
    "highway_or_heavy_traffic",
    "mountain_or_plantation",
    "non_residential",
)

SCENE_REQUIREMENTS = {
    "location": "quiet residential neighbourhood, independent houses, villa street, residential aerial or local approach road",
    "road": "residential street, layout road, paved local road or quiet villa approach road; not highway/flyover/arterial traffic",
    "land": "residential plot, vacant house site, plotted development or residential layout land",
    "exterior": "independent house, villa, residential facade, house entrance or residential exterior",
    "living": "residential living room interior; room itself must dominate the frame",
    "kitchen": "residential modular/home kitchen; cabinetry and room must dominate, not cooking/food/people",
    "bedroom": "residential bedroom interior; room itself must dominate the frame",
}


def _duration_seconds(path: Path) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return max(0.1, float(result.stdout.strip()))
    except Exception:
        return 6.0


def _extract_frames(path: Path, frame_dir: Path) -> list[Path]:
    duration = _duration_seconds(path)
    times = [max(0.15, duration * 0.25), max(0.3, duration * 0.72)]
    frames = []
    for index, second in enumerate(times, start=1):
        target = frame_dir / f"{path.stem}-{index}.jpg"
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{second:.3f}",
                    "-i", str(path), "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "4", str(target),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )
            if target.exists() and target.stat().st_size > 0:
                frames.append(target)
        except Exception:
            continue
    return frames


def _parse_json(text: str):
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start = min([pos for pos in (cleaned.find("["), cleaned.find("{")) if pos >= 0], default=-1)
    end = max(cleaned.rfind("]"), cleaned.rfind("}"))
    if start < 0 or end < start:
        raise ValueError("visual validator returned no JSON")
    return json.loads(cleaned[start:end + 1])


def _fallback(items: list[dict], reason: str) -> list[dict]:
    return [
        {
            **item,
            "visual_validated": False,
            "visual_validation_reason": reason,
            "visual_score": int(item.get("quality_score", 0) or 0),
        }
        for item in items
    ]


def _normalized_result(result: dict, item: dict, scene: str) -> dict:
    score = result.get("score", 0)
    try:
        score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        score = 0

    flags = {field: bool(result.get(field, False)) for field in HARD_FLAG_FIELDS}
    scene_match = str(result.get("scene_match", "")).strip().lower()
    scene_ok = bool(result.get("scene_ok", False)) and scene_match in {scene, "residential " + scene, "residential"}
    rejected_flags = [field for field, enabled in flags.items() if enabled]
    accepted = scene_ok and score >= MIN_VISUAL_SCORE and not rejected_flags

    return {
        **item,
        "visual_validated": True,
        "visual_score": score,
        "visual_scene_match": scene_match,
        "visual_scene_ok": scene_ok,
        "visual_reject_flags": rejected_flags,
        "visual_reason": str(result.get("reason", "")).strip()[:500],
        "visual_accepted": accepted,
    }


def validate_downloaded_clips(scene: str, items: list[dict]) -> list[dict]:
    """Inspect actual frames from downloaded stock clips using Gemini Vision.

    The function sends two representative frames per candidate in a single
    scene-level Gemini request, so a normal villa render needs only a handful
    of model calls instead of one call per clip.

    If GEMINI_API_KEY is absent, metadata ranking remains available as a safe
    compatibility fallback. If a key is configured but validation itself
    fails, the batch fails closed and the caller can fall back to cached/R2
    footage instead of silently accepting unverified stock.
    """
    if not items:
        return []
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _fallback(items, "gemini-key-not-configured")

    batch = items[:MAX_BATCH_CLIPS]
    with tempfile.TemporaryDirectory(prefix="broll-frames-") as temp_dir:
        frame_dir = Path(temp_dir)
        contents = []
        mapped = []
        for index, item in enumerate(batch, start=1):
            path = Path(str(item.get("local_file", "")))
            if not path.exists():
                continue
            frames = _extract_frames(path, frame_dir)
            if not frames:
                continue
            mapped.append((index, item))
            contents.append(f"CANDIDATE {index} provider={item.get('provider','')} metadata={item.get('title') or item.get('tags') or item.get('description') or ''}")
            for frame_number, frame in enumerate(frames, start=1):
                contents.append(f"CANDIDATE {index} FRAME {frame_number}")
                contents.append(types.Part.from_bytes(data=frame.read_bytes(), mime_type="image/jpeg"))

        if not mapped:
            return []

        requirement = SCENE_REQUIREMENTS.get(scene, "residential property footage matching the scene")
        prompt = f"""
You are a strict visual QA gate for a Coimbatore, Tamil Nadu residential real-estate Reel.
Target scene: {scene}
Acceptable visual: {requirement}

Inspect the ACTUAL frames for every candidate. Do not trust provider search terms or metadata if the pixels disagree.
Reject a candidate if ANY sampled frame is dominated by people, food/cooking, flags/political symbols, religion, hotel/resort, office/commercial activity, highway/flyover/heavy traffic, mountains/tea plantations/agriculture, tourism, or other non-residential content.
For kitchen/living/bedroom scenes, the ROOM must be the subject; a person cooking, holding an object, posing or eating is a rejection.
For location/road/exterior scenes, prefer ordinary South-Indian/Indian residential context. Do not claim an exact locality from appearance alone.

Return ONLY a JSON array with one object for each candidate index you received:
[
  {{
    "candidate": 1,
    "scene_match": "{scene}",
    "scene_ok": true,
    "score": 0,
    "people_dominant": false,
    "food_or_cooking": false,
    "flag_or_political_symbol": false,
    "religious": false,
    "commercial": false,
    "hotel_or_resort": false,
    "highway_or_heavy_traffic": false,
    "mountain_or_plantation": false,
    "non_residential": false,
    "reason": "short factual reason"
  }}
]
Score 90-100 only for an excellent direct scene match, 72-89 for a usable residential match, below 72 for weak/ambiguous footage.
"""
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=[prompt, *contents],
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                ),
            )
            parsed = _parse_json(response.text or "")
            if isinstance(parsed, dict):
                parsed = parsed.get("results", [])
            if not isinstance(parsed, list):
                raise ValueError("visual validator JSON was not a list")
            by_index = {}
            for result in parsed:
                if not isinstance(result, dict):
                    continue
                try:
                    by_index[int(result.get("candidate"))] = result
                except (TypeError, ValueError):
                    continue

            validated = []
            for index, item in mapped:
                result = by_index.get(index)
                if result is None:
                    # Key exists, so an omitted candidate is treated as unsafe.
                    result = {"candidate": index, "scene_match": "unknown", "scene_ok": False, "score": 0, "non_residential": True, "reason": "validator omitted candidate"}
                validated.append(_normalized_result(result, item, scene))
            return validated
        except Exception as error:
            print(f"Gemini visual B-roll validation failed for {scene!r}: {error}")
            # Fail closed when visual validation was explicitly configured.
            return [
                {
                    **item,
                    "visual_validated": True,
                    "visual_score": 0,
                    "visual_scene_match": "error",
                    "visual_scene_ok": False,
                    "visual_reject_flags": ["validation_error"],
                    "visual_reason": str(error)[:500],
                    "visual_accepted": False,
                }
                for _, item in mapped
            ]
