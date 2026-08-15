"""Cloudflare Workers AI primary image backend for the property visual pipeline.

This module wraps ai_visual_pipeline without duplicating the property prompt logic.
Cloudflare FLUX.1-schnell is tried first. Existing Pollinations/Hugging Face
backends remain secondary fallbacks inside ai_visual_pipeline.
"""

import base64
import io
import json
import os
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
    """Keep the complete generated image while packaging it as a 9:16 JPEG.

    FLUX.1-schnell on Workers AI currently exposes prompt/steps rather than a
    reliable portrait-size parameter. We therefore avoid destructive cropping:
    a blurred copy fills the portrait canvas and the complete generated frame is
    fitted on top. This can be replaced later if Cloudflare exposes portrait
    dimensions for the model.
    """
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
            "prompt": prompt[:2048],
            "steps": 4,
            "seed": int(seed),
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
    """Cloudflare first, then the existing Pollinations/HF chain."""
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
