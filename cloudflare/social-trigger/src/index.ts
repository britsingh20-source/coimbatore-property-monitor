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
  object?: {
    key?: string;
    size?: number;
    eTag?: string;
  };
  eventTime?: string;
};

type QueueMessage = Message<R2Event>;

const GITHUB_API = "https://api.github.com";
const ACTIVE_FOCUS_KEY = "weekly-focus-active";

type TelegramMessage = {
  message_id?: number;
  chat?: { id?: string | number };
  text?: string;
  caption?: string;
  video?: unknown;
  document?: { mime_type?: string; file_name?: string };
};

type TelegramCallbackQuery = {
  id?: string;
  data?: string;
  message?: TelegramMessage;
};

type TelegramUpdate = {
  update_id?: number;
  message?: TelegramMessage;
  edited_message?: TelegramMessage;
  callback_query?: TelegramCallbackQuery;
};

type FocusArea = {
  slug: string;
  name: string;
  aliases?: string[];
  micro_localities?: string[];
};

type FocusCatalog = {
  areas: FocusArea[];
  rules?: { max_selected?: number; selection_ttl_minutes?: number };
};

function extractVideoId(text: string): string {
  const labelled = text.match(/(?:video[\s_-]*id|id)[\s:=_-]+([A-Za-z0-9_-]{11})/i);
  if (labelled) return labelled[1];
  return /^[A-Za-z0-9_-]{11}$/.test(text) ? text : "";
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

async function loadFocusCatalog(env: Env): Promise<FocusCatalog> {
  const url = `https://raw.githubusercontent.com/${env.GITHUB_REPOSITORY}/main/config/focus_areas.json`;
  const response = await fetch(url, { cf: { cacheTtl: 60, cacheEverything: true } });
  if (!response.ok) throw new Error(`Focus area catalog unavailable: ${response.status}`);
  return await response.json() as FocusCatalog;
}

function focusSelectionKey(chatId: string): string {
  return `weekly-focus-selection:${chatId}`;
}

async function readJsonList(env: Env, key: string): Promise<string[]> {
  const raw = await env.PAIRING_STATE.get(key);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return [];
  }
}

async function readFocusSelection(env: Env, chatId: string): Promise<string[]> {
  const pending = await readJsonList(env, focusSelectionKey(chatId));
  if (pending.length) return pending;
  return readJsonList(env, ACTIVE_FOCUS_KEY);
}

async function writeFocusSelection(env: Env, chatId: string, selected: string[], ttlMinutes: number): Promise<void> {
  await env.PAIRING_STATE.put(
    focusSelectionKey(chatId),
    JSON.stringify(selected),
    { expirationTtl: Math.max(60, ttlMinutes * 60) },
  );
}

function focusKeyboard(catalog: FocusCatalog, selected: string[]): object {
  const buttons = catalog.areas.map(area => ({
    text: `${selected.includes(area.slug) ? "✅ " : ""}${area.name}`,
    callback_data: `focus:toggle:${area.slug}`,
  }));
  const rows: object[][] = [];
  for (let i = 0; i < buttons.length; i += 2) rows.push(buttons.slice(i, i + 2));
  rows.push([
    { text: "✅ Apply Weekly Focus", callback_data: "focus:apply" },
    { text: "✖ Cancel", callback_data: "focus:cancel" },
  ]);
  return { inline_keyboard: rows };
}

function focusText(catalog: FocusCatalog, selected: string[]): string {
  const max = Number(catalog.rules?.max_selected || 2);
  const names = catalog.areas.filter(area => selected.includes(area.slug)).map(area => area.name);
  return [
    "🎯 WEEKLY FOCUS",
    `Select 1 or up to ${max} areas for the current Sunday–Saturday campaign.`,
    names.length ? `Selected: ${names.join(" + ")}` : "Selected: none",
    "Tap Apply Weekly Focus when ready.",
  ].join("\n");
}

