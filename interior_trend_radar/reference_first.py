from __future__ import annotations

import io
import json
import os
from pathlib import Path


def build_reference_prompt(candidate: dict, analysis: dict, config: dict) -> str:
    source = candidate["url"]
    source_title = candidate.get("title", "Interior reference video")
    source_description = candidate.get("description", "") or "No written description supplied — rely on the linked video"
    brand = config.get("brand", "Olive Tree Interiors")
    contact = os.getenv("INTERIOR_CONTACT", "")
    contact_line = f"  |  ENQUIRY: {contact}" if contact else ""
    shots = []
    labels = ["ESTABLISHING VIEW", "PRODUCT OR DESIGN CONTEXT", "MATERIAL DETAIL", "MECHANISM OR FUNCTION", "PRACTICAL APPLICATION", "SECOND VERIFIED DETAIL", "FINAL REVEAL"]
    times = ["0 TO 1.4", "1.4 TO 2.8", "2.8 TO 4.2", "4.2 TO 5.6", "5.6 TO 7.0", "7.0 TO 8.5", "8.5 TO 10"]
    instructions = [
        "the strongest verified wide view of the real room or installation shown in the source",
        "the new product, equipment or design idea in its verified room context",
        "a close verified material, hardware, finish or construction detail",
        "the real mechanism, opening movement or functional demonstration only if visible",
        "the verified practical use of the design inside the same room",
        "a second distinct verified feature that has not appeared earlier",
        "the strongest final verified reveal of the same design or equipment",
    ]
    for i in range(7):
        shots.append(f"SHOT {i+1} — {times[i]} SECONDS — {labels[i]}\nHard cut to {instructions[i]}. Use a controlled professional smartphone-gimbal push-in, lateral slide or detail reveal appropriate to the source. Preserve the same room, product geometry, materials, colours, scale and installation. If this subject is not visible in the reference, substitute a different visually verified detail; never invent it.")
    return f"""MANDATORY OUTPUT FORMAT LOCK — READ THIS FIRST
Generate a NATIVE PORTRAIT video only: vertical 9:16 aspect ratio, ideally 1080×1920 pixels. The frame must be taller than it is wide. Never generate landscape 16:9, horizontal video, square video, a rotated landscape frame, letterboxing, pillarboxing, or a landscape clip placed inside a portrait canvas. This format requirement overrides the orientation of every source or reference.

The linked YouTube reference may be landscape. Use it only to understand the interior's real visual identity, then intelligently recompose every shot for a full-screen 9:16 portrait canvas. If native 9:16 output is unavailable, do not generate a landscape substitute; instruct the user to select Portrait/9:16 first.

REFERENCE-FIRST INSTRUCTION
Open and use this exact YouTube interior video as the visual reference before generating:
{source}

First open and analyse that linked YouTube interior video frame-by-frame. Base the reconstruction on the interior, equipment and design actually shown—not on a generic luxury interior or only on the written description. If the link cannot be opened or visually analysed, do not generate a substitute; ask the user to retry the reference.

Identify only visually confirmed details: room type, layout, product or equipment, mechanism, cabinet geometry, materials, colours, handles, fittings, lighting, ceiling, walls, flooring, furniture, proportions and visible connections. Never copy or recreate the presenter, face, logo, captions or competitor branding. Never infer an unseen feature.

VERIFIED INTERIOR TREND INFORMATION
Source: {source}
Creator: {candidate.get('creator', 'Not specified')}
Source title: {source_title}
Source description: {source_description}
Reference requirement: Gemini must determine the actual room, new product/equipment, materials, colours, mechanism, layout and practical benefit directly from the linked video. Treat the title and description only as supporting context. Do not display any unverified claim in the generated video.

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


def _send_prompt(prompt: str, candidate: dict, token: str, chat_id: str, position: int, total: int) -> None:
    import requests
    payload = io.BytesIO(prompt.encode()); payload.name = f"interior-{candidate['video_id']}-gemini-prompt.txt"
    caption = f"<b>Olive Tree Interiors — daily prompt {position}/{total}</b>\n<b>Source:</b> {candidate.get('creator', 'Interior channel')}\nNo image attachment is required. Paste this prompt in Gemini, allow it to open the included YouTube link, select Portrait/9:16, and generate the 10-second silent source clip."
    response = requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}, files={"document": (payload.name, payload, "text/plain")}, timeout=90)
    response.raise_for_status()
    if not response.json().get("ok"): raise RuntimeError(response.text)


def _load_state(path: Path) -> dict:
    if not path.exists(): return {"used_video_ids": [], "history": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _select_daily(candidates: list[dict], config: dict, state: dict) -> list[dict]:
    used = set(state.get("used_video_ids", [])); selected = []
    limit = int(config.get("daily_prompt_limit", 5))
    for channel in config.get("monitored_youtube_channels", []):
        name = channel.get("name", "")
        match = next((item for item in candidates if item.get("creator") == name and item.get("video_id") not in used), None)
        if match: selected.append(match)
        if len(selected) >= limit: break
    return selected


def run(candidates_path: str, config_path: str, output_path: str, deliver: bool, state_path: str = "data/interior_trend_state.json") -> dict:
    discovery = json.loads(Path(candidates_path).read_text()); config = json.loads(Path(config_path).read_text())
    candidates = discovery.get("candidates", [])
    if not candidates: raise ValueError("No interior candidates found")
    state_file = Path(state_path); state = _load_state(state_file)
    selected = _select_daily(candidates, config, state)
    jobs = [{"candidate": candidate, "gemini_prompt": build_reference_prompt(candidate, {}, config)} for candidate in selected]
    result = {"jobs": jobs, "prompt_count": len(jobs), "reference_mode": "youtube_url_only"}
    Path(output_path).parent.mkdir(parents=True, exist_ok=True); Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    if deliver and jobs:
        token = os.environ["TELEGRAM_BOT_TOKEN"]; chat_id = os.environ["TELEGRAM_CHAT_ID"]
        for index, job in enumerate(jobs, 1): _send_prompt(job["gemini_prompt"], job["candidate"], token, chat_id, index, len(jobs))
        used = state.setdefault("used_video_ids", []); history = state.setdefault("history", [])
        for job in jobs:
            candidate = job["candidate"]
            if candidate["video_id"] not in used: used.append(candidate["video_id"])
            history.append({"video_id": candidate["video_id"], "creator": candidate.get("creator", ""), "url": candidate["url"]})
        state["used_video_ids"] = used[-500:]; state["history"] = history[-500:]
        state_file.parent.mkdir(parents=True, exist_ok=True); state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("candidates"); parser.add_argument("config"); parser.add_argument("output"); parser.add_argument("--deliver", action="store_true"); parser.add_argument("--state", default="data/interior_trend_state.json")
    args = parser.parse_args(); run(args.candidates, args.config, args.output, args.deliver, args.state)
