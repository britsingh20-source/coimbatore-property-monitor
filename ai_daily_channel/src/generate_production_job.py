from __future__ import annotations
import json, os
from datetime import datetime, timezone
from pathlib import Path
from urllib import parse, request
from .job_validation import validate_job

SYSTEM="""You are the evidence editor for Aibros, an Indian AI-updates and verified-free-tools channel.
Choose one candidate with freshness, practical value, technical depth, free access and visual demonstration potential.
Never invent pricing, licence, commercial use, watermark, card or limits: use unknown when evidence is missing.
Write a natural advanced Tamil-English 45-60 second Reel script covering what changed, why it matters,
how it works, how an ordinary person can use it, its exact free classification, requirements and one honest limitation.
Return only JSON. Hook prompt: preserve the supplied presenter identity, choose scene-specific clothing, forbid text/logos/watermarks.
B-roll prompt: visualize the actual mechanism, not generic robots or server rooms."""

def gemini(prompt):
    key=os.environ["GEMINI_API_KEY"]; model=os.getenv("GEMINI_MODEL","gemini-2.5-flash")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={parse.quote(key)}"
    body={"contents":[{"parts":[{"text":SYSTEM+"\n\n"+prompt}]}],"generationConfig":{"temperature":.2,"responseMimeType":"application/json"}}
    req=request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with request.urlopen(req,timeout=90) as r: data=json.loads(r.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def generate(discovery_path,output_path):
    candidates=json.loads(Path(discovery_path).read_text())["candidates"][:15]
    shape={"job_id":"lowercase-hyphenated-id","language":"ta","status":"pack_ready","tool":{"name":"","official_url":"https://","free_claim":"unknown","verified_at":datetime.now(timezone.utc).isoformat(),"evidence":[{"url":"https://","claim":""}],"limitations":[],"card_required":None,"watermark":None,"commercial_use":"unknown"},"script":{"exact_text":"","pronunciation":[],"segments":[{"start_hint":0,"end_hint":3,"text":"","delivery":"energetic"}]},"prompts":{"cinematic_hook":"","ai_broll":""},"production":{"screen_demo":[],"motion_graphics":[],"edit_reference":[]},"publishing":{"destinations":{},"title":"","caption":"","hashtags":["#Aibros","#FreeAITools","#AIUpdates"]}}
    prompt="Candidates:\n"+json.dumps(candidates,ensure_ascii=False,indent=2)+"\nReturn the exact structure, filling every field:\n"+json.dumps(shape,ensure_ascii=False,indent=2)
    job=json.loads(gemini(prompt))
    job.setdefault("publishing", {})["hashtags"]=["#Aibros","#FreeAITools","#AIUpdates"]
    errors=validate_job(job)
    if errors: raise ValueError("; ".join(errors))
    Path(output_path).write_text(json.dumps(job,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Generated",job["job_id"])
if __name__=="__main__":
    import sys; generate(sys.argv[1],sys.argv[2])
