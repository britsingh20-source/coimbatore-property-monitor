# Coimbatore Property Monitor and AI Video Queue

This project discovers recent YouTube property listings, analyzes each public
video once with Gemini, filters configured Coimbatore localities, stores durable
retry state, and creates reviewable vertical-video jobs. Final video rendering
uses FFmpeg and makes no paid video-generation API calls.

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

## Workflow

1. `Property Monitor` runs hourly and processes at most three eligible videos.
2. Successful target-locality records are written to `data/properties.csv`.
3. A storyboard is written to `data/video_jobs/<video-id>.json`.
4. Verify the facts and add the ID to `data/approved_video_ids.txt`.
5. Manually run `Render Free Approved Property Videos`.
6. The workflow searches Wikimedia Commons for exact-locality media, optionally
   falls back to Pexels when `PEXELS_API_KEY` is configured, and saves attribution.
7. It writes a fact-based Tamil script and generates a male Tamil narration using
   `ta-IN-ValluvarNeural`.
8. Download and review the 1080×1920 MP4 plus its attribution file before publishing.

User-owned photos always take priority when present. Retrieved stock/locality media
is labeled as representative—not the actual property. Each photo receives a slow
cinematic pan/zoom, transitions and fact captions. The timing automatically expands
to fit the complete Tamil narration. No paid video-generation API is called.

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
