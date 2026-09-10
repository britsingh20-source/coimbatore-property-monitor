export interface Env {
  GITHUB_TOKEN: string;
  GITHUB_REPOSITORY: string;
}

type R2Message = {
  action?: string;
  bucket?: string;
  object?: {
    key?: string;
    size?: number;
    eTag?: string;
  };
  eventTime?: string;
};

export default {
  async queue(batch: MessageBatch<R2Message>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      const event = message.body ?? {};
      const key = event.object?.key ?? "";

      // Only wake GitHub for uploaded MP4s in the social-ready area.
      if (!key.startsWith("social-ready/") || !key.toLowerCase().endsWith(".mp4")) {
        message.ack();
        continue;
      }

      const response = await fetch(
        `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/dispatches`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.GITHUB_TOKEN}`,
            Accept: "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "coimbatore-property-monitor-r2-trigger",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            event_type: "r2-social-object-created",
            client_payload: {
              source: "cloudflare-r2",
              bucket: event.bucket ?? "",
              key,
              size: event.object?.size ?? 0,
              etag: event.object?.eTag ?? "",
              action: event.action ?? "",
              event_time: event.eventTime ?? "",
            },
          }),
        },
      );

      if (!response.ok) {
        const body = await response.text();
        throw new Error(`GitHub repository_dispatch failed (${response.status}): ${body.slice(0, 1000)}`);
      }

      message.ack();
    }
  },
};
