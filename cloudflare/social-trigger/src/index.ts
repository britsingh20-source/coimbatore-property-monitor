export interface Env {
  GITHUB_DISPATCH_TOKEN: string;
  GITHUB_REPOSITORY: string;
  GITHUB_EVENT_TYPE: string;
}

type R2Event = {
  account?: string;
  action?: string;
  bucket?: string;
  object?: {
    key?: string;
    size?: number;
    eTag?: string;
  };
  eventTime?: string;
};

type QueueMessage = Message<R2Event>;

const GITHUB_API = "https://api.github.com";

function normalizeKey(key: string): string {
  return key.replace(/^\/+/, "");
}

function isPublishableObject(event: R2Event): boolean {
  const key = normalizeKey(String(event.object?.key || ""));
  return (
    event.action !== "DeleteObject" &&
    key.startsWith("social-ready/") &&
    key.toLowerCase().endsWith(".mp4")
  );
}

async function dispatchToGitHub(event: R2Event, env: Env): Promise<void> {
  const key = normalizeKey(String(event.object?.key || ""));
  const payload = {
    r2_key: key,
    bucket: event.bucket || "",
    action: event.action || "",
    etag: event.object?.eTag || "",
    size: event.object?.size || 0,
    event_time: event.eventTime || new Date().toISOString(),
    source: "cloudflare-r2-event-notification",
  };

  const response = await fetch(
    `${GITHUB_API}/repos/${env.GITHUB_REPOSITORY}/dispatches`,
    {
      method: "POST",
      headers: {
        "Accept": "application/vnd.github+json",
        "Authorization": `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        "X-GitHub-Api-Version": "2026-03-10",
        "Content-Type": "application/json",
        "User-Agent": "coimbatore-property-social-trigger",
      },
      body: JSON.stringify({
        event_type: env.GITHUB_EVENT_TYPE,
        client_payload: payload,
      }),
    },
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(
      `GitHub repository_dispatch failed (${response.status}): ${body.slice(0, 1000)}`,
    );
  }
}

export default {
  async queue(batch: MessageBatch<R2Event>, env: Env): Promise<void> {
    for (const message of batch.messages as QueueMessage[]) {
      const event = message.body;
      const key = normalizeKey(String(event.object?.key || ""));

      if (!isPublishableObject(event)) {
        message.ack();
        continue;
      }

      try {
        await dispatchToGitHub(event, env);
        console.log(`Dispatched ${key} to GitHub social autopilot`);
        message.ack();
      } catch (error) {
        console.error(`Dispatch failed for ${key}:`, error);
        // Throwing leaves the message retryable according to the Queue consumer policy.
        message.retry();
      }
    }
  },
};
