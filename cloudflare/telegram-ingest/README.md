# Event-driven Telegram publishing

This Worker removes GitHub cron polling from the critical path.

## Flow

1. Telegram calls the Worker webhook immediately.
2. A standalone 11-character VIDEO_ID is held in KV for 15 minutes.
3. The next MP4 is paired to that exact ID. A missing ID produces an immediate Telegram error and no dispatch.
4. The Worker sends a GitHub `repository_dispatch` event.
5. `r2-social-autopilot.yml` ingests the supplied Telegram update and runs live publishing.
6. `data/social_publish_state.json` remains the destination-level duplicate guard.
7. Existing 10-minute schedules remain recovery-only fallbacks.

## One-time deployment

Create a KV namespace and place its ID in `wrangler.toml`. Then configure secrets:

```bash
cd cloudflare/telegram-ingest
npx wrangler kv namespace create PAIRING_STATE
npx wrangler secret put WEBHOOK_SECRET
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_CHAT_ID
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

The GitHub token needs Actions write access and repository metadata read access only.

Register the deployed URL with Telegram (substitute the Worker URL and the same webhook secret):

```bash
curl --request POST "https://api.telegram.org/bot<token>/setWebhook" \
  --data-urlencode "url=https://<worker-domain>/telegram/<webhook-secret>" \
  --data-urlencode 'allowed_updates=["message"]' \
  --data-urlencode "drop_pending_updates=false"
```

Test by sending the exact VIDEO_ID first and then the MP4. Telegram should acknowledge both the saved ID and the publishing dispatch immediately.
