// Run: node --test cloudflare/site-visits/tests/api.test.mjs  (Node 22+, uses built-in node:sqlite)
import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { createHash } from "node:crypto";
import worker from "../src/index.js";

function makeDB() {
  const db = new DatabaseSync(":memory:");
  db.exec(`CREATE TABLE site_visits (id TEXT PRIMARY KEY, visit_date TEXT NOT NULL, visit_time TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL, phone TEXT NOT NULL, place TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
    added_by TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, area TEXT NOT NULL DEFAULT '');
    CREATE TABLE area_master (code TEXT PRIMARY KEY, canonical_name TEXT, priority_band TEXT, active INTEGER);
    CREATE TABLE areas (code TEXT PRIMARY KEY, name TEXT, active INTEGER);
    INSERT INTO area_master VALUES ('SRV','Saravanampatti',NULL,1),('IDG','Idigarai','P1',1);
    INSERT INTO areas VALUES ('IDG','Idigarai',1),('ANR','Annur',1),('RSP','RS Puram',0);
    CREATE TABLE site_visit_settings (id INTEGER PRIMARY KEY CHECK (id = 1), pin_hash TEXT NOT NULL,
    failed_attempts INTEGER NOT NULL DEFAULT 0, locked_until INTEGER NOT NULL DEFAULT 0, updated_at TEXT);`);
  const hash = createHash("sha256").update("site-visits:123456").digest("hex");
  db.prepare("INSERT INTO site_visit_settings (id, pin_hash) VALUES (1, ?)").run(hash);
  const wrap = (sql) => {
    const st = db.prepare(sql.replace(/\?(\d+)/g, "?"));
    const pos = [...sql.matchAll(/\?(\d+)/g)].map((m) => Number(m[1]) - 1);
    let args = [];
    const a = () => (pos.length ? pos.map((i) => args[i]) : args);
    const api = {
      bind: (...x) => { args = x; return api; },
      first: async () => st.get(...a()) ?? null,
      all: async () => ({ results: st.all(...a()) }),
      run: async () => st.run(...a()),
    };
    return api;
  };
  return { prepare: wrap };
}

const env = { DB: makeDB(), ALLOWED_ORIGINS: "https://britsingh20-source.github.io" };
const call = (path, init = {}) => worker.fetch(new Request("https://x.dev" + path, init), env);
const pinH = { "X-Pin": "123456", Origin: "https://britsingh20-source.github.io" };

test("health and wrong pin", async () => {
  assert.equal(await (await call("/")).text(), "coimbatore-site-visits-api: healthy");
  const r = await call("/visits", { headers: { "X-Pin": "000000" } });
  assert.equal(r.status, 401);
});

test("add, list, update, delete", async () => {
  const today = new Date().toISOString().slice(0, 10);
  const v = { id: "abc123xyz", date: today, time: "10:30", name: "Ramesh", phone: "9876543210", area: "Idigarai", place: "Near temple", by: "Bright", done: false, created: 1 };
  let r = await call("/visits", { method: "POST", headers: pinH, body: JSON.stringify({ visit: v }) });
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), "https://britsingh20-source.github.io");
  r = await (await call("/visits", { headers: pinH })).json();
  assert.equal(r.visits.length, 1);
  assert.equal(r.visits[0].by, "Bright");
  assert.equal(r.visits[0].area, "Idigarai");
  await call("/visits", { method: "POST", headers: pinH, body: JSON.stringify({ visit: { ...v, done: true, by: "Someone else" } }) });
  r = await (await call("/visits", { headers: pinH })).json();
  assert.equal(r.visits[0].done, true);
  assert.equal(r.visits[0].by, "Bright", "added_by never changes on edit");
  assert.equal((await call("/visits/abc123xyz", { method: "DELETE", headers: pinH })).status, 200);
  r = await (await call("/visits", { headers: pinH })).json();
  assert.equal(r.visits.length, 0);
});

test("area list: main first, Idigarai on top, inactive hidden", async () => {
  const r = await (await call("/visits/areas", { headers: pinH })).json();
  assert.deepEqual(r.main, ["Idigarai", "Saravanampatti"]);
  assert.deepEqual(r.other, ["Annur"]);
});

test("bad input rejected", async () => {
  const r = await call("/visits", { method: "POST", headers: pinH, body: JSON.stringify({ visit: { id: "abc123xyz", date: "tomorrow", name: "x", phone: "1" } }) });
  assert.equal(r.status, 400);
});

test("locks after 10 wrong pins", async () => {
  let r;
  for (let i = 0; i < 10; i++) r = await call("/visits", { headers: { "X-Pin": "999999" } });
  assert.equal(r.status, 429);
  r = await call("/visits", { headers: pinH });
  assert.equal(r.status, 429, "even the right PIN waits during the lock");
});
