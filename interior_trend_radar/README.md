# Interior Trend Radar

An isolated reference-first pipeline for growing Olive Tree Interiors. It discovers recent public interior videos, extracts five time-distributed visual references, verifies only what the images show, and sends those frames with one strict ready-to-paste Google Gemini/Veo prompt to Telegram.

It does **not** download or repost competitor footage. Metadata-only runs are labeled low confidence; the pack never claims frame-level inspection unless visual input is actually available.

## Flow

1. YouTube search/channel feeds and manually curated public URLs.
2. Recent-item deduplication and ranking.
3. Five-frame visual analysis through Gemini with no unsupported inference.
4. One 10-second, seven-shot, reference-first 9:16 prompt following the property-monitor structure.
5. Telegram reference album followed by the prompt document, plus a downloadable Actions artifact.

## Configuration

Edit `config.json`. Add priority creators to `monitored_youtube_channels`; a verified channel ID is preferred, but the workflow can resolve a YouTube handle through the official API. Lower priority numbers are processed first. Add Instagram/Reel links to `manual_competitor_urls`. Manual Instagram URLs are reference inputs; automated public Instagram scraping is intentionally not used because it is unreliable and may violate access controls.

Required repository secrets for full operation:

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `INTERIOR_CONTACT` (your public enquiry number used inside production packs)

Run manually from **Actions → Interior Trend Radar → Run workflow**. Set `deliver_to_telegram=true` to receive the pack.
