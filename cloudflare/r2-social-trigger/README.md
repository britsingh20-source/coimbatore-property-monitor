# Cloudflare R2 → GitHub social publishing trigger

This Worker is the event trigger for the social publishing autopilot.

Flow:

R2 `social-ready/*.mp4` upload → R2 Event Notification → Queue → this Worker → GitHub `repository_dispatch` → `R2 Social Publishing Autopilot`.

## Cloudflare setup

1. Create a Queue named `property-social-publish-trigger`.
2. Deploy this Worker with Wrangler.
3. Add Worker secrets:
   - `GITHUB_TOKEN`: fine-grained GitHub token with Actions/workflow dispatch permission for `britsingh20-source/coimbatore-property-monitor`.
   - `GITHUB_REPOSITORY`: `britsingh20-source/coimbatore-property-monitor`
4. Configure the R2 bucket's Event Notification for `object-create` and send it to `property-social-publish-trigger`.
5. Filter the rule to prefix `social-ready/` and suffix `.mp4`.

The GitHub workflow listens for `r2-social-object-created` and performs the normal state-aware scan. It does not blindly publish the object; the existing video/property matching and destination state checks remain the gate before publishing.

## Deploy

```bash
cd cloudflare/r2-social-trigger
npx wrangler login
npx wrangler deploy
npx wrangler secret put GITHUB_TOKEN
npx wrangler secret put GITHUB_REPOSITORY
```

`GITHUB_REPOSITORY` is not sensitive, so it can also be configured as a Wrangler var instead of a secret.
