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
8. That commit automatically triggers **Render Autopilot Property Videos**.
9. The selector renders only auto-approved jobs changed by that commit.
10. The MP4 and its attribution, map and narration records are uploaded as a
    seven-day GitHub Actions artifact.

No manual footage upload or workflow dispatch is required for a valid listing.

## Automatic media and narration

- Wikimedia Commons supplies reusable location-related images.
- Pexels supplies licensed representative portrait property clips when
  `PEXELS_API_KEY` is configured.
- Nominatim geocodes the locality and OpenStreetMap provides a three-stage zoom.
- Edge TTS generates a Tamil male narration with `ta-IN-ValluvarNeural`.
- The Remotion timeline expands automatically to fit the narration.
- Automatically sourced property media is labelled as representative.

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
- `PEXELS_API_KEY` for licensed walkthrough clips; without it the workflow
  continues with Wikimedia and bundled representative visuals

## Manual recovery

`workflow_dispatch` remains available. A manually listed ID in
`data/approved_video_ids.txt` is included during manual or pull-request runs.
Push-triggered production renders do not rerender the historical approval list.

## Local validation

```bash
python -m unittest discover -s tests -v
python -m py_compile *.py
npm --prefix professional_video run typecheck
```
