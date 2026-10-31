// Deployment marker: Interior ID + next MP4 must route to telegram-interior-upload.
export interface Env {
  GITHUB_DISPATCH_TOKEN: string;
  GITHUB_REPOSITORY: string;
  GITHUB_EVENT_TYPE: string;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_CHAT_ID: string;
  PAIRING_STATE: KVNamespace;
}

type R2Event = {
  account?: string;
  action?: string;
  bucket?: string;
  object?: { key?: string; size?: number; eTag?: string };
  eventTime?: string;
};

type QueueMessage = Message<R2Event>;
const GITHUB_API = "https://api.github.com";

type TelegramMessage = {
  message_id?: number;
  chat?: { id?: string | number };
  text?: string;
  caption?: string;
  video?: unknown;
  document?: { mime_type?: string; file_name?: string };
};

type TelegramUpdate = {
  update_id?: number;
  message?: TelegramMessage;
  edited_message?: TelegramMessage;
};

function extractVideoId(text: string): string {
  const labelled = text.match(/(?:video[\s_-]*id|id)[\s:=_-]+([A-Za-z0-9_-]{11})/i);
  if (labelled) return labelled[1];
  return /^[A-Za-z0-9_-]{11}$/.test(text) ? text : "";
}

type UploadPairing = { id: string; label: "VIDEO_ID" | "INTERIOR_ID" };

function extractUploadPairing(text: string): UploadPairing | null {
  const interior = text.match(/INTERIOR[\s_-]*ID\s*[:=\-]\s*([A-Za-z0-9_-]{6,32})(?![A-Za-z0-9_-])/i);
  if (interior) return { id: interior[1], label: "INTERIOR_ID" };
  const id = extractVideoId(text);
  return id ? { id, label: "VIDEO_ID" } : null;
}

function videoAttachment(message: TelegramMessage): boolean {
  if (message.video) return true;
  const doc = message.document;
  const mime = String(doc?.mime_type || "").toLowerCase();
  const name = String(doc?.file_name || "").toLowerCase();
  return Boolean(doc && (mime.startsWith("video/") || name.endsWith(".mp4")));
}

async function telegram(env: Env, method: string, body: object): Promise<void> {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Telegram ${method} failed: ${response.status}`);
}

async function githubDispatch(env: Env, eventType: string, clientPayload: object): Promise<Response> {
  return fetch(`${GITHUB_API}/repos/${env.GITHUB_REPOSITORY}/dispatches`, {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "coimbatore-property-telegram-worker",
    },
    body: JSON.stringify({ event_type: eventType, client_payload: clientPayload }),
  });
}

async function dispatchTelegram(update: TelegramUpdate, env: Env): Promise<Response> {
  const message = update.message || update.edited_message;
  const chatId = String(message?.chat?.id || "");
  if (!message || chatId !== String(env.TELEGRAM_CHAT_ID)) return new Response("ok");

  const updateKey = `telegram-update:${update.update_id}`;
  if (await env.PAIRING_STATE.get(updateKey)) return new Response("ok");
  await env.PAIRING_STATE.put(updateKey, "1", { expirationTtl: 86400 });

  const text = String(message.caption || message.text || "").trim();
  const explicit = extractUploadPairing(text);
  const attachment = videoAttachment(message);
  if (!attachment) {
    if (!explicit) return new Response("ok");
    await env.PAIRING_STATE.put(`pending-id:${chatId}`, `${explicit.label}: ${explicit.id}`, { expirationTtl: 900 });
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: `✅ ${explicit.label} saved: ${explicit.id}\nSend the MP4 within 15 minutes. It will publish immediately after pairing.`,
    });
    return new Response("ok");
  }

  // Parse both labelled pairings and bare VIDEO_ID values saved by older deployments.
  const pairing = explicit || extractUploadPairing(await env.PAIRING_STATE.get(`pending-id:${chatId}`) || "");
  if (!pairing) {
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: "⚠️ Pairing failed. Send VIDEO_ID or INTERIOR_ID, then resend the MP4 within 15 minutes. Nothing was published.",
    });
    return new Response("ok");
  }

  const videoId = pairing.id;
  message.caption = `${pairing.label}: ${videoId}`;
  const eventType = pairing.label === "INTERIOR_ID" ? "telegram-interior-upload" : "telegram-property-upload";
  const response = await githubDispatch(env, eventType, { update });
  console.log(`Telegram dispatch ${eventType} for ${videoId}: GitHub HTTP ${response.status}`);
  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    // Retain duplicate protection after a failed dispatch; Telegram must not replay it.
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: `⚠️ Upload paired to ${videoId}, but GitHub publishing could not start: ${response.status}. Do not resend repeatedly; fix publishing access before retrying once.`,
    });
    console.error("Telegram GitHub dispatch failed", response.status, detail);
    return new Response("ok");
  }

  await env.PAIRING_STATE.delete(`pending-id:${chatId}`);
  await telegram(env, "sendMessage", {
    chat_id: chatId,
    text: `✅ ${videoId} paired and GitHub accepted ${eventType}. Live publishing dispatch started. Duplicate protection is active.`,
  });
  return new Response("ok");
}

function normalizeKey(key: string): string { return key.replace(/^\/+/, ""); }

function isPublishableObject(event: R2Event): boolean {
  const key = normalizeKey(String(event.object?.key || ""));
  return event.action !== "DeleteObject" && key.startsWith("social-ready/") && key.toLowerCase().endsWith(".mp4");
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
  const response = await fetch(`${GITHUB_API}/repos/${env.GITHUB_REPOSITORY}/dispatches`, {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
      "X-GitHub-Api-Version": "2026-03-10",
      "Content-Type": "application/json",
      "User-Agent": "coimbatore-property-social-trigger",
    },
    body: JSON.stringify({ event_type: env.GITHUB_EVENT_TYPE, client_payload: payload }),
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GitHub repository_dispatch failed (${response.status}): ${body.slice(0, 1000)}`);
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET") return new Response("coimbatore-property-social-trigger: healthy");
    if (request.method !== "POST") return new Response("Method not allowed", { status: 405 });
    let update: TelegramUpdate;
    try { update = await request.json() as TelegramUpdate; }
    catch { return new Response("Bad request", { status: 400 }); }
    return dispatchTelegram(update, env);
  },

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
        message.retry();
      }
    }
  },
};
