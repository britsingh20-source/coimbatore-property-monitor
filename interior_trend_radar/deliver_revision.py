"""Deliver the explicitly requested corrected reference prompt once."""
import json
import os
from pathlib import Path
from .reference_first import build_reference_prompt, _send_prompt

data = json.loads(Path("interior_trend_radar/revisions/wardrobe_motion_v2.json").read_text())
receipt = Path("data/wardrobe_motion_v3_delivery.json")
if receipt.exists():
    raise SystemExit("Revision already delivered or pending; inspect receipt before resending")
prompt = build_reference_prompt(data["candidate"], data["analysis"], {"brand": "Olive Tree Interiors"})
print(f"REVISION_PROMPT words={len(prompt.split())} characters={len(prompt)}", flush=True)
# Persist uncertainty before sending to avoid blindly repeating a successful delivery.
receipt.write_text(json.dumps({"revision_id": data["revision_id"], "status": "pending"}) + "\n")
_send_prompt(prompt, data["candidate"], os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"], 1, 1)
receipt.write_text(json.dumps({"revision_id": data["revision_id"], "status": "confirmed"}) + "\n")
print("CORRECTED_WARDROBE_PROMPT_DELIVERY_CONFIRMED", flush=True)
