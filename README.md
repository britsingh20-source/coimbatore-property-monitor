# Coimbatore Property Monitor and Autopilot Video Generator

This project discovers recent Tamil property listings, analyzes them with Gemini,
filters configured Coimbatore localities and automatically renders truthful
vertical marketing videos with Remotion.

## Production flow

1. **Property Monitor** runs hourly.
2. It checks the configured YouTube channels and processes at most three eligible videos.
3. Gemini extracts the property type, location, land area, built-up area, price,
   facing, road width, parking, approval and source facts.
4. The locality matcher rejects listings outside the configured Coimbatore areas.
5. A target listing with a property type, source facts and at least two usable
   property facts becomes `auto_approved`.
6. Sparse or ambiguous listings become `needs_review` and are not rendered.
7. The monitor commits the job JSON to `data/video_jobs/`.
8. It sends a `repository_dispatch` event containing only the newly approved
   video IDs. This explicit dispatch is required because GitHub does not start a
   second workflow from a normal `GITHUB_TOKEN` push.
9. **Render Autopilot Property Videos** validates the dispatched IDs against the
   committed `auto_approved` jobs and rejects historical or unapproved IDs.
10. Each property is rendered independently. One failed property cannot prevent
    the remaining dispatched properties from completing.
11. MP4 files plus attribution, map, voice-engine and failure diagnostics are
    uploaded as a seven-day GitHub Actions artifact.

No manual footage upload or workflow dispatch is required for a valid listing.

## Automatic media and narration

- Wikimedia Commons supplies reusable location-related images.
- Pixabay is the primary licensed image/video source, with Pexels as a
  fallback, when `PIXABAY_API_KEY` / `PEXELS_API_KEY` are configured.
  Previously-approved video clips are cached locally under
  `assets/library/<category>/` and reused across runs.
- Nominatim geocodes the locality and OpenStreetMap provides a three-stage zoom.
- Edge TTS generates the Tamil male narration for every fact scene.
- Every narration manifest records the TTS engine and style used.
- The Remotion timeline expands automatically to fit the narration.
- Automatically sourced property media is labelled as representative.

Dispatch uses the built-in repository `GITHUB_TOKEN`; no personal access token
or additional secret is required.

The system never presents stock footage as the actual property. Advertiser-owned
media is still supported and takes priority when it exists, but it is optional.

## Video output

- 1080 × 1920 vertical MP4
- H.264 video with Tamil audio
- Coimbatore → locality map journey
- narration-synced land, built-up, price, facing, road and approval VFX
- COIMBATOREVEEDU BUILDERS branding
- persistent Call / WhatsApp number 9003787621
- FFmpeg emergency fallback if Remotion fails

## Required GitHub secrets

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY`
- `PIXABAY_API_KEY` for licensed images and video b-roll (primary source);
  without it the workflow falls back to Pexels, Wikimedia and bundled
  representative visuals
- `PEXELS_API_KEY` for licensed walkthrough clips as a fallback source; without
  it the workflow continues with Wikimedia and bundled representative visuals

## Persistent video-clip cache (Cloudflare R2)

Every approved video clip gets cached in a Cloudflare R2 bucket, organized by
scene (`library/exteriors/`, `library/interiors/`, `library/roads/`,
`library/plots/`, `library/drone_views/`). Each scene checks the cache before
calling Pixabay/Pexels at all, so the pool of pre-approved footage grows on
its own across runs instead of researching from scratch every time. Without
R2 credentials configured, the cache falls back to the GitHub Actions
runner's local disk, which does **not** persist between runs — R2 is what
makes this actually durable.

Required secrets/variables (Settings → Secrets and variables → Actions):

- `R2_ACCOUNT_ID` — from the R2 dashboard URL or bucket settings
- `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` — from an R2 API token
  (Cloudflare dashboard → R2 → Manage API Tokens → Create API Token,
  with Object Read & Write permission scoped to the bucket)
- `R2_BUCKET_NAME` (repository *variable*, not secret) — defaults to
  `github` if unset

## Own filmed b-roll (highest priority, no stock at all)

Before touching the stock cache or any API, each scene first checks the
advertiser's own filmed footage in the same R2 bucket, organized as
`<property-type>/<room>/*.mp4`:

```
villas/
  Road/
  exterior/
  bedroom/
  dining & Kitchen/
  living_room/
```

- `road` scene → `villas/Road/`
- `exterior` scene → `villas/exterior/`
- `interior` scene → pooled across `villas/bedroom/`, `villas/dining & Kitchen/`,
  `villas/living_room/` for variety
- Bare plots (no rooms to film) skip this tier entirely and go straight to the
  stock cache/APIs
- This tier is **read-only from the pipeline's side** — it never auto-writes
  stock clips here, so the folders only ever contain footage the business
  actually filmed and uploaded itself. Only `villas` exists today; more
  property-type folders (e.g. `apartments/`) can be added later by uploading
  clips and adding a keyword entry to `PROPERTY_TYPE_LIBRARY_FOLDERS` in
  `media_sources.py`.

Priority order per scene: **own footage → cached stock → Pixabay → Pexels**.
Each tier only fills the shortfall left by the one before it.

## Manual recovery

`workflow_dispatch` remains available. A manually listed ID in
`data/approved_video_ids.txt` is included during manual or pull-request runs.
Manual runs can also accept comma-separated video IDs. Blank manual runs use
`data/approved_video_ids.txt`. Automated production renders use only the exact
IDs supplied by the monitor and never rerender the historical approval list.

## Local validation

```bash
python -m unittest discover -s tests -v
python -m py_compile *.py
npm --prefix professional_video run typecheck
```

## R2 social publishing autopilot

After generating a 9:16 MP4 in Gemini mobile, upload it to the configured R2 bucket inside the `social-ready` folder. Keep the phone's original filename; renaming is not required.

```text
social-ready/GeminiGeneratedVideo.mp4
```

Every successfully delivered Telegram prompt is added to `data/telegram_prompt_queue.json`. The scheduled **R2 Social Publishing Autopilot** pairs the oldest unpaired Telegram prompt with the oldest new mobile upload, scans every 15 minutes, and processes at most one video per run. For reliable matching, generate and upload one property at a time in the same order the prompts arrive.

For each R2 upload it generates:

- a hook-led YouTube title;
- a property caption and YouTube description using only verified job facts;
- exactly three hashtags;
- the fixed site-visit number `9003787621`.

Destinations are tracked separately in `data/social_publish_state.json`:

- Instagram Reel;
- Facebook Page Reel;
- Instagram Story;
- Facebook Page Story;
- YouTube Short.

If one destination fails, completed destinations remain recorded and are not posted again. Only the failed or unconfigured destination is retried.

### Required GitHub Actions secrets

Existing R2 and Meta publishing secrets:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `META_PAGE_ACCESS_TOKEN`
- `META_PAGE_ID`
- `META_IG_USER_ID`

YouTube uploads require OAuth credentials with the `youtube.upload` scope:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

The existing `YOUTUBE_API_KEY` cannot upload videos. When the YouTube OAuth secrets are absent, Meta destinations can still publish and YouTube remains in `waiting_for_secrets` for a later retry.

Use **Run workflow** with `dry_run=true` to scan and preview state without publishing. Scheduled runs publish automatically.
