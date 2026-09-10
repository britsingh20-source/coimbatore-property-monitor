export interface Env {
  GITHUB_REPOSITORY_DISPATCH_TOKEN: string;
  GITHUB_OWNER: string;
  GITHUB_REPO: string;
}

type R2Event = {
  account?: string;
  action?: string;
  bucket?: string;
  object?: { key?: string; size?: number; eTag?: string };
  eventTime?: string;
};

export default {
  async queue(batch: MessageBatch<R2Event>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      const event = message.body;
      const key = event?.object?.key ?? "";

      if (!key.startsWith("social-ready/") || !key.toLowerCase().endsWith(".mp4")) {
        message.ack();
        continue;
      }

      const response = await fetch(
        `https://api.github.com/repos/${encodeURIComponent(env.GITHUB_OWNER)}/${encodeURIComponent(env.GITHUB_REPO)}/dispatches`,
        {
          method: "POST",
          headers: {
            "Accept": "application/vnd.github+json",
            "Authorization": `Bearer ${env.GITHUB_REPOSITORY_DISPATCH_TOKEN}`,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "coimbatore-property-monitor-r2-trigger",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event_type: "r2-social-object-created",
            client_payload: {
              r2_key: key,
              bucket: event.bucket ?? null,
              size: event.object?.size ?? null,
              etag: event.object?.eTag ?? null,
              action: event.action ?? null,
              event_time: event.eventTime ?? null,
            },
          }),
        },
      );

      if (!response.ok) {
        throw new Error(`GitHub repository_dispatch failed (${response.status}): ${await response.text()}`);
      }

      message.ack();
      console.log(`Dispatched social publishing for ${key}`);
    }
  },
};
