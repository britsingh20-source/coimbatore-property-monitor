import json
import os
import re
from typing import Any

from google import genai


MODEL = os.environ.get("GEMINI_SCRIPT_MODEL", os.environ.get("GEMINI_ANALYSIS_MODEL", "gemini-3.6-flash"))
ALLOWED_SCENES = ("location", "land", "builtUp", "price", "facing", "road", "approval", "verify", "cta")
ALLOWED_BROLL = ("exterior", "road", "land", "living_room", "kitchen", "bedroom", "interior")


def _present(value: Any) -> bool:
    return str(value or "").strip().upper() not in {"", "NOT SPECIFIED", "UNKNOWN", "N/A", "NONE"}


def _parse_json(text: str) -> dict:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Script director response did not contain JSON")
    return json.loads(cleaned[start:end + 1])


def _digits(value: Any) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", json.dumps(value, ensure_ascii=False)))


def _fallback_plan(property_data: dict, location: dict) -> dict:
    locality = (location.get("matched_localities") or [property_data.get("location") or "கோயம்புத்தூர்"])[0]
    ptype = property_data.get("property_type") if _present(property_data.get("property_type")) else "வீடு"
    bhk = property_data.get("bhk") if _present(property_data.get("bhk")) else ""
    title = " ".join(str(x) for x in (bhk, ptype) if _present(x)).strip()

    scenes = [{
        "name": "location",
        "voice": f"{locality} சைட்ல {title} தேடிட்டு இருந்தீங்கனா இந்த ப்ராப்பர்ட்டியை பாருங்க. நல்ல ரெசிடென்ஷியல் லொக்கேஷன்ல இருக்கு.",
        "broll": ["exterior", "road"],
        "avoid_broll": ["bedroom", "kitchen"],
        "vfx": "location-pin",
        "purpose": "hook",
    }]
    mapping = [
        ("price", "price", "இதோட கேட்குற விலை {value}.", ["exterior", "living_room"], "price-reveal"),
        ("land", "land_area", "மொத்தம் {value} லேண்ட் கிடைக்குது.", ["land", "exterior"], "plot-boundary"),
        ("builtUp", "built_up_area", "பில்ட் அப் பாத்தீங்கனா {value} இருக்கு.", ["living_room", "kitchen", "bedroom"], "builtup-lines"),
        ("road", "road_width", "இதுல முக்கியமான விஷயம், முன்னாடி {value} ரோடு வசதி இருக்கு.", ["road"], "road-measure"),
        ("facing", "facing", "வீடு {value} ஃபேசிங்.", ["exterior", "land"], "compass"),
        ("approval", "approval", "அப்ரூவல் பாத்தீங்கனா {value} இருக்கு.", ["exterior"], "approval-seal"),
    ]
    for scene, key, template, broll, vfx in mapping:
        if _present(property_data.get(key)):
            scenes.append({
                "name": scene,
                "voice": template.format(value=property_data[key]),
                "broll": broll,
                "avoid_broll": [],
                "vfx": vfx,
                "purpose": "fact",
            })
    scenes.extend([
        {
            "name": "verify",
            "voice": "லொக்கேஷன், அளவு, விலை, டாக்குமெண்ட்ஸ் எல்லாத்தையும் சைட் விசிட்டுக்கு வரும்போது நாம கிளியரா செக் பண்ணிக்கலாம்.",
            "broll": ["exterior", "living_room", "kitchen", "bedroom"],
            "avoid_broll": ["road"],
            "vfx": "verify-checklist",
            "purpose": "trust",
        },
        {
            "name": "cta",
            "voice": "இந்த ப்ராப்பர்ட்டி பிடிச்சிருந்தா டீட்டெயில்ஸ் மற்றும் சைட் விசிட்டுக்கு கோயம்புத்தூர் வீடு பில்டர்ஸ்க்கு கால் பண்ணுங்க.",
            "broll": ["exterior", "living_room"],
            "avoid_broll": [],
            "vfx": "cta",
            "purpose": "cta",
        },
    ])
    return {
        "version": "content-director-v1-fallback",
        "target_duration_seconds": 40,
        "style": "natural conversational Coimbatore Tamil property presenter",
        "hook_strategy": "strongest verified fact plus locality",
        "scenes": scenes,
    }