function indiaDateParts(now = new Date()): { year: number; month: number; day: number } {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const get = (type: string) => Number(parts.find(part => part.type === type)?.value || 0);
  return { year: get("year"), month: get("month"), day: get("day") };
}

function isoDateUtc(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function currentSundaySaturday(): { start: string; end: string } {
  const p = indiaDateParts();
  const d = new Date(Date.UTC(p.year, p.month - 1, p.day));
  const daysSinceSunday = d.getUTCDay();
  const start = new Date(d);
  start.setUTCDate(d.getUTCDate() - daysSinceSunday);
  const end = new Date(start);
  end.setUTCDate(start.getUTCDate() + 6);
  return { start: isoDateUtc(start), end: isoDateUtc(end) };
}

function buildWeeklyFocusConfig(catalog: FocusCatalog, selected: string[]): object {
  const { start, end } = currentSundaySaturday();
  const maxSelected = Number(catalog.rules?.max_selected || 2);
  const chosen = catalog.areas.filter(area => selected.includes(area.slug)).slice(0, maxSelected);
  return {
    timezone: "Asia/Kolkata",
    week_start: start,
    week_end: end,
    focus_areas: chosen.map(area => ({
      name: area.name,
      aliases: area.aliases || [],
      micro_localities: area.micro_localities || [],
    })),
    rules: {
      max_focus_areas: maxSelected,
      require_focus_match_for_prompt: true,
      allow_citywide_fallback: false,
      prompt_instruction: "For this Sunday-to-Saturday focus week, prioritize only properties and prompt context that belong to the configured focus area(s) or their configured micro-localities. Do not broaden the prompt to unrelated Coimbatore areas.",
    },
  };
}

async function showFocusMenu(env: Env, chatId: string, messageId?: number): Promise<void> {
  const catalog = await loadFocusCatalog(env);
  const selected = await readFocusSelection(env, chatId);
  const payload = {
    chat_id: chatId,
    text: focusText(catalog, selected),
    reply_markup: focusKeyboard(catalog, selected),
  };
  if (messageId) {
    await telegram(env, "editMessageText", { ...payload, message_id: messageId });
  } else {
    await telegram(env, "sendMessage", payload);
  }
}

async function dispatchFocusCallback(update: TelegramUpdate, env: Env): Promise<Response> {
  const query = update.callback_query;
  const data = String(query?.data || "");
  const chatId = String(query?.message?.chat?.id || "");
  const messageId = query?.message?.message_id;
  if (!query || chatId !== String(env.TELEGRAM_CHAT_ID) || !data.startsWith("focus:")) {
    return new Response("ok");
  }

  const callbackId = String(query.id || "");
  const catalog = await loadFocusCatalog(env);
  const maxSelected = Number(catalog.rules?.max_selected || 2);
  const ttlMinutes = Number(catalog.rules?.selection_ttl_minutes || 15);
  let selected = await readFocusSelection(env, chatId);

  if (data === "focus:open") {
    if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId });
    await showFocusMenu(env, chatId);
    return new Response("ok");
  }

  if (data === "focus:cancel") {
    await env.PAIRING_STATE.delete(focusSelectionKey(chatId));
    if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId, text: "Weekly focus selection cancelled." });
    if (messageId) {
      await telegram(env, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: "Weekly focus selection cancelled.",
      });
    }
    return new Response("ok");
  }

  if (data.startsWith("focus:toggle:")) {
    const slug = data.slice("focus:toggle:".length);
    const area = catalog.areas.find(item => item.slug === slug);
    if (!area) {
      if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId, text: "Unknown area." });
      return new Response("ok");
    }
    if (selected.includes(slug)) {
      selected = selected.filter(item => item !== slug);
    } else if (selected.length >= maxSelected) {
      if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId, text: `Select maximum ${maxSelected} areas.` });
      return new Response("ok");
    } else {
      selected = [...selected, slug];
    }
    await writeFocusSelection(env, chatId, selected, ttlMinutes);
    if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId });
    if (messageId) await showFocusMenu(env, chatId, messageId);
    return new Response("ok");
  }

  if (data === "focus:apply") {
    if (!selected.length) {
      if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId, text: "Select at least one area first." });
      return new Response("ok");
    }
    await env.PAIRING_STATE.put(ACTIVE_FOCUS_KEY, JSON.stringify(selected));
    await env.PAIRING_STATE.delete(focusSelectionKey(chatId));
    const names = catalog.areas.filter(area => selected.includes(area.slug)).map(area => area.name);
    if (callbackId) await telegram(env, "answerCallbackQuery", { callback_query_id: callbackId, text: "Weekly focus updated." });
    if (messageId) {
      await telegram(env, "editMessageText", {
        chat_id: chatId,
        message_id: messageId,
        text: `✅ Weekly focus active: ${names.join(" + ")}\nArea aliases and saved micro-localities will be injected into every Property Monitor run for the current Sunday–Saturday week.`,
      });
    }
    return new Response("ok");
  }

  return new Response("ok");
}

