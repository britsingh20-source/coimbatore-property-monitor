# AI Free Tools Daily Channel

A separate, evidence-first production pipeline for publishing two or three daily AI-tool videos in Tamil, Hindi, and English.

## Human/automation boundary

The system creates the verified script, cinematic-hook prompt, AI B-roll prompt, screen-demonstration plan, tech-motion pack, captions, icons, 3D scene instructions, editing reference and publishing metadata.

The creator manually:
1. records the supplied script;
2. generates the cinematic hook in Google Gemini;
3. generates the conceptual B-roll in Google Gemini;
4. completes the final edit;
5. uploads the final MP4 to Telegram as a document.

The system then validates and publishes the completed video. It never automatically publishes an unfinished production pack.

## Job lifecycle

`discovered -> verified -> pack_ready -> pack_delivered -> final_uploaded -> validated -> approved -> publishing -> published`

Any failed validation becomes `correction_required`. Destination failures are retried independently.

## Initial destinations

- Instagram Reel
- Instagram Story
- Facebook Page Reel
- Facebook Page Story
- YouTube Short

TikTok remains a manual-ready export until Content Posting API access is approved.

## Required secrets

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `META_PAGE_ACCESS_TOKEN`
- `META_PAGE_ID`
- `META_IG_USER_ID`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

## Safety

Every “free” claim must include an official source, verification date, free-plan type, limitations, watermark status, card requirement and commercial-use status. A tool cannot reach `verified` with missing evidence.
