# Cloudflare R2 → automatic Instagram/YouTube trigger

The repository already has `.github/workflows/r2-social-autopilot.yml`, which listens for the `r2-social-object-created` repository-dispatch event. This Worker is the missing Cloudflare bridge: R2 object-create → Queue → Worker → GitHub repository_dispatch.

## Cloudflare setup

Create a Queue, for example `coimbatore-property-social-events`.

Configure the R2 bucket that receives `social-ready/` uploads with an `object-create` event notification to that queue, filtered with prefix `social-ready/` and suffix `.mp4`.

Deploy `cloudflare-r2-social-trigger.ts` as a Queue consumer Worker.

Set these Worker variables:

- `GITHUB_OWNER=britsingh20-source`
- `GITHUB_REPO=coimbatore-property-monitor`

Create the Worker secret:

- `GITHUB_REPOSITORY_DISPATCH_TOKEN` — a GitHub token allowed to create repository dispatch events for this repository. Do not commit this value.

The Worker only dispatches for `social-ready/*.mp4`; other R2 objects are acknowledged and ignored.

## Expected flow

Telegram upload → existing ingestion → R2 `social-ready/` → R2 event notification → Cloudflare Queue → Worker → GitHub `r2-social-object-created` → existing `R2 Social Publishing Autopilot` → YouTube/Instagram/Facebook.

The existing 10-minute GitHub schedule remains as a fallback/recovery mechanism, so the event-driven trigger does not remove the safety net.
