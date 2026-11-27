// Site Visit Board API — shared day-by-day site visits for the sales team.
// Storage: D1 "coimbatore-lead-crm", tables site_visits + site_visit_settings.
// Every request except the health check needs the shared PIN in the X-Pin header.
// After 10 wrong PINs the board locks for 15 minutes.

const MAX_FAILS = 10;
const LOCK_MS = 15 * 60 * 1000;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;
const ID_RE = /^[a-z0-9]{6,32}$/;

function cors(request, env) {
  const origin = request.headers.get("Origin") || "";
  const allowed = String(env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean);
  const ok = allowed.includes(origin) || /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin);
  return {
    "Access-Control-Allow-Origin": ok ? origin : allowed[0] || "*",
    "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type,X-Pin",
    "Access-Control-Max-Age": "86400",
    Vary: "Origin",
  };
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers },
  });
}

async function sha256(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function checkPin(env, pin) {
  const row = await env.DB.prepare("SELECT pin_hash, failed_attempts, locked_until FROM site_visit_settings WHERE id = 1").first();
  if (!row) return "not_configured";
  const now = Date.now();
  if (row.locked_until > now) return "locked";
  const good = pin && (await sha256("site-visits:" + String(pin).trim())) === row.pin_hash;
  if (good) {
    if (row.failed_attempts) await env.DB.prepare("UPDATE site_visit_settings SET failed_attempts = 0 WHERE id = 1").run();
    return "ok";
  }
  const fails = row.failed_attempts + 1;
  const lock = fails >= MAX_FAILS ? now + LOCK_MS : 0;
  await env.DB.prepare("UPDATE site_visit_settings SET failed_attempts = ?, locked_until = ? WHERE id = 1")
    .bind(lock ? 0 : fails, lock).run();
  return lock ? "locked" : "pin";
}

const clean = (v, max) => String(v == null ? "" : v).trim().slice(0, max);

function toVisit(r) {
  return {
    id: r.id, date: r.visit_date, time: r.visit_time, name: r.name, phone: r.phone,
    area: r.area || "", place: r.place, note: r.note, by: r.added_by, done: !!r.done, created: r.created_at,
  };
}

export default {
  async fetch(request, env) {
    const h = cors(request, env);
    const url = new URL(request.url);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: h });
    if (url.pathname === "/" && request.method === "GET") {
      return new Response("coimbatore-site-visits-api: healthy", { headers: h });
    }
    if (!url.pathname.startsWith("/visits")) return json({ ok: false, error: "not_found" }, 404, h);

    try {
      const auth = await checkPin(env, request.headers.get("X-Pin"));
      if (auth !== "ok") return json({ ok: false, error: auth }, auth === "locked" ? 429 : 401, h);

      // Area list from the CRM: main areas (area_master) first, then every other active area
      if (request.method === "GET" && url.pathname === "/visits/areas") {
        const main = await env.DB.prepare("SELECT canonical_name AS name FROM area_master WHERE active = 1 ORDER BY CASE WHEN priority_band = 'P1' THEN 0 ELSE 1 END, canonical_name").all();
        const all = await env.DB.prepare("SELECT name FROM areas WHERE active = 1 ORDER BY name").all();
        const mainNames = main.results.map((r) => r.name);
        const rest = all.results.map((r) => r.name).filter((n) => !mainNames.includes(n));
        return json({ ok: true, main: mainNames, other: rest }, 200, h);
      }

      // List: last 60 days and everything ahead
      if (request.method === "GET" && url.pathname === "/visits") {
        const from = new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 10);
        const { results } = await env.DB.prepare(
          "SELECT * FROM site_visits WHERE visit_date >= ? ORDER BY visit_date, visit_time, created_at LIMIT 2000"
        ).bind(from).all();
        return json({ ok: true, visits: results.map(toVisit) }, 200, h);
      }

      // Add or update one visit
      if (request.method === "POST" && url.pathname === "/visits") {
        const b = await request.json().catch(() => null);
        const v = b && b.visit;
        if (!v) return json({ ok: false, error: "missing" }, 400, h);
        const id = clean(v.id, 32);
        const date = clean(v.date, 10);
        const time = clean(v.time, 5);
        const name = clean(v.name, 80);
        const phone = clean(v.phone, 20);
        if (!ID_RE.test(id) || !DATE_RE.test(date) || (time && !TIME_RE.test(time)) || !name || phone.replace(/\D/g, "").length < 6) {
          return json({ ok: false, error: "missing" }, 400, h);
        }
        await env.DB.prepare(
          `INSERT INTO site_visits (id, visit_date, visit_time, name, phone, place, note, added_by, done, created_at, area, updated_at)
           VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, CURRENT_TIMESTAMP)
           ON CONFLICT(id) DO UPDATE SET visit_date = ?2, visit_time = ?3, name = ?4, phone = ?5, place = ?6,
             note = ?7, done = ?9, area = ?11, updated_at = CURRENT_TIMESTAMP`
        ).bind(id, date, time, name, phone, clean(v.place, 100), clean(v.note, 400), clean(v.by, 30),
          v.done ? 1 : 0, Number(v.created) || Date.now(), clean(v.area, 60)).run();
        return json({ ok: true }, 200, h);
      }

      // Delete one visit
      const m = url.pathname.match(/^\/visits\/([a-z0-9]{6,32})$/);
      if (request.method === "DELETE" && m) {
        await env.DB.prepare("DELETE FROM site_visits WHERE id = ?").bind(m[1]).run();
        return json({ ok: true }, 200, h);
      }
      return json({ ok: false, error: "not_found" }, 404, h);
    } catch (err) {
      return json({ ok: false, error: "server" }, 500, h);
    }
  },
};
