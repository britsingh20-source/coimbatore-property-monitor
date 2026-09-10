# Cloudflare R2 → automatic Instagram/YouTube trigger

The social publishing code already lives in GitHub Actions. The Cloudflare layer is the reliable event trigger and buffer:

**Telegram upload → R2 `social-ready/*.mp4` → R2 Event Notification → Cloudflare Queue → Cloudflare Worker → GitHub `repository_dispatch` → R2 Social Publishing Autopilot → Instagram + YouTube**

The existing scheduled scan remains as a recovery fallback.

## What was added to this repository

- `cloudflare/social-trigger/wrangler.jsonc` — Queue consumer Worker configuration.
- `cloudflare/social-trigger/src/index.ts` — consumes R2 events and dispatches the exact R2 object to GitHub.
- `.github/workflows/deploy-cloudflare-social-trigger.yml` — creates the Queue, deploys the Worker, sets the Worker secret, and configures the R2 event notification.
- `.github/workflows/r2-social-autopilot.yml` — no longer cancels an active publishing run when another video arrives; incoming videos are queued. R2 events process only the exact MP4 that triggered the event, while scheduled runs continue to scan the full `social-ready/` prefix.

## One-time GitHub secrets required

Add these repository secrets before running the Cloudflare deployment workflow:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`
- `GITHUB_DISPATCH_TOKEN`
- `R2_BUCKET_NAME` (already required by the existing R2 pipeline; keep the existing value)

The existing Meta/Instagram and YouTube secrets are reused by the publishing workflow; they are not moved into Cloudflare.

### `GITHUB_DISPATCH_TOKEN`

Use a GitHub token that can create a repository dispatch for `britsingh20-source/coimbatore-property-monitor`. Keep it only as a Cloudflare Worker secret; never commit it.

### `CLOUDFLARE_API_TOKEN`

Use a Cloudflare API token with enough permissions to manage the Worker, Queues, and the R2 event-notification rule for this account.

## Cloudflare resources

The deployment workflow creates/uses:

- Queue: `coimbatore-property-social-events`
- Worker: `coimbatore-property-social-trigger`
- R2 event rule: `object-create`, prefix `social-ready/`, suffix `.mp4`

Cloudflare R2 Event Notifications are designed to send object-change messages to Queues, and Queue consumers can retry failed messages. See the official Cloudflare documentation for the event-notification and Queue model.

## Four-video behavior

If four MP4s arrive close together, each R2 event enters the Queue. GitHub Actions is configured not to cancel the active publishing run, so the videos wait rather than being lost. Each event carries its exact R2 key, preventing a new upload from accidentally publishing an older file.

The scheduled GitHub scan remains enabled as a safety net for anything that was not successfully dispatched.
