from __future__ import annotations

import base64
import io
import json
import os
import tempfile
from pathlib import Path
from urllib import request

ANALYSIS_INSTRUCTION = """Analyse these time-distributed frames from one public interior-design YouTube video.
Return valid JSON only. Record only visually supported facts and source metadata; never guess.
Required keys: trend_name, room_type, product_or_equipment, materials, colours, mechanism,
layout, lighting, styling, practical_benefit, limitations, verified_visual_facts, shot_subjects.
All values except shot_subjects and verified_visual_facts are short strings. The two list fields contain strings.
Ignore the presenter's identity, face, logos, subtitles and branding. If a detail is unclear, say not visually confirmed."""


def _gemini_visual_analysis(candidate: dict, frame_paths: list[Path]) -> dict:
    key = os.environ["GEMINI_API_KEY"]
    model = os.getenv("INTERIOR_GEMINI_MODEL", "gemini-2.5-flash")
    parts = [{"text": ANALYSIS_INSTRUCTION + "\nSOURCE METADATA:\n" + json.dumps(candidate, ensure_ascii=False)}]
    for path in frame_paths:
        parts.append({"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(path.read_bytes()).decode()}})
    payload = json.dumps({"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}).encode()
    req = request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        data=payload, headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=180) as response: result = json.loads(response.read())
    return json.loads(result["candidates"][0]["content"]["parts"][0]["text"])


def build_reference_prompt(candidate: dict, analysis: dict, config: dict) -> str:
    source = candidate["url"]
    facts = "; ".join(analysis.get("verified_visual_facts", [])) or "Use only the attached reference frames"
    subjects = analysis.get("shot_subjects", [])[:7]
    while len(subjects) < 7: subjects.append("another distinct visually verified detail from the same interior")
    brand = config.get("brand", "Olive Tree Interiors")
    contact = os.getenv("INTERIOR_CONTACT", "")
    contact_line = f"  |  ENQUIRY: {contact}" if contact else ""
    shots = []
    labels = ["ESTABLISHING VIEW", "PRODUCT OR DESIGN CONTEXT", "MATERIAL DETAIL", "MECHANISM OR FUNCTION", "PRACTICAL APPLICATION", "SECOND VERIFIED DETAIL", "FINAL REVEAL"]
    times = ["0 TO 1.4", "1.4 TO 2.8", "2.8 TO 4.2", "4.2 TO 5.6", "5.6 TO 7.0", "7.0 TO 8.5", "8.5 TO 10"]
    for i in range(7):
        shots.append(f"SHOT {i+1} — {times[i]} SECONDS — {labels[i]}\nHard cut to {subjects[i]}. Use a controlled professional smartphone-gimbal push-in, lateral slide or detail reveal appropriate to the reference. Preserve the same room, product geometry, materials, colours, scale and installation. Do not invent an unseen feature.")
    return f"""MANDATORY OUTPUT FORMAT LOCK — READ THIS FIRST
Generate a NATIVE PORTRAIT video only: vertical 9:16 aspect ratio, ideally 1080×1920 pixels. The frame must be taller than it is wide. Never generate landscape 16:9, horizontal video, square video, a rotated landscape frame, letterboxing, pillarboxing, or a landscape clip placed inside a portrait canvas. This format requirement overrides the orientation of every source or reference.

The linked YouTube reference and attached reference frames may be landscape. Use them only to understand the interior's real visual identity, then intelligently recompose every shot for a full-screen 9:16 portrait canvas. If native 9:16 output is unavailable, do not generate a landscape substitute; instruct the user to select Portrait/9:16 first.

REFERENCE-FIRST INSTRUCTION
Open and use this exact YouTube interior video as the visual reference before generating:
{source}

Also use all attached reference frames from that exact video. First analyse the source and attached images frame-by-frame. Base the reconstruction on the interior, equipment and design actually shown—not on a generic luxury interior or only on the written description. If the source and images cannot be visually analysed, do not generate a substitute; ask the user to retry the reference.

Identify only visually confirmed details: room type, layout, product or equipment, mechanism, cabinet geometry, materials, colours, handles, fittings, lighting, ceiling, walls, flooring, furniture, proportions and visible connections. Never copy or recreate the presenter, face, logo, captions or competitor branding. Never infer an unseen feature.

VERIFIED INTERIOR TREND INFORMATION
Source: {source}
Creator: {candidate.get('creator', 'Not specified')}
Trend/design: {analysis.get('trend_name', 'Visually verified interior idea')}
Room/application: {analysis.get('room_type', 'Not visually confirmed')}
Product/equipment: {analysis.get('product_or_equipment', 'Not visually confirmed')}
Materials: {analysis.get('materials', 'Not visually confirmed')}
Colours: {analysis.get('colours', 'Not visually confirmed')}
Mechanism/function: {analysis.get('mechanism', 'Not visually confirmed')}
Practical benefit: {analysis.get('practical_benefit', 'Not visually confirmed')}
Verified visual facts: {facts}

Generate one completely new, highly photorealistic, exactly 10-second vertical 9:16 interior source clip at 60 fps. It will be slowed to 33.3% speed in VN Editor to create a smooth 30-second final video. Do not reuse source frames directly. Reconstruct only the visually confirmed design identity. It must resemble genuine smartphone footage recorded with a professional gimbal inside a real occupied Indian home or working interior showroom—not an architectural render, showroom CGI, slideshow or AI-image animation.

Create seven clearly different but visually consistent shots of approximately 1.4 seconds each. Use clean hard cuts only. All shots must retain the same room, cabinetry, product, dimensions, materials, lighting and installation.

{chr(10).join(shots)}

OLIVE TREE INTERIORS FOOTER — 0.3 TO 10 SECONDS
Display one slim, professional, completely opaque lower-third continuously from 0.3 seconds until the clip ends. It must remain upright, sharp, stationary and identical across all seven shots. Use a premium deep-olive or charcoal background, high-contrast white text and one restrained warm-gold accent. Maximum height: 12% of the frame. No animation, bouncing, perspective tilt or oversized card. Display exactly:
“{brand.upper()}  |  REAL INTERIOR IDEAS{contact_line}”

AUDIO
Generate no voiceover, dialogue, music, footsteps or ambience. The 10-second source clip must be silent because it will be slowed to 33.3% in VN Editor. Add the original Tamil voiceover, music and sound effects only after slowing.

FIXED REALISM RULES
Exactly 10 seconds; native 60 fps; vertical 9:16; designed for smooth 3× slow motion; seven distinct shots; photorealistic smartphone-gimbal footage; preserve the verified reference identity; hard cuts; no invented rooms or mechanisms; no presenter or copied person; no competitor logos or text; no religious imagery; no impossible cabinet movement; no floating camera; no morphing geometry; no glossy CGI surfaces; no excessive cinematic haze; no perfect sterile render lighting; no speed ramps; no whip pans; no repeated shots; no rotating captions; no oversized graphics; no distorted doors, drawers, hardware or cabinets; no spelling errors; no third-party phone numbers.

Make the footage feel physically filmed: natural Indian daylight, subtle sensor noise, believable exposure changes, realistic material texture, stable straight lines, correct cabinet clearances, minor real-world variation and natural reflections. When unclear, exclude the feature. A simpler accurate reconstruction is preferable to an attractive invented design.

Disclosure for final edit or caption: “AI visual reconstruction inspired by a verified interior reference.”
"""


def _send_album(paths: list[Path], token: str, chat_id: str, source: str) -> None:
    import requests
    media, files, handles = [], {}, []
    try:
        for i, path in enumerate(paths[:5]):
            key = f"frame{i}"; handle = path.open("rb"); handles.append(handle)
            files[key] = (path.name, handle, "image/jpeg")
            item = {"type": "photo", "media": f"attach://{key}"}
            if i == 0: item["caption"] = "OLIVE TREE INTERIORS — REFERENCE FRAMES\nSave and attach all five images together in Gemini before pasting the prompt.\n" + source
            media.append(item)
        response = requests.post(f"https://api.telegram.org/bot{token}/sendMediaGroup", data={"chat_id": chat_id, "media": json.dumps(media)}, files=files, timeout=90)
        response.raise_for_status()
        if not response.json().get("ok"): raise RuntimeError(response.text)
    finally:
        for handle in handles: handle.close()


def _send_prompt(prompt: str, candidate: dict, token: str, chat_id: str) -> None:
    import requests
    payload = io.BytesIO(prompt.encode()); payload.name = f"interior-{candidate['video_id']}-gemini-prompt.txt"
    caption = "<b>Olive Tree Interiors — reference-first Gemini prompt</b>\nAttach the five images sent above, paste this prompt, select Portrait/9:16, and generate the 10-second silent source clip."
    response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}, files={"document": (payload.name, payload, "text/plain")}, timeout=90)
    response.raise_for_status()
    if not response.json().get("ok"): raise RuntimeError(response.text)


def run(candidates_path: str, config_path: str, output_path: str, deliver: bool) -> dict:
    from reference_frames import extract_reference_frames
    discovery = json.loads(Path(candidates_path).read_text()); config = json.loads(Path(config_path).read_text())
    candidates = discovery.get("candidates", [])
    if not candidates: raise ValueError("No interior candidates found")
    candidate = candidates[0]
    with tempfile.TemporaryDirectory(prefix="interior-reference-") as temp:
        frames = extract_reference_frames({"source_url": candidate["url"]}, Path(temp), target_count=5)
        analysis = _gemini_visual_analysis(candidate, frames)
        prompt = build_reference_prompt(candidate, analysis, config)
        result = {"candidate": candidate, "visual_analysis": analysis, "gemini_prompt": prompt, "reference_frame_count": len(frames)}
        Path(output_path).parent.mkdir(parents=True, exist_ok=True); Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2))
        if deliver:
            token = os.environ["TELEGRAM_BOT_TOKEN"]; chat_id = os.environ["TELEGRAM_CHAT_ID"]
            _send_album(frames, token, chat_id, candidate["url"]); _send_prompt(prompt, candidate, token, chat_id)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("candidates"); parser.add_argument("config"); parser.add_argument("output"); parser.add_argument("--deliver", action="store_true")
    args = parser.parse_args(); run(args.candidates, args.config, args.output, args.deliver)
