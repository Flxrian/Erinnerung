// Server-Teil des Tätigkeitsbericht-Generators (Netlify Function + Netlify Blobs).
//
// Gespeichert werden:
//   users/<id>       Kontodaten: Anzeigename, Salt, verschlüsselte Datenschlüssel, Passwort-Prüfwert, Zugang
//   data/<id>        die Berichte des Kontos – im Browser mit AES-256 verschlüsselt, der Server kann sie nicht lesen
//   keys/issued/<n>  vom Admin erstellte Zugangskeys
//   keys/used/<n>    eingelöste Zugangskeys (jeder Key nur einmal, atomar über onlyIfNew)
//
// Der Server kennt weder Passwörter noch Datenschlüssel. Admin-Anfragen sind mit dem Admin-Signaturschlüssel
// (ECDSA P-256) unterschrieben; der Server prüft sie mit dem öffentlichen Schlüssel.
import { getStore } from '@netlify/blobs';
import crypto from 'node:crypto';

const ADMIN_ID = "0798fde18d50";
const SIG_PUB = "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEIzFcBW8Oo5Zgo9TbJboFZ85f2gaQg9x4vD1lyeAiDG6LRLAeqghsXf5qd5/1gElcvrbMX98gTUbRpnuFeOphyA==";
const MAX_DATA = 4 * 1024 * 1024;        // max. Größe der verschlüsselten Berichte pro Konto
const MAX_FAILS = 10, LOCK_MS = 15 * 60 * 1000;
const ADMIN_WINDOW_MS = 5 * 60 * 1000;

const store = () => globalThis.__TB_STORE__ || getStore({ name: 'taetigkeitsbericht', consistency: 'strong' });
const json = (status, body) => new Response(JSON.stringify(body), {
  status, headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }
});
class HttpError extends Error { constructor(status, code, extra) { super(code); this.status = status; this.code = code; this.extra = extra; } }
const fail = (status, code, extra) => { throw new HttpError(status, code, extra); };

const sha = s => crypto.createHash('sha256').update(String(s)).digest('hex');
const sameHash = (a, b) => typeof a === 'string' && typeof b === 'string' && a.length === b.length && crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
const today = () => new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin' }).format(new Date());
function addMonths(iso, m) {
  const [y, mo, d] = iso.split('-').map(Number), x = new Date(Date.UTC(y, mo - 1 + m, d));
  return x.toISOString().slice(0, 10);
}

// ---------- Eingaben prüfen ----------
function userId(u) {
  if (typeof u !== 'string') fail(400, 'bad_user');
  const id = u.trim().toLowerCase();
  if (!id || id.length > 60 || /[\u0000-\u001f\/\\]/.test(id)) fail(400, 'bad_user');
  return id;
}
const ukey = id => 'users/' + encodeURIComponent(id);
const dkey = id => 'data/' + encodeURIComponent(id);
const isB64 = (s, max = 4096) => typeof s === 'string' && s.length <= max && /^[A-Za-z0-9+/=_-]*$/.test(s);
const isCipher = (o, max = 4096) => o && typeof o === 'object' && isB64(o.iv, 64) && isB64(o.ct, max);
function str(s, max) { if (typeof s !== 'string' || s.length > max) fail(400, 'bad_input'); return s; }

// ---------- Speicher ----------
async function getMeta(id) {
  const r = await store().getWithMetadata(ukey(id), { type: 'json' });
  return r ? { meta: r.data, etag: r.etag } : null;
}
// Kontodaten ändern; bei gleichzeitigen Änderungen wird neu gelesen und wiederholt
async function updateMeta(id, change) {
  for (let i = 0; i < 5; i++) {
    const cur = await getMeta(id);
    if (!cur) fail(404, 'no_user');
    const next = change({ ...cur.meta });
    const res = await store().setJSON(ukey(id), next, { onlyIfMatch: cur.etag });
    if (res.modified) return next;
  }
  fail(409, 'busy');
}
async function authed(body) {
  const id = userId(body.u);
  const cur = await getMeta(id);
  if (!cur || !sameHash(sha(str(body.auth, 200)), cur.meta.authHash)) fail(401, 'auth');
  return { id, meta: cur.meta };
}
const publicAccess = a => a ? { until: a.until ?? null, n: a.n || null, legacy: !!a.legacy } : null;