def _validate_plan(plan: dict, property_data: dict) -> dict:
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Content plan has no scenes")

    source_digits = _digits(property_data)
    seen = set()
    validated = []
    for item in scenes:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        voice = str(item.get("voice", "")).strip()
        if name not in ALLOWED_SCENES or not voice or name in seen:
            continue
        extra_digits = _digits(voice) - source_digits
        if extra_digits:
            raise ValueError(f"Script invented numeric facts in {name}: {sorted(extra_digits)}")
        broll = [str(x) for x in item.get("broll", []) if str(x) in ALLOWED_BROLL]
        avoid = [str(x) for x in item.get("avoid_broll", []) if str(x) in ALLOWED_BROLL]
        validated.append({
            "name": name,
            "voice": voice,
            "broll": broll or ["exterior"],
            "avoid_broll": avoid,
            "vfx": str(item.get("vfx", "")).strip(),
            "purpose": str(item.get("purpose", "fact")).strip(),
        })
        seen.add(name)

    if not validated or validated[0]["name"] != "location":
        raise ValueError("Content plan must begin with a location/hook scene")
    if "cta" not in seen:
        raise ValueError("Content plan is missing CTA")
    plan["scenes"] = validated
    plan["target_duration_seconds"] = max(30, min(45, int(plan.get("target_duration_seconds", 40))))
    plan["version"] = "content-director-v1"
    return plan


def develop_property_script(property_data: dict, location: dict) -> dict:
    """Turn extracted facts into a natural spoken-Tamil reel plan without inventing facts."""
    fallback = _fallback_plan(property_data, location)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return fallback

    locality = (location.get("matched_localities") or [property_data.get("location", "Coimbatore")])[0]
    verified = {
        key: property_data.get(key, "NOT SPECIFIED")
        for key in (
            "location", "property_type", "bhk", "land_area", "built_up_area", "price",
            "facing", "road_width", "parking", "approval", "amenities", "nearby_landmarks",
            "source_facts",
        )
    }
    prompt = f"""
You are the content director for a high-retention Tamil real-estate Reel in Coimbatore.
Develop the extracted property facts into a NATURAL SPOKEN TAMIL presentation. Do not merely read fields.

Hard rules:
- Never invent or infer a fact, number, amenity, landmark, approval, distance, road width or property feature.
- Use only the VERIFIED INPUT below. If a field is NOT SPECIFIED, do not mention it.
- Keep common real-estate words naturally mixed in Tamil speech: location, built-up, facing, road, approval, site visit, details.
- Sound like a relaxed local property presenter speaking to camera, not a formal announcer and not a database.
- Short conversational sentences. Natural connectors such as "பாத்தீங்கனா", "இதுல முக்கியமான விஷயம்", "அதே மாதிரி" may be used sparingly.
- Build a strong first 3-second hook from the best VERIFIED selling point. Do not use fake urgency or superlatives.
- Reorder facts for retention instead of following database field order.
- Target 35-45 seconds total.
- Every narration scene MUST include visual direction so footage exactly matches what is being spoken.
- Use canonical scene names only: location, land, builtUp, price, facing, road, approval, verify, cta.
- Start with location. End with cta. Include only factual scenes whose facts exist.
- B-roll categories may only be: exterior, road, land, living_room, kitchen, bedroom, interior.
- road narration should prefer road footage only.
- builtUp should prefer living_room/kitchen/bedroom/interior.
- facing should prefer exterior/land.
- Do not request religious visuals, tea estates, mountains, generic offices or unrelated stock footage.
- Keep the CTA simple: call for details/site visit. Do not invent offers.

Return JSON only with this shape:
{{
  "target_duration_seconds": 40,
  "style": "...",
  "hook_strategy": "...",
  "scenes": [
    {{
      "name": "location",
      "voice": "spoken Tamil sentence",
      "broll": ["exterior", "road"],
      "avoid_broll": ["bedroom"],
      "vfx": "location-pin",
      "purpose": "hook"
    }}
  ]
}}

Locality: {locality}
VERIFIED INPUT:
{json.dumps(verified, ensure_ascii=False, indent=2)}
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return _validate_plan(_parse_json(response.text), property_data)
    except Exception as error:
        fallback["director_error"] = str(error)[:500]
        return fallback
