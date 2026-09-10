from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .reference_first import build_reference_prompt, _send_prompt, _load_state
from .video_analyzer import analyze_interior_video


def run(candidates_path: str, config_path: str, output_path: str, deliver: bool, state_path: str, slot: str) -> dict:
    discovery = json.loads(Path(candidates_path).read_text(encoding="utf-8"))
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    state_file = Path(state_path)
    state = _load_state(state_file)
    used = set(state.get("used_video_ids", []))
    candidates = [c for c in discovery.get("candidates", []) if c.get("video_id") not in used]

    # Prefer monitored channels, then fall back to search results. A single unrelated
    # upload must never abort the whole daily Interior Radar run.
    channel_order = [c.get("name", "") for c in config.get("monitored_youtube_channels", [])]
    rank = {name: i for i, name in enumerate(channel_order)}
    candidates.sort(key=lambda c: (rank.get(c.get("creator", ""), 999), c.get("published_at", "")), reverse=False)

    jobs = []
    rejected = []
    target = 1 if slot != "manual" else min(int(config.get("daily_prompt_limit", 5)), 5)
    for candidate in candidates:
        try:
            analysis = analyze_interior_video(candidate)
        except Exception as exc:
            rejected.append({"video_id": candidate.get("video_id", ""), "creator": candidate.get("creator", ""), "reason": str(exc)})
            print(f"Skipping candidate {candidate.get('video_id', '')}: {exc}")
            continue
        jobs.append({"candidate": candidate, "video_analysis": analysis, "gemini_prompt": build_reference_prompt(candidate, analysis, config)})
        if len(jobs) >= target:
            break

    if not jobs:
        raise ValueError(f"No verified interior candidate remained after analysis. Rejected {len(rejected)} candidates.")

    result = {"jobs": jobs, "prompt_count": len(jobs), "reference_mode": "youtube_url_only", "delivery_slot": slot, "rejected_candidates": rejected}
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if deliver:
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]
        for index, job in enumerate(jobs, 1):
            _send_prompt(job["gemini_prompt"], job["candidate"], token, chat_id, index, len(jobs))
        used_list = state.setdefault("used_video_ids", [])
        history = state.setdefault("history", [])
        for job in jobs:
            candidate = job["candidate"]
            if candidate["video_id"] not in used_list:
                used_list.append(candidate["video_id"])
            history.append({"video_id": candidate["video_id"], "creator": candidate.get("creator", ""), "url": candidate["url"]})
        state["used_video_ids"] = used_list[-500:]
        state["history"] = history[-500:]
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates")
    parser.add_argument("config")
    parser.add_argument("output")
    parser.add_argument("--deliver", action="store_true")
    parser.add_argument("--state", default="data/interior_trend_state.json")
    parser.add_argument("--slot", choices=("morning", "afternoon", "evening", "night", "manual"), default="manual")
    args = parser.parse_args()
    run(args.candidates, args.config, args.output, args.deliver, args.state, args.slot)