async function dispatchTelegram(update: TelegramUpdate, env: Env): Promise<Response> {
  if (update.callback_query) return dispatchFocusCallback(update, env);

  const message = update.message || update.edited_message;
  const chatId = String(message?.chat?.id || "");
  if (!message || chatId !== String(env.TELEGRAM_CHAT_ID)) return new Response("ok");

  const updateKey = `telegram-update:${update.update_id}`;
  if (await env.PAIRING_STATE.get(updateKey)) return new Response("ok");
  await env.PAIRING_STATE.put(updateKey, "1", { expirationTtl: 86400 });

  const text = String(message.caption || message.text || "").trim();
  if (/^\/focus(?:@\w+)?$/i.test(text) || text === "🎯 Weekly Focus") {
    await showFocusMenu(env, chatId);
    return new Response("ok");
  }

  const explicit = extractVideoId(text);
  const attachment = videoAttachment(message);

  if (!attachment) {
    if (!explicit) return new Response("ok");
    await env.PAIRING_STATE.put(`pending-id:${chatId}`, explicit, { expirationTtl: 900 });
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: `✅ VIDEO_ID saved: ${explicit}\nSend the MP4 within 15 minutes. It will publish immediately after pairing.`,
      reply_markup: {
        inline_keyboard: [[{ text: "🎯 Weekly Focus", callback_data: "focus:open" }]],
      },
    });
    return new Response("ok");
  }

  const videoId = explicit || await env.PAIRING_STATE.get(`pending-id:${chatId}`);
  if (!videoId) {
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: "⚠️ Pairing failed. Send the exact 11-character VIDEO_ID, then resend the MP4 within 15 minutes. Nothing was published.",
    });
    return new Response("ok");
  }

  message.caption = `VIDEO_ID: ${videoId}`;
  const response = await githubDispatch(env, "telegram-property-upload", { update });

  if (!response.ok) {
    const detail = (await response.text()).slice(0, 300);
    await env.PAIRING_STATE.delete(updateKey);
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: `⚠️ Upload paired to ${videoId}, but GitHub publishing could not start: ${response.status}. Please resend the MP4.`,
    });
    console.error("Telegram GitHub dispatch failed", response.status, detail);
    return new Response("dispatch failed", { status: 502 });
  }

  await env.PAIRING_STATE.delete(`pending-id:${chatId}`);
  await telegram(env, "sendMessage", {
    chat_id: chatId,
    text: `✅ ${videoId} paired. Live publishing started immediately. Duplicate protection is active.`,
    reply_markup: {
      inline_keyboard: [[{ text: "🎯 Weekly Focus", callback_data: "focus:open" }]],
    },
  });
  return new Response("ok");
}

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
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/weekly-focus-config") {
      const catalog = await loadFocusCatalog(env);
      const selected = await readJsonList(env, ACTIVE_FOCUS_KEY);
      if (!selected.length) return new Response("No active weekly focus", { status: 404 });
      return new Response(JSON.stringify(buildWeeklyFocusConfig(catalog, selected)), {
        headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
      });
    }
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