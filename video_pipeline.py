import json
from pathlib import Path

from develop_property_script import develop_property_script


JOBS = Path("data/video_jobs")
APPROVALS = Path("data/approved_video_ids.txt")
MISSING = {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def _present(value) -> bool:
    return str(value or "").strip().upper() not in MISSING


def automatic_approval_ready(property_data: dict) -> bool:
    """Approve only listings with a property type and at least two usable facts.

    `main.py` already limits this function to Gemini-classified property listings
    that match a configured Coimbatore locality. This final gate prevents sparse
    or ambiguous records from reaching the renderer automatically.
    """
    if not _present(property_data.get("property_type")):
        return False
    fact_keys = ("land_area", "built_up_area", "price", "facing", "road_width", "approval")
    usable_facts = sum(_present(property_data.get(key)) for key in fact_keys)
    return usable_facts >= 2 and bool(property_data.get("source_facts"))


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
    auto_approved = automatic_approval_ready(property_data)
    content_plan = develop_property_script(property_data, location)
    job = {
        "video_id": video["video_id"],
        "source_url": video["url"],
        "property_location": property_data.get("location", "NOT SPECIFIED"),
        "property": {
            key: property_data.get(key, "NOT SPECIFIED")
            for key in (
                "property_type", "bhk", "land_area", "built_up_area", "price",
                "facing", "road_width", "parking", "approval"
            )
        },
        "verified_facts": facts,
        "content_plan": content_plan,
        "disclosure": "Representative locality/property visuals; verify the actual property before purchase.",
        "aspect_ratio": "9:16",
        "render_engine": "remotion-professional-free",
        "required_owned_images_folder": f"assets/properties/{video['video_id']}/",
        "optional_owned_audio": f"assets/audio/{video['video_id']}.mp3",
        "scenes": scenes,
        "status": "auto_approved" if auto_approved else "needs_review",
        "approval_mode": "automatic_fact_gate_v1",
    }
    JOBS.mkdir(parents=True, exist_ok=True)
    path = JOBS / f"{video['video_id']}.json"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def approved_ids() -> set[str]:
    if not APPROVALS.exists():
        return set()
    return {line.strip() for line in APPROVALS.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}
