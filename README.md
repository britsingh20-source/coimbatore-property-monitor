# Coimbatore Property Monitor and AI Video Queue

This project discovers recent YouTube property listings, analyzes each public
video once with Gemini, filters configured Coimbatore localities, stores durable
retry state, and creates reviewable vertical-video jobs. Veo rendering is manual
and restricted to IDs explicitly listed in `data/approved_video_ids.txt`.

## Safety and publishing rule

Generated videos are original AI visualizations based on verified listing facts.
They are not copies of competitor footage and must display this disclosure when
published: **AI visualisation based on listing facts; not actual property footage.**

No generated video is automatically uploaded to Instagram, YouTube or WhatsApp.
A person must verify the property facts, approve the source ID and review the
rendered artifact first.

## Required GitHub secrets

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY` with billing/quota for video understanding
- Veo access on the same Google project for video generation

## Workflow

1. `Property Monitor` runs hourly and processes at most three eligible videos.
2. Successful target-locality records are written to `data/properties.csv`.
3. A storyboard is written to `data/video_jobs/<video-id>.json`.
4. Verify the facts and add the ID to `data/approved_video_ids.txt`.
5. Manually run `Generate Approved Property Videos`.
6. Download the 9:16 MP4 artifact, review it and add branding/captions before publishing.

## Local checks

```bash
python -m unittest discover -s tests -v
python -m py_compile *.py
```

## Configuration

Edit `config/channels.json` for sources and `config/locations.json` for target
localities and aliases. Set `MAX_VIDEOS_PER_RUN` to control Gemini spend.
