# Coimbatore Property Monitor and AI Video Queue

This project discovers recent YouTube property listings, analyzes each public
video once with Gemini, filters configured Coimbatore localities, stores durable
retry state, and creates reviewable vertical-video jobs. Final video rendering
uses Remotion, OpenStreetMap and FFmpeg without a paid video-generation API.

## Safety and publishing rule

Only property/location photographs owned by the advertiser or explicitly licensed
for reuse may be placed in `assets/properties`. Competitor footage and thumbnails
must not be copied. The renderer displays a verification disclosure automatically.

No generated video is automatically uploaded to Instagram, YouTube or WhatsApp.
A person must verify the property facts, approve the source ID and review the
rendered artifact first.

## Required GitHub secrets

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY` for property analysis (video rendering itself does not use it)
- `PEXELS_API_KEY` (optional) for free licensed walkthrough clips

## Workflow

1. `Property Monitor` runs hourly and processes at most three eligible videos.
2. Successful target-locality records are written to `data/properties.csv`.
3. A storyboard is written to `data/video_jobs/<video-id>.json`.
4. Verify the facts and add the ID to `data/approved_video_ids.txt`.
5. Manually run `Render Professional Approved Property Videos`.
6. The workflow searches Wikimedia Commons for exact-locality photographs and,
   when `PEXELS_API_KEY` is configured, Pexels for licensed property walkthrough clips.
7. Nominatim geocodes the locality once and a cached three-stage OpenStreetMap zoom
   is rendered with required attribution. The pin is never presented as an exact
   property coordinate unless the input has been independently verified.
8. It writes a fact-based Tamil script and generates a male Tamil narration using
   `ta-IN-ValluvarNeural`.
9. Remotion creates a 1080×1920 broadcast-style reel with a hook, map animation,
   real video clips, verified fact cards, disclosure and branded CTA.
10. Download and review the MP4 plus its attribution file before publishing.

User-owned video always takes priority, followed by user-owned photos and licensed
stock clips. Retrieved stock/locality media is visibly labeled as representative—not
the actual property. The timeline automatically expands to fit the Tamil narration.
If the Chromium/Remotion render fails, the existing FFmpeg renderer produces a
clearly identified fallback rather than losing the complete workflow run.

## What “professional” means here

This free GitHub Actions architecture can create polished editing, motion graphics,
map storytelling, narration and licensed B-roll. It cannot invent an exact, truthful
walkthrough of a house that was never filmed. Put actual portrait or landscape clips
in `assets/properties/<video-id>/`; the workflow automatically promotes them and
changes the footage label to `ACTUAL PROPERTY FOOTAGE`.

Pexels API access is free but requires an API key. Without it, the workflow uses
Wikimedia Commons and its per-file license/attribution metadata.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m py_compile *.py
```

## Configuration

Edit `config/channels.json` for sources and `config/locations.json` for target
localities and aliases. Set `MAX_VIDEOS_PER_RUN` to control Gemini spend.
