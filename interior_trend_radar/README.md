# Interior Trend Radar

An isolated competitor-learning pipeline for growing an interior-design Instagram page. It discovers recent public interior Shorts, extracts reusable creative patterns, creates an original Tamil-English content package, and sends four ready-to-paste Google Flow/Veo prompts to Telegram.

It does **not** download or repost competitor footage. Metadata-only runs are labeled low confidence; the pack never claims frame-level inspection unless visual input is actually available.

## Flow

1. YouTube search/channel feeds and manually curated public URLs.
2. Recent-item deduplication and ranking.
3. Gemini creative analysis with an original-content constraint.
4. Four consistent 9:16 Google video prompts, script, cover, caption and hashtags.
5. Optional Telegram delivery plus a downloadable GitHub Actions artifact.

## Configuration

Edit `config.json`. Add known competitor YouTube channel IDs to `youtube_channel_ids` and Instagram/Reel links to `manual_competitor_urls`. Manual Instagram URLs are reference inputs; automated public Instagram scraping is intentionally not used because it is unreliable and may violate access controls.

Required repository secrets for full operation:

- `YOUTUBE_API_KEY`
- `GEMINI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `INTERIOR_CONTACT` (your public enquiry number used inside production packs)

Run manually from **Actions → Interior Trend Radar → Run workflow**. Set `deliver_to_telegram=true` to receive the pack.
