// UCP (Universal Commerce Protocol, version 2026-04-08) checkout for HALLUX credit packs.
//
// What is real here and what is not:
//   - The catalog is the three live HALLUX packs, read from the live billing API.
//   - An agent can create, read, update and cancel a checkout session over REST.
//   - Payment is PayPal, taken by the buyer in their own browser. No UCP payment
//     credential can complete the purchase server-side, so `complete` answers
//     `requires_escalation` with a `continue_url`. That page creates the PayPal
//     order through the live billing API, the buyer approves it, and the capture
//     is verified server-side (amount and credits) before the session reads
//     `completed`. This Worker never sees card data and never stores an API key:
//     the buyer's new key is shown only in the buyer's browser.
//
// Sessions live in KV (binding COMMERCE) for six hours, or thirty days once
// completed.

export const UCP_VERSION = "2026-04-08";
const SPEC = "https://ucp.dev/" + UCP_VERSION + "/specification/checkout";
const REST_SCHEMA = "https://ucp.dev/" + UCP_VERSION + "/services/shopping/rest.openapi.json";
const CHECKOUT_SCHEMA = "https://ucp.dev/" + UCP_VERSION + "/schemas/shopping/checkout.json";
const HANDLER = "com.paypal.checkout";
const SESSION_TTL = 6 * 3600;
const DONE_TTL = 30 * 86400;

const api = (env) => (env.HALLUX_API || "https://api.blvkware.dev/hallux").replace(/\/+$/, "");
const callApi = (env, path, init) => (env.HALLUX && !env.HALLUX_API ? env.HALLUX.fetch(api(env) + path, init) : fetch(api(env) + path, init));

const minor = (amount) => Math.round(Number(amount) * 100);

let packCache = null;
async function packs(env) {
  if (packCache && packCache.at > Date.now() - 600000) return packCache.v;
  const r = await callApi(env, "/v1/billing/config", { headers: { accept: "application/json" } });
  const c = await r.json();
  const v = { clientId: c.client_id, currency: c.currency || "USD", items: {} };
  for (const p of c.packs || []) v.items["hallux-" + p.id] = { id: "hallux-" + p.id, pack: p.id, title: p.name, price: minor(p.amount), credits: p.credits };
  packCache = { at: Date.now(), v };
  return v;
}

export async function profile(origin, env) {
  const ucp = {
    version: UCP_VERSION,
    services: { "dev.ucp.shopping": [{ version: UCP_VERSION, spec: "https://ucp.dev/" + UCP_VERSION + "/specification/overview", transport: "rest", endpoint: origin + "/ucp/v1", schema: REST_SCHEMA }] },
    capabilities: { "dev.ucp.shopping.checkout": [{ version: UCP_VERSION, spec: SPEC, schema: CHECKOUT_SCHEMA }] },
    payment_handlers: { [HANDLER]: [{ id: "paypal_buyer_handoff", version: UCP_VERSION, config: { mode: "buyer_handoff", note: "The buyer pays with PayPal at continue_url. complete returns requires_escalation until the capture is verified." } }] },
  };
  const p = await packs(env).catch(() => null);
  return {
    ucp,
    // Flat aliases some discovery scanners read. Same facts as the ucp object above.
    protocol_version: UCP_VERSION,
    services: ["dev.ucp.shopping"],
    capabilities: ["dev.ucp.shopping.checkout"],
    endpoints: { rest: origin + "/ucp/v1", checkout_sessions: origin + "/ucp/v1/checkout-sessions" },
    business: { name: "BlvkWare", url: origin, support: origin + "/legal/" },
    catalog: p ? Object.values(p.items).map((i) => ({ id: i.id, title: i.title, price: i.price, currency: p.currency, credits: i.credits })) : [],
  };
}

// ------------------------------------------------------------------ helpers --

function res(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body, null, 2) + "\n", {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type, ucp-agent, idempotency-key, request-id, authorization",
      "access-control-allow-methods": "GET, POST, PUT, OPTIONS",
      "cache-control": "no-store",
      ...extra,
    },
  });
}

