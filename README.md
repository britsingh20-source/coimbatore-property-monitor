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
4. Add at least three owned JPG/PNG photos to `assets/properties/<video-id>/`.
5. Optionally add your Tamil narration or licensed music as `assets/audio/<video-id>.mp3`.
6. Verify the facts and add the ID to `data/approved_video_ids.txt`.
7. Manually run `Render Free Approved Property Videos`.
8. Download and review the 1080×1920 MP4 artifact before publishing.

Each photo receives a slow cinematic pan/zoom, fade transitions and fact captions.
With five images the result is 30 seconds long. No Veo, Runway, Kling or other paid
video service is called.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m py_compile *.py
```

## Configuration

Edit `config/channels.json` for sources and `config/locations.json` for target
localities and aliases. Set `MAX_VIDEOS_PER_RUN` to control Gemini spend.
