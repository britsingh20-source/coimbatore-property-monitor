from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib import request


SYSTEM = """You are an interior-reel creative strategist for a Coimbatore interior company.
Study the supplied public competitor references only to learn trends, structure and filming techniques.
Never copy sentences, logos, people, footage, project claims, floor plans or a creator's distinctive branding.
Return valid JSON only with: trend_name, why_it_works, audience_problem, hook_formula,
shot_pattern (array), camera_ideas (array), edit_ideas (array), material_or_design_ideas (array),
original_tamil_english_script, google_video_prompts (array of exactly 4 prompts),
caption, cover_text, hashtags (array), source_urls (array), confidence, limitations.
The script must be original, useful, conversational Tamil-English, 25-35 seconds, and end with a soft CTA.
Each Google video prompt must create a separate 9:16 photorealistic Indian interior clip, 6-8 seconds,
with consistent warm-modern styling, realistic carpentry dimensions, no logo, no text, no watermark, no people.
Use only observations supported by title/description/URL metadata; state limitations clearly."""


def _fallback(items: list[dict], config: dict) -> dict:
    topic = (items[0].get("title") if items else "space-saving interior") or "space-saving interior"
    return {
        "trend_name": topic, "why_it_works": "Fast problem-to-solution reveal with practical value.",
        "audience_problem": "Homeowners want attractive interiors without wasting usable space.",
        "hook_formula": "Show the common mistake, then reveal one practical upgrade.",
        "shot_pattern": ["problem close-up", "wide before view", "detail transformation", "finished reveal"],
        "camera_ideas": ["slow vertical push-in", "cabinet-detail macro", "wide corner reveal"],
        "edit_ideas": ["cut on cabinet movement", "before/after match cut", "minimal callout captions"],
        "material_or_design_ideas": ["warm wood laminate", "soft neutral palette", "concealed storage"],
        "original_tamil_english_script": "Interior beautiful-aa irundha mattum podhaadhu; daily use easy-aa irukkanum. Indha space-la open shelves-ku badhila concealed storage, warm wood finish, and clean lighting use pannina clutter kammi, movement easy. Ungal veetukku design pannumbodhu look-um function-um rendu equal-aa plan pannunga. More practical interior ideas-ku follow pannunga.",
        "google_video_prompts": [
            "9:16 photorealistic Indian apartment living room, cluttered open shelving shown as a design problem, slow cinematic push-in, natural daylight, realistic scale, no people, no text, no logo, 7 seconds",
            "9:16 photorealistic warm-modern Coimbatore apartment living room before redesign, neutral walls and empty TV wall, smooth wide corner pan, realistic Indian proportions, no people, no text, no logo, 7 seconds",
            "9:16 macro cinematic detail of concealed soft-close storage and warm wood laminate cabinetry opening smoothly, premium realistic carpentry, soft LED lighting, no hands, no text, no logo, 7 seconds",
            "9:16 final reveal of the same warm-modern Indian living room with concealed storage, clean circulation and layered lighting, slow pull-back, photorealistic, no people, no text, no logo, 7 seconds"
        ],
        "caption": "Beautiful interiors should also make everyday life easier. Save this practical design idea.",
        "cover_text": "LOOK + FUNCTION", "hashtags": ["#CoimbatoreInteriors", "#InteriorDesignTamil", "#SBInteriors", "#HomeInteriors"],
        "source_urls": [x["url"] for x in items[:3]], "confidence": "low", "limitations": "Metadata-only fallback; visual content was not inspected because Gemini was unavailable."
    }


def _gemini(items: list[dict], config: dict, api_key: str) -> dict:
    model = os.getenv("INTERIOR_GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    references = [{k: x.get(k, "") for k in ("url", "title", "description", "creator", "published_at", "query")} for x in items[:5]]
    prompt = SYSTEM + "\n\nBRAND CONFIG:\n" + json.dumps(config, ensure_ascii=False) + "\n\nREFERENCES:\n" + json.dumps(references, ensure_ascii=False)
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.5}}).encode()
    req = request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=120) as response: data = json.loads(response.read())
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(re.sub(r"^```json|```$", "", text.strip(), flags=re.MULTILINE).strip())


def analyze(candidates_path: str, config_path: str, output_path: str) -> dict:
    discovery = json.loads(Path(candidates_path).read_text(encoding="utf-8")); config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    items = discovery.get("candidates", [])
    if not items: raise ValueError("No interior candidates found. Add channel IDs/manual URLs or configure YOUTUBE_API_KEY.")
    key = os.getenv("GEMINI_API_KEY", "")
    try: result = _gemini(items, config, key) if key else _fallback(items, config)
    except Exception as exc:
        result = _fallback(items, config); result["limitations"] += f" Gemini error: {type(exc).__name__}."
    result["brand"] = config["brand"]
    result["contact"] = os.getenv("INTERIOR_CONTACT", config.get("contact", ""))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    import sys
    analyze(sys.argv[1], sys.argv[2], sys.argv[3])