// ---------- Zugangskeys ----------
const b64u = s => Buffer.from(s.replace(/-/g, '+').replace(/_/g, '/'), 'base64');
function verifySigned(data, sigB64u) {
  return crypto.verify('sha256', Buffer.from(data), { key: Buffer.from(SIG_PUB, 'base64'), format: 'der', type: 'spki', dsaEncoding: 'ieee-p1363' }, b64u(sigB64u));
}
function parseKey(key) {
  const m = /^TB([12])-([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)$/.exec(String(key || '').replace(/\s+/g, ''));
  if (!m || !verifySigned(m[2], m[3])) return null;
  try { return { v: +m[1], p: JSON.parse(b64u(m[2]).toString('utf8')), key: `TB${m[1]}-${m[2]}.${m[3]}` }; } catch { return null; }
}

// ---------- Endpunkte ----------
const routes = {
  async health() { return { ok: true, v: 1 }; },

  async salt(b) {
    const cur = await getMeta(userId(b.u));
    return cur ? { exists: true, salt: cur.meta.salt } : { exists: false };
  },

  async register(b) {
    const id = userId(b.u);
    const name = str(b.name, 80).trim() || id;
    if (!isB64(b.salt, 64) || !isCipher(b.wrapPw, 256) || !isB64(b.auth, 200)) fail(400, 'bad_input');
    if (b.data && (!isCipher(b.data, MAX_DATA))) fail(400, 'bad_input');
    const now = Date.now();
    const meta = {
      name, created: Number(b.created) || now, salt: b.salt, wrapPw: b.wrapPw,
      wrapAdmin: isB64(b.wrapAdmin, 1024) ? b.wrapAdmin : null, adminId: b.adminId === ADMIN_ID ? ADMIN_ID : null,
      authHash: sha(b.auth), access: null, fails: 0, lockUntil: 0, lastLogin: now
    };
    const res = await store().setJSON(ukey(id), meta, { onlyIfNew: true });
    if (!res.modified) fail(409, 'exists');
    await store().setJSON(dkey(id), { data: b.data || null, rev: 1, updated: now });
    return { ok: true, rev: 1 };
  },

  async login(b) {
    const id = userId(b.u);
    const cur = await getMeta(id);
    if (!cur) fail(401, 'auth');
    if (cur.meta.lockUntil > Date.now()) fail(429, 'locked', { until: cur.meta.lockUntil });
    if (!sameHash(sha(str(b.auth, 200)), cur.meta.authHash)) {
      await updateMeta(id, m => { m.fails = (m.fails || 0) + 1; if (m.fails >= MAX_FAILS) { m.lockUntil = Date.now() + LOCK_MS; m.fails = 0; } return m; });
      fail(401, 'auth');
    }
    const meta = await updateMeta(id, m => { m.fails = 0; m.lockUntil = 0; m.lastLogin = Date.now(); return m; });
    const d = await store().get(dkey(id), { type: 'json' }) || { data: null, rev: 0 };
    return {
      name: meta.name, created: meta.created, wrapPw: meta.wrapPw, adminId: meta.adminId,
      access: publicAccess(meta.access), data: d.data, rev: d.rev
    };
  },

  async save(b) {
    const { id } = await authed(b);
    if (!isCipher(b.data, MAX_DATA)) fail(400, 'bad_input');
    const cur = await store().getWithMetadata(dkey(id), { type: 'json' });
    const curRev = cur ? cur.data.rev : 0;
    if (Number(b.rev) !== curRev) fail(409, 'conflict', { data: cur ? cur.data.data : null, rev: curRev });
    const next = { data: b.data, rev: curRev + 1, updated: Date.now() };
    const res = cur ? await store().setJSON(dkey(id), next, { onlyIfMatch: cur.etag }) : await store().setJSON(dkey(id), next, { onlyIfNew: true });
    if (!res.modified) {
      const now = await store().get(dkey(id), { type: 'json' });
      fail(409, 'conflict', { data: now ? now.data : null, rev: now ? now.rev : 0 });
    }
    return { rev: next.rev };
  },

  async meta(b) {
    const { id } = await authed(b);
    if (b.adminId !== ADMIN_ID || !isB64(b.wrapAdmin, 1024)) fail(400, 'bad_input');
    await updateMeta(id, m => { m.wrapAdmin = b.wrapAdmin; m.adminId = ADMIN_ID; return m; });
    return { ok: true };
  },

  async password(b) {
    const { id } = await authed(b);
    if (!isB64(b.salt, 64) || !isCipher(b.wrapPw, 256) || !isB64(b.newAuth, 200)) fail(400, 'bad_input');
    await updateMeta(id, m => { m.salt = b.salt; m.wrapPw = b.wrapPw; m.authHash = sha(b.newAuth); return m; });
    return { ok: true };
  },

  async deleteMe(b) {
    const { id } = await authed(b);
    await store().delete(ukey(id)); await store().delete(dkey(id));
    return { ok: true };
  },

  async redeem(b) {
    const { id, meta } = await authed(b);
    const k = parseKey(b.key);
    if (!k) fail(400, 'key_invalid');
    const t = today();
    if (k.v === 1) {   // ältere Keys mit Benutzername und festem Ablaufdatum
      if (k.p.u !== id) fail(400, 'key_other_user', { owner: k.p.u });
      if (k.p.e && k.p.e < t) fail(400, 'key_expired', { until: k.p.e });
      const m = await updateMeta(id, x => { x.access = { key: k.key, until: k.p.e || null, legacy: true, at: Date.now() }; return x; });
      return { access: publicAccess(m.access) };
    }
    const n = String(k.p.n || ''), months = Number(k.p.m) || 0;
    if (!/^[A-Za-z0-9_-]{4,32}$/.test(n)) fail(400, 'key_invalid');
    const used = await store().setJSON('keys/used/' + n, { by: id, at: Date.now(), m: months }, { onlyIfNew: true });
    if (!used.modified) fail(409, 'key_used');
    const m = await updateMeta(id, x => {
      const a = x.access;
      let until;
      if (a && a.until === null && !a.legacy) until = null;                       // schon unbegrenzt
      else if (!months) until = null;                                             // unbegrenzter Key
      else until = addMonths(a && a.until && a.until >= t ? a.until : t, months);  // verlängert ab Ende des laufenden Zugangs
      x.access = { key: k.key, n, until, at: Date.now() };
      return x;
    });
    return { access: publicAccess(m.access) };
  },

  async admin(b) {
    if (typeof b.msg !== 'string' || typeof b.sig !== 'string' || b.msg.length > 20000) fail(400, 'bad_input');
    let ok = false; try { ok = verifySigned(b.msg, b.sig); } catch { ok = false; }
    if (!ok) fail(401, 'admin_auth');
    const { action, ts, body = {} } = JSON.parse(b.msg);
    if (Math.abs(Date.now() - Number(ts)) > ADMIN_WINDOW_MS) fail(401, 'admin_expired');
    const s = store();
    switch (action) {
      case 'list': {
        const { blobs } = await s.list({ prefix: 'users/' });
        const users = [];
        for (const { key } of blobs) {
          const m = await s.get(key, { type: 'json' }); if (!m) continue;
          users.push({ id: decodeURIComponent(key.slice(6)), name: m.name, created: m.created, lastLogin: m.lastLogin,
            resettable: m.adminId === ADMIN_ID && !!m.wrapAdmin, access: publicAccess(m.access), locked: m.lockUntil > Date.now() });
        }
        const issued = (await s.list({ prefix: 'keys/issued/' })).blobs;
        const keys = [];
        for (const { key } of issued) {
          const n = key.slice(12), i = await s.get(key, { type: 'json' }), u = await s.get('keys/used/' + n, { type: 'json' });
          keys.push({ n, m: i?.m ?? 0, d: i?.d || '', usedBy: u?.by || null, usedAt: u?.at || null });
        }
        return { users, keys };
      }
      case 'wrap': {
        const cur = await getMeta(userId(body.u)); if (!cur) fail(404, 'no_user');
        return { wrapAdmin: cur.meta.wrapAdmin, adminId: cur.meta.adminId };
      }
      case 'reset': {
        const id = userId(body.u);
        if (!isB64(body.salt, 64) || !isCipher(body.wrapPw, 256) || !isB64(body.auth, 200)) fail(400, 'bad_input');
        await updateMeta(id, m => { m.salt = body.salt; m.wrapPw = body.wrapPw; m.authHash = sha(body.auth); m.fails = 0; m.lockUntil = 0; return m; });
        return { ok: true };
      }
      case 'delete': {
        const id = userId(body.u);
        await s.delete(ukey(id)); await s.delete(dkey(id));
        return { ok: true };
      }
      case 'issue': {
        const n = String(body.n || '');
        if (!/^[A-Za-z0-9_-]{4,32}$/.test(n)) fail(400, 'bad_input');
        await s.setJSON('keys/issued/' + n, { m: Number(body.m) || 0, d: String(body.d || '').slice(0, 10), at: Date.now() });
        return { ok: true };
      }
      default: fail(400, 'bad_action');
    }
  }
};

export default async (req) => {
  const name = new URL(req.url).pathname.replace(/^\/api\/?/, '').replace(/\/$/, '');
  const route = routes[name];
  if (!route) return json(404, { error: 'not_found' });
  if (req.method !== 'POST' && name !== 'health') return json(405, { error: 'method' });
  try {
    const body = req.method === 'POST' ? await req.json().catch(() => fail(400, 'bad_json')) : {};
    return json(200, await route(body || {}));
  } catch (e) {
    if (e instanceof HttpError) return json(e.status, { error: e.code, ...(e.extra || {}) });
    console.error(e);
    return json(500, { error: 'server' });
  }
};

export const config = { path: '/api/*' };
