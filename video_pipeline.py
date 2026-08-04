import json
import os
import subprocess
import time
from pathlib import Path

from google import genai
from google.genai import types


JOBS = Path("data/video_jobs")
OUTPUTS = Path("outputs")
APPROVALS = Path("data/approved_video_ids.txt")


def build_video_job(video: dict, property_data: dict, location: dict) -> Path:
    locality = (location.get("matched_localities") or [property_data.get("location", "Coimbatore")])[0]
    facts = ", ".join(str(x) for x in property_data.get("source_facts", [])[:8])
    base = (
        f"Photorealistic contemporary residential property in {locality}, Coimbatore, Tamil Nadu. "
        f"Architecture consistent with: {property_data.get('exterior_description', 'the verified listing facts')}. "
        f"Neighbourhood: {property_data.get('neighbourhood_description', 'a realistic Coimbatore residential street')}. "
        "Natural tropical daylight, accurate Indian road scale, realistic materials, cinematic property marketing, "
        "no logos, no visible phone numbers, no misleading text, vertical composition."
    )
    scenes = [
        {"name": "street", "prompt": base + " Smooth establishing gimbal shot from the approach road, ambient city sounds."},
        {"name": "exterior", "prompt": base + " Slow premium reveal of the front elevation and parking, realistic shadows."},
        {"name": "living", "prompt": base + " Interior walkthrough of a bright Indian living room matching the property type."},
        {"name": "kitchen", "prompt": base + " Smooth walkthrough of a practical premium modular kitchen and dining space."},
    ]
    job = {
        "video_id": video["video_id"],
        "source_url": video["url"],
        "property_location": property_data.get("location", "NOT SPECIFIED"),
        "verified_facts": facts,
        "disclosure": "AI visualisation based on listing facts; not actual property footage.",
        "aspect_ratio": "9:16",
        "model": os.environ.get("GEMINI_VIDEO_MODEL", "veo-3.1-generate-preview"),
        "reference_images": [],
        "scenes": scenes,
        "status": "approval_pending",
    }
    JOBS.mkdir(parents=True, exist_ok=True)
    path = JOBS / f"{video['video_id']}.json"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def approved_ids() -> set[str]:
    if not APPROVALS.exists():
        return set()
    return {line.strip() for line in APPROVALS.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}


def generate_job(path: Path) -> Path:
    job = json.loads(path.read_text(encoding="utf-8"))
    if job["video_id"] not in approved_ids():
        raise PermissionError(f"{job['video_id']} is not listed in {APPROVALS}")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    output_dir = OUTPUTS / job["video_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    for index, scene in enumerate(job["scenes"], start=1):
        # Separate clips share the same design description. For stronger visual
        # consistency, add owned reference images to the job in a future review.
        operation = client.models.generate_videos(
            model=job["model"],
            prompt=scene["prompt"],
            config=types.GenerateVideosConfig(aspect_ratio="9:16", duration_seconds=8),
        )
        while not operation.done:
            time.sleep(10)
            operation = client.operations.get(operation)
        generated = operation.response.generated_videos[0]
        client.files.download(file=generated.video)
        clip = output_dir / f"{index:02d}-{scene['name']}.mp4"
        generated.video.save(str(clip))
        clips.append(clip)

    concat = output_dir / "clips.txt"
    concat.write_text("".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8")
    final = output_dir / "final-vertical.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c", "copy", str(final),
    ], check=True)
    job["status"] = "generated_pending_human_review"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return final
