import assert from "node:assert/strict";
import { test, afterEach } from "node:test";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";

const source = readFileSync(new URL("../src/index.ts", import.meta.url), "utf8");
const code = stripTypeScriptTypes(source);
const worker = (await import("data:text/javascript;base64," + Buffer.from(code).toString("base64"))).default;
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

function harness(status = 204) {
  const state = new Map();
  const dispatched = [];
  const notifications = [];
  globalThis.fetch = async (url, options) => {
    const payload = JSON.parse(options.body);
    if (String(url).startsWith("https://api.github.com/")) {
      dispatched.push(payload);
      return new Response(status === 204 ? null : "permission denied", { status });
    }
    assert.ok(String(url).startsWith("https://api.telegram.org/"));
    notifications.push(payload);
    return new Response('{"ok":true}');
  };
  const env = {
    TELEGRAM_CHAT_ID: "123", TELEGRAM_BOT_TOKEN: "test",
    GITHUB_REPOSITORY: "owner/repo", GITHUB_DISPATCH_TOKEN: "test",
    PAIRING_STATE: {
      get: async key => state.get(key) ?? null,
      put: async (key, value) => { state.set(key, value); },
      delete: async key => { state.delete(key); },
    },
  };
  const send = (id, message) => worker.fetch(new Request("https://worker.test/", {
    method: "POST", body: JSON.stringify({ update_id: id, message: { chat: { id: 123 }, ...message } }),
  }), env);
  return { state, dispatched, notifications, send };
}

test("captioned Interior upload preserves its ID and uses only the Interior event", async () => {
  const h = harness();
  assert.equal((await h.send(1, { caption: "INTERIOR_ID: SybwGjg5-Ds", video: {} })).status, 200);
  assert.equal(h.dispatched.length, 1);
  assert.equal(h.dispatched[0].event_type, "telegram-interior-upload");
  assert.equal(h.dispatched[0].client_payload.update.message.caption, "INTERIOR_ID: SybwGjg5-Ds");
});

test("Interior ID followed by an uncaptioned MP4 retains Interior routing", async () => {
  const h = harness();
  await h.send(1, { text: "INTERIOR_ID: SybwGjg5-Ds" });
  assert.equal(h.state.get("pending-id:123"), "INTERIOR_ID: SybwGjg5-Ds");
  await h.send(2, { document: { file_name: "upload.MP4" } });
  assert.equal(h.dispatched[0].event_type, "telegram-interior-upload");
  assert.equal(h.dispatched[0].client_payload.update.message.caption, "INTERIOR_ID: SybwGjg5-Ds");
  assert.equal(h.state.has("pending-id:123"), false);
});

test("explicit Property ID overrides a pending Interior pairing", async () => {
  const h = harness();
  await h.send(1, { text: "INTERIOR_ID: SybwGjg5-Ds" });
  await h.send(2, { caption: "VIDEO_ID: Fs9ObmoAxhY", video: {} });
  assert.equal(h.dispatched[0].event_type, "telegram-property-upload");
  assert.equal(h.dispatched[0].client_payload.update.message.caption, "VIDEO_ID: Fs9ObmoAxhY");
});

test("bare pending IDs from older deployments still publish as Property", async () => {
  const h = harness();
  h.state.set("pending-id:123", "Fs9ObmoAxhY");
  await h.send(1, { video: {} });
  assert.equal(h.dispatched[0].event_type, "telegram-property-upload");
});

test("unauthorized chat and an unpaired video never dispatch", async () => {
  const h = harness();
  await h.send(1, { chat: { id: 456 }, caption: "INTERIOR_ID: SybwGjg5-Ds", video: {} });
  await h.send(2, { video: {} });
  assert.equal(h.dispatched.length, 0);
});

test("replayed successful Telegram update does not dispatch twice", async () => {
  const h = harness();
  const message = { caption: "INTERIOR_ID: SybwGjg5-Ds", video: {} };
  await h.send(1, message);
  await h.send(1, message);
  assert.equal(h.dispatched.length, 1);
});

test("403 returns 200 and retains duplicate protection and a single warning", async () => {
  const h = harness(403);
  const message = { caption: "INTERIOR_ID: SybwGjg5-Ds", video: {} };
  assert.equal((await h.send(1, message)).status, 200);
  assert.equal((await h.send(1, message)).status, 200);
  assert.equal(h.dispatched.length, 1);
  assert.equal(h.notifications.length, 1);
  assert.equal(h.state.get("telegram-update:1"), "1");
});