const ucpMeta = (status = "success") => ({
  version: UCP_VERSION,
  status,
  capabilities: { "dev.ucp.shopping.checkout": [{ version: UCP_VERSION }] },
  payment_handlers: { [HANDLER]: [{ id: "paypal_buyer_handoff", version: UCP_VERSION }] },
});

function errorBody(code, content, severity = "recoverable", path) {
  return { ucp: { version: UCP_VERSION, status: "error" }, messages: [{ type: "error", code, content, severity, ...(path ? { path } : {}) }] };
}

function newId() {
  const b = crypto.getRandomValues(new Uint8Array(18));
  return "cs_" + btoa(String.fromCharCode(...b)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

const load = async (env, id) => (/^cs_[A-Za-z0-9_-]{24}$/.test(id) ? env.COMMERCE.get("ucp:" + id, "json") : null);
const save = (env, s) => env.COMMERCE.put("ucp:" + s.id, JSON.stringify(s), { expirationTtl: s.status === "completed" ? DONE_TTL : SESSION_TTL });

// Validate requested line items against the live catalog. One pack per checkout:
// a PayPal order here carries exactly one pack.
async function priceLines(env, lines) {
  const cat = await packs(env);
  if (!Array.isArray(lines) || lines.length !== 1) return { error: errorBody("invalid_line_items", "Send exactly one line item: one HALLUX credit pack per checkout. Items: " + Object.keys(cat.items).join(", "), "recoverable", "$.line_items") };
  const l = lines[0] || {};
  const itemId = l.item && l.item.id;
  const it = cat.items[itemId];
  if (!it) return { error: errorBody("item_unavailable", "Unknown item " + JSON.stringify(itemId) + ". Items: " + Object.keys(cat.items).join(", "), "recoverable", "$.line_items[0].item.id") };
  if ((l.quantity ?? 1) !== 1) return { error: errorBody("invalid_quantity", "Quantity must be 1. Buy a larger pack instead.", "recoverable", "$.line_items[0].quantity") };
  return { currency: cat.currency, item: it };
}

function view(s, origin) {
  const total = s.item.price;
  const out = {
    ucp: ucpMeta(),
    id: s.id,
    line_items: [{ id: "li_1", item: { id: s.item.id, title: s.item.title, price: s.item.price }, quantity: 1, totals: [{ type: "subtotal", amount: total }, { type: "total", amount: total }] }],
    status: s.status,
    currency: s.currency,
    totals: [{ type: "subtotal", display_text: "Subtotal", amount: total }, { type: "total", display_text: "Total", amount: total }],
    links: [
      { type: "terms_of_service", url: origin + "/terms/" },
      { type: "privacy_policy", url: origin + "/privacy/" },
    ],
    expires_at: s.expires_at,
  };
  if (s.buyer) out.buyer = s.buyer;
  const msgs = [];
  if (s.status === "requires_escalation") {
    out.continue_url = origin + "/checkout/ucp/" + s.id;
    msgs.push({ type: "error", code: "buyer_handoff_required", content: "The buyer completes payment with PayPal at continue_url. Poll this session; it reads completed once the capture is verified.", severity: "requires_buyer_input" });
  }
  if (s.status === "completed") {
    out.order = { id: s.order.id, label: s.item.credits.toLocaleString("en-US") + " HALLUX credits", permalink_url: origin + "/checkout/ucp/" + s.id };
    msgs.push({ type: "info", content: s.item.credits.toLocaleString("en-US") + " credits were added to key " + s.order.key_prefix + "…. The full key was shown once to the buyer on the payment page." });
  }
  if (msgs.length) out.messages = msgs;
  return out;
}

// ------------------------------------------------------------------- REST ----

export async function handleUcp(request, env, url) {
  if (request.method === "OPTIONS") return res(null, 204);
  if (!env.COMMERCE) return res(errorBody("unavailable", "Checkout storage is not configured.", "unrecoverable"), 503);
  const origin = url.origin;
  const m = url.pathname.replace(/\/+$/, "").match(/^\/ucp\/v1\/checkout-sessions(?:\/([^/]+))?(?:\/(complete|cancel))?$/);
  if (!m) return res(errorBody("not_found", "Supported: POST /ucp/v1/checkout-sessions, GET|PUT /ucp/v1/checkout-sessions/{id}, POST …/{id}/complete, POST …/{id}/cancel.", "unrecoverable"), 404);
  const [, id, action] = m;
  const body = request.method === "GET" ? {} : await request.json().catch(() => null);
  if (body === null) return res(errorBody("invalid_json", "Request body must be JSON.", "recoverable"), 400);

  if (!id) {
    if (request.method !== "POST") return res(errorBody("method_not_allowed", "Use POST to create a checkout session.", "recoverable"), 405);
    const pr = await priceLines(env, body.line_items);
    if (pr.error) return res(pr.error, 400);
    const now = Date.now();
    const s = { id: newId(), item: pr.item, currency: pr.currency, status: "requires_escalation", created_at: now, expires_at: new Date(now + SESSION_TTL * 1000).toISOString() };
    if (body.buyer && typeof body.buyer === "object") s.buyer = pickBuyer(body.buyer);
    await save(env, s);
    return res(view(s, origin), 201);
  }

  const s = await load(env, id);
  if (!s) return res(errorBody("not_found", "No checkout session " + id + " (sessions expire after six hours).", "unrecoverable"), 404);

  if (!action && request.method === "GET") return res(view(s, origin));
  if (s.status === "completed" || s.status === "canceled") {
    if (action === "complete" && s.status === "completed") return res(view(s, origin));
    return res({ ...view(s, origin), messages: [{ type: "error", code: "invalid_state", content: "Session is " + s.status + ".", severity: "unrecoverable" }] }, 409);
  }
  if (!action && request.method === "PUT") {
    if (s.order_pending) return res({ ...view(s, origin), messages: [{ type: "error", code: "invalid_state", content: "Payment has started on the handoff page; the session can no longer change.", severity: "unrecoverable" }] }, 409);
    const pr = await priceLines(env, body.line_items);
    if (pr.error) return res(pr.error, 400);
    s.item = pr.item;
    if (body.buyer && typeof body.buyer === "object") s.buyer = pickBuyer(body.buyer);
    await save(env, s);
    return res(view(s, origin));
  }
  if (action === "cancel" && request.method === "POST") {
    s.status = "canceled";
    await save(env, s);
    return res(view(s, origin));
  }
  if (action === "complete" && request.method === "POST") {
    // Nothing an agent can send settles a PayPal payment. Say so plainly.
    return res(view(s, origin));
  }
  return res(errorBody("method_not_allowed", "Method not allowed here.", "recoverable"), 405);
}

function pickBuyer(b) {
  const out = {};
  for (const k of ["first_name", "last_name", "email"]) if (typeof b[k] === "string" && b[k].length < 200) out[k] = b[k];
  return out;
}

// ------------------------------------------------- buyer handoff (browser) --

export async function handleHandoff(request, env, url) {
  if (!env.COMMERCE) return new Response("Checkout is not configured.", { status: 503 });
  const m = url.pathname.replace(/\/+$/, "").match(/^\/checkout\/ucp\/(cs_[A-Za-z0-9_-]{24})(?:\/(order|capture))?$/);
  if (!m) return new Response("Not found", { status: 404 });
  const [, id, step] = m;
  const s = await load(env, id);

  if (!step) {
    if (request.method !== "GET") return new Response("Method not allowed", { status: 405 });
    return handoffPage(s, id, await packs(env).catch(() => null));
  }
  if (request.method !== "POST") return res({ error: "method_not_allowed" }, 405);
  // Same-origin only: these steps are for the handoff page, not for agents.
  const o = request.headers.get("origin");
  if (o && o !== url.origin) return res({ error: "forbidden_origin" }, 403);
  if (!s) return res({ error: "session_not_found" }, 404);
  if (s.status !== "requires_escalation") return res({ error: "session_" + s.status }, 409);
  const body = await request.json().catch(() => ({}));

  if (step === "order") {
    const payload = { pack: s.item.pack };
    const email = typeof body.email === "string" && body.email ? body.email : s.buyer && s.buyer.email;
    if (email) payload.email = String(email).slice(0, 254);
    if (typeof body.api_key === "string" && body.api_key.startsWith("bk_")) payload.api_key = body.api_key.trim();
    const r = await callApi(env, "/v1/billing/orders", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok || !j.id) return res({ error: j.error || "order_failed" }, r.ok ? 502 : r.status);
    s.order_pending = j.id;
    await save(env, s);
    // The new key (if any) goes to the buyer's browser only. It is not stored here.
    return res({ id: j.id, ...(j.api_key ? { api_key: j.api_key } : {}) });
  }

  // capture
  const orderId = String(body.orderID || "");
  if (!orderId || orderId !== s.order_pending) return res({ error: "order_mismatch" }, 400);
  const r = await callApi(env, "/v1/billing/orders/" + encodeURIComponent(orderId) + "/capture", { method: "POST" });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) return res({ error: j.error || "capture_failed", detail: j.detail }, r.status);
  // Verified by the billing API against PayPal: COMPLETED, amount equals the pack price.
  if (j.status !== "COMPLETED" || j.credited !== s.item.credits) return res({ error: "capture_unverified" }, 502);
  s.status = "completed";
  s.order = { id: orderId, key_prefix: j.key_prefix };
  s.completed_at = Date.now();
  await save(env, s);
  return res({ status: "completed", credits: j.credits, credited: j.credited, key_prefix: j.key_prefix });
}

const esc = (v) => String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function handoffPage(s, id, cat) {
  const head = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex"><title>Complete your BlvkWare purchase</title>
<style>
:root{--bg:#0b0b0d;--fg:#ececf0;--mut:#9a9aa6;--card:#15151a;--line:#26262e;--acc:#7cf5c0}
@media(prefers-color-scheme:light){:root{--bg:#fafafa;--fg:#111;--mut:#5c5c66;--card:#fff;--line:#ddd;--acc:#0a7d54}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:560px;margin:0 auto;padding:40px 18px}h1{font-size:1.5rem;margin:0 0 6px}p{color:var(--mut);margin:.4em 0}
.card{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:18px;margin:18px 0}
.row{display:flex;justify-content:space-between;gap:12px;align-items:baseline}.row strong{font-size:1.25rem}
label{display:block;font-size:.9rem;color:var(--mut);margin-top:12px}input{width:100%;padding:10px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);margin-top:4px;font:inherit}
#err{color:#ff6b6b;min-height:1.4em}#done{display:none;border-color:var(--acc)}code{display:block;word-break:break-all;padding:10px;border-radius:6px;background:var(--bg);margin:8px 0;user-select:all}
a{color:var(--acc)}small{color:var(--mut)}
</style></head><body><main>`;
  const foot = `</main></body></html>`;
  const page = (inner, status = 200) => new Response(head + inner + foot, { status, headers: {
    "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "referrer-policy": "no-referrer", "x-content-type-options": "nosniff",
    "content-security-policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://www.paypal.com https://*.paypal.com https://*.paypalobjects.com; frame-src https://*.paypal.com; img-src 'self' data: https://*.paypal.com https://*.paypalobjects.com; connect-src 'self' https://*.paypal.com; style-src 'self' 'unsafe-inline'",
  } });
  if (!s) return page(`<h1>Checkout expired</h1><p>This checkout session no longer exists. Sessions last six hours. Ask your agent to start a new one, or buy directly at <a href="https://api.blvkware.dev/hallux/buy">the HALLUX store</a>.</p>`, 404);
  const price = (s.item.price / 100).toFixed(2);
  const summary = `<div class="card"><div class="row"><span>${esc(s.item.title)}</span><strong>$${esc(price)}</strong></div><small>${esc(s.item.credits.toLocaleString("en-US"))} identifier checks · one-time · ${esc(s.currency)}</small></div>`;
  if (s.status === "completed") return page(`<h1>Purchase complete</h1>${summary}<div class="card" style="border-color:var(--acc)"><p>Credits were added to key <strong>${esc(s.order.key_prefix)}…</strong>. Your agent's checkout now reads <em>completed</em>.</p></div>`);
  if (s.status === "canceled") return page(`<h1>Checkout canceled</h1>${summary}<p>Nothing was charged.</p>`);
  if (!cat || !cat.clientId) return page(`<h1>Payment unavailable</h1><p>PayPal could not be loaded right now. Nothing was charged. Try again shortly.</p>`, 503);
  const email = s.buyer && s.buyer.email ? esc(s.buyer.email) : "";
  return page(`<h1>Complete your purchase</h1><p>An agent started this checkout for you. Review it and pay with PayPal. You can close this page to decline.</p>
${summary}
<label>Email for the receipt (optional)<input type="email" id="email" autocomplete="email" value="${email}"></label>
<label>Top up an existing key instead of getting a new one (optional)<input type="text" id="apikey" placeholder="bk_live_…" autocomplete="off" spellcheck="false"></label>
<div class="card"><div id="paypal-buttons"></div><p id="err" role="alert"></p></div>
<div class="card" id="done" aria-live="polite"><strong>Payment complete.</strong><div id="out"></div></div>
<p><small>Payments are processed by PayPal. BlvkWare never sees card details. <a href="/terms/">Terms</a> · <a href="/privacy/">Privacy</a></small></p>
<script src="https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(cat.clientId)}&currency=${encodeURIComponent(s.currency)}&intent=capture&components=buttons"></script>
<script>
(function(){
var base = "/checkout/ucp/${esc(id)}", newKey = null, $ = function(i){return document.getElementById(i)};
function fail(m){ $("err").textContent = m || ""; }
function post(p, b){ return fetch(base + p, { method:"POST", headers:{"content-type":"application/json"}, body: JSON.stringify(b||{}) }).then(function(r){ return r.json().then(function(j){ return { ok:r.ok, j:j }; }); }); }
paypal.Buttons({
  style:{ layout:"vertical", color:"gold", label:"pay" },
  createOrder: function(){ fail(""); return post("/order", { email: $("email").value || undefined, api_key: $("apikey").value.trim() || undefined }).then(function(x){ if(!x.ok){ fail(x.j.error === "unknown_api_key" ? "That key was not recognised." : "Could not start checkout ("+(x.j.error||"error")+")."); throw new Error(x.j.error); } newKey = x.j.api_key || null; return x.j.id; }); },
  onApprove: function(d){ return post("/capture", { orderID: d.orderID }).then(function(x){
    if(!x.ok){ return fail("Capture could not be confirmed (" + (x.j.error||"error") + "). If PayPal charged you, contact support with order " + d.orderID + "."); }
    $("paypal-buttons").style.display = "none"; $("done").style.display = "block";
    var o = $("out"); o.textContent = "";
    var p = document.createElement("p"); p.textContent = x.j.credits.toLocaleString() + " credits are on key " + x.j.key_prefix + "…. Your agent's checkout now reads completed."; o.appendChild(p);
    if (newKey) { var w = document.createElement("p"); w.textContent = "Your new API key. It is shown once, so save it now:"; o.appendChild(w); var c = document.createElement("code"); c.textContent = newKey; o.appendChild(c); }
  }); },
  onCancel: function(){ fail("Payment canceled. Nothing was charged."); },
  onError: function(){ fail("PayPal reported an error. Nothing was charged unless PayPal confirmed it."); }
}).render("#paypal-buttons");
})();
</script>`);
}
