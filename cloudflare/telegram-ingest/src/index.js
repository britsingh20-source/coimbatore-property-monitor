export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("Not found", { status: 404 });
    const url = new URL(request.url);
    if (url.pathname !== `/telegram/${env.WEBHOOK_SECRET}`) {
      return new Response("Not found", { status: 404 });
    }

    let update;
    try { update = await request.json(); }
    catch { return new Response("Bad request", { status: 400 }); }

    const message = update.message;
    const chatId = String(message?.chat?.id || "");
    if (!message || chatId !== String(env.TELEGRAM_CHAT_ID)) {
      return new Response("ok");
    }

    const updateKey = `update:${update.update_id}`;
    if (await env.PAIRING_STATE.get(updateKey)) return new Response("ok");
    await env.PAIRING_STATE.put(updateKey, "1", { expirationTtl: 86400 });

    const text = String(message.caption || message.text || "").trim();
    const explicit = extractVideoId(text);
    const attachment = videoAttachment(message);

    if (!attachment) {
      if (!explicit) return new Response("ok");
      await env.PAIRING_STATE.put(`pending-id:${chatId}`, explicit, { expirationTtl: 900 });
      await telegram(env, "sendMessage", {
        chat_id: chatId,
        text: `✅ VIDEO_ID saved: ${explicit}\nSend the MP4 within 15 minutes. It will be paired before publishing.`,
      });
      return new Response("ok");
    }

    const videoId = explicit || await env.PAIRING_STATE.get(`pending-id:${chatId}`);
    if (!videoId) {
      await telegram(env, "sendMessage", {
        chat_id: chatId,
        text: "⚠️ Pairing failed immediately. Send the exact 11-character VIDEO_ID, then resend the MP4 within 15 minutes. Nothing was published.",
      });
      return new Response("ok");
    }

    message.caption = `VIDEO_ID: ${videoId}`;
    const dispatched = await fetch(
      `https://api.github.com/repos/${env.GITHUB_REPOSITORY}/dispatches`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
          "Accept": "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "User-Agent": "coimbatore-property-telegram-worker",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          event_type: "telegram-property-upload",
          client_payload: { update },
        }),
      },
    );

    if (!dispatched.ok) {
      const detail = (await dispatched.text()).slice(0, 300);
      await telegram(env, "sendMessage", {
        chat_id: chatId,
        text: `⚠️ Upload received and paired to ${videoId}, but publishing could not start. Nothing was reposted. GitHub dispatch: ${dispatched.status} ${detail}`,
      });
      return new Response("dispatch failed", { status: 502 });
    }

    await env.PAIRING_STATE.delete(`pending-id:${chatId}`);
    await telegram(env, "sendMessage", {
      chat_id: chatId,
      text: `✅ Upload paired exactly to ${videoId}. Live social publishing started. Duplicate protection is active.`,
    });
    return new Response("ok");
  },
};

function extractVideoId(text) {
  const labelled = text.match(/(?:video[\\s_-]*id|id)[\\s:=_-]+([A-Za-z0-9_-]{11})/i);
  if (labelled) return labelled[1];
  return /^[A-Za-z0-9_-]{11}$/.test(text) ? text : "";
}

function videoAttachment(message) {
  if (message.video) return message.video;
  const doc = message.document;
  const mime = String(doc?.mime_type || "").toLowerCase();
  const name = String(doc?.file_name || "").toLowerCase();
  return doc && (mime.startsWith("video/") || name.endsWith(".mp4")) ? doc : null;
}

async function telegram(env, method, body) {
  const response = await fetch(`https://api.telegram.org/bot${env.TELEGRAM_BOT_TOKEN}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Telegram ${method} failed: ${response.status}`);
}
