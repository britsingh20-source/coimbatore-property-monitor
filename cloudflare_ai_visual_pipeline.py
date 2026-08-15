"""Cloudflare Workers AI primary image backend for the property visual pipeline."""

import base64
import io
import json
import os
import re
from pathlib import Path

import requests
from PIL import Image, ImageFilter

import ai_visual_pipeline as base


CLOUDFLARE_MODEL = os.environ.get(
    "CLOUDFLARE_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell"
).strip() or "@cf/black-forest-labs/flux-1-schnell"
CLOUDFLARE_API_BASE = "https://api.cloudflare.com/client/v4"
ORIGINAL_GENERATE_STILL = base.generate_still


def _credentials() -> tuple[str, str]:
    account_id = (
        os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        or os.environ.get("R2_ACCOUNT_ID", "").strip()
    )
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    return account_id, token


def _portrait_jpeg(image_bytes: bytes, destination: Path) -> None:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    canvas_size = (768, 1344)

    background = image.copy()
    scale = max(canvas_size[0] / background.width, canvas_size[1] / background.height)
    background = background.resize(
        (max(1, int(background.width * scale)), max(1, int(background.height * scale))),
        Image.Resampling.LANCZOS,
    )
    left = (background.width - canvas_size[0]) // 2
    top = (background.height - canvas_size[1]) // 2
    background = background.crop((left, top, left + canvas_size[0], top + canvas_size[1]))
    background = background.filter(ImageFilter.GaussianBlur(radius=28))

    foreground = image.copy()
    foreground.thumbnail((768, 1120), Image.Resampling.LANCZOS)
    x = (canvas_size[0] - foreground.width) // 2
    y = (canvas_size[1] - foreground.height) // 2
    background.paste(foreground, (x, y))

    destination.parent.mkdir(parents=True, exist_ok=True)
    background.save(destination, "JPEG", quality=94, optimize=True)
    if destination.stat().st_size < 50_000:
        raise RuntimeError(f"Cloudflare image is suspiciously small: {destination.stat().st_size} bytes")


def _extract_context(prompt: str) -> tuple[str, str, str]:
    first = re.search(r"visual for a (.+?) in (.+?), Coimbatore", prompt, flags=re.I)
    title = first.group(1).strip() if first else "compact residential property"
    locality = first.group(2).strip() if first else "Coimbatore"
    area_match = re.search(r"built-up size is ([^;]+)", prompt, flags=re.I)
    area = area_match.group(1).strip() if area_match else "compact realistic size"
    return title, locality, area


def _cloudflare_prompt(prompt: str, destination: Path) -> str:
    """Use short, scene-first prompts because FLUX schnell overweights long shared prefixes."""
    scene = destination.parent.name.lower()
    title, locality, area = _extract_context(prompt)
    common = (
        f"Property context: {title}, {area}, {locality}, Coimbatore, Tamil Nadu, India. "
        "Photorealistic, realistic South Indian proportions, natural tropical daylight, vertical property-ad composition. "
        "No people, text, logo, watermark, religious building, fantasy geometry, foreign suburban style or impossible structures. "
        "Representative AI visual only, not the actual listing."
    )
    scene_prompts = {
        "exterior": (
            "EXTERIOR BUILDING ONLY. Show one coherent mid-rise Coimbatore apartment building, ground/stilt plus 3 to 5 floors, "
            "entirely behind the road edge, practical compound gate, realistic parking, aligned balconies and normal structural columns. "
            "Do not show an interior room. "
        ),
        "location": (
            f"LOCATION STREET ONLY. Show a realistic {locality} residential neighbourhood with an unobstructed local tar road, "
            "modest apartments and independent houses only on both sides, utility poles, compound walls and tropical greenery. "
            "Do not show an interior room. "
        ),
        "road": (
            "ACCESS ROAD ONLY. The road must be the main subject: a believable Coimbatore residential road, continuous and usable, "
            "with modest buildings safely set back on both sides, utility poles and greenery. No highway or flyover. "
        ),
        "living": (
            f"INTERIOR LIVING ROOM ONLY. Show a compact furnished Indian apartment living room appropriate to {area}. "
            "Include a practical 2-3 seat sofa, TV wall, vitrified floor, simple warm laminate details and believable walking clearance. "
            "Absolutely no building exterior, facade, street, road or outdoor house view as the main subject. "
        ),
        "kitchen": (
            f"INTERIOR KITCHEN ONLY. Show a compact practical Indian modular kitchen appropriate to {area}. "
            "Use a straight or small L-shaped counter, upper and base cabinets, chimney, tiled backsplash, sink and realistic appliance clearance. "
            "Absolutely no building exterior, facade, street or house front. No oversized island. "
        ),
        "bedroom": (
            f"INTERIOR BEDROOM ONLY. Show a compact furnished Indian apartment bedroom appropriate to {area}. "
            "Include one realistic cot, practical wardrobe, one small side table, simple curtains and believable walking clearance. "
            "Absolutely no building exterior, facade, road or street as the main subject. "
        ),
    }
    return (scene_prompts.get(scene, "REALISTIC RESIDENTIAL PROPERTY SCENE. ") + common)[:1800]


def generate_still_cloudflare(prompt: str, destination: Path, seed: int) -> None:
    account_id, token = _credentials()
    if not account_id or not token:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID/R2_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required")

    url = f"{CLOUDFLARE_API_BASE}/accounts/{account_id}/ai/run/{CLOUDFLARE_MODEL}"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "prompt": _cloudflare_prompt(prompt, destination),
            "steps": 4,
        },
        timeout=180,
    )

    if response.status_code >= 400:
        detail = response.text[:700].replace("\n", " ")
        raise RuntimeError(f"Cloudflare Workers AI request failed ({response.status_code}): {detail}")

    try:
        payload = response.json()
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Cloudflare Workers AI returned non-JSON: {response.headers.get('content-type')}") from error

    if not payload.get("success", False):
        raise RuntimeError(f"Cloudflare Workers AI error: {json.dumps(payload.get('errors') or payload)[:700]}")

    result = payload.get("result") or {}
    image_b64 = result.get("image") if isinstance(result, dict) else None
    if not image_b64:
        raise RuntimeError("Cloudflare Workers AI response did not contain result.image")

    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception as error:
        raise RuntimeError("Cloudflare Workers AI returned invalid base64 image data") from error

    _portrait_jpeg(image_bytes, destination)


def generate_still(prompt: str, destination: Path, seed: int) -> str:
    account_id, token = _credentials()
    errors: list[str] = []

    if account_id and token:
        try:
            generate_still_cloudflare(prompt, destination, seed)
            return f"cloudflare:{CLOUDFLARE_MODEL}"
        except Exception as error:
            errors.append(f"Cloudflare: {error}")

    try:
        return ORIGINAL_GENERATE_STILL(prompt, destination, seed)
    except Exception as error:
        errors.append(str(error))

    if not account_id or not token:
        errors.insert(0, "Cloudflare credentials not configured")
    raise RuntimeError("; ".join(errors))


def generate_for_job(job: dict, max_animated: int = base.DEFAULT_ANIMATED) -> dict:
    previous = base.generate_still
    base.generate_still = generate_still
    try:
        manifest = base.generate_for_job(job, max_animated)
        manifest["image_backend_preference"] = "cloudflare-first"
        manifest["cloudflare_image_model"] = CLOUDFLARE_MODEL
        manifest_path = Path(base.ROOT) / str(job["video_id"]) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest
    finally:
        base.generate_still = previous


def main() -> None:
    previous = base.generate_still
    base.generate_still = generate_still
    try:
        base.main()
    finally:
        base.generate_still = previous


if __name__ == "__main__":
    main()
