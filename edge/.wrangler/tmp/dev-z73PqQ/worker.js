var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// worker.js
var ISSUER = "https://blvkware.dev";
var API_ACCOUNT = "https://api.blvkware.dev/hallux/v1/account";
var SCOPES = ["hallux", "cordon"];
var CODE_TTL = 300;
var LINKS = [
  '</.well-known/api-catalog>; rel="api-catalog"; type="application/linkset+json"',
  '<https://api.blvkware.dev/hallux/openapi.json>; rel="service-desc"; type="application/openapi+json"',
  '<https://cordon.blvkware.dev/openapi.json>; rel="service-desc"; type="application/openapi+json"',
  '</docs/hallux-spec/>; rel="service-doc"; type="text/html"',
  '</llms.txt>; rel="describedby"; type="text/plain"',
  '</.well-known/ai-catalog.json>; rel="describedby"; type="application/json"',
  '</auth.md>; rel="describedby"; type="text/markdown"',
  '</.well-known/mcp/server-card.json>; rel="describedby"; type="application/json"'
].join(", ");
var MEDIA_TYPES = {
  "/.well-known/api-catalog": 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"',
  "/auth.md": "text/markdown; charset=utf-8",
  "/llms.txt": "text/plain; charset=utf-8"
};
var worker_default = {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const p = url.pathname;
    try {
      if (p === "/.well-known/oauth-authorization-server" || p === "/.well-known/oauth-authorization-server/oauth") return json(asMetadata(), 200, cacheable());
      if (p === "/.well-known/oauth-protected-resource" || p.startsWith("/.well-known/oauth-protected-resource/")) return json(prMetadata(), 200, cacheable());
      if (p === "/oauth/jwks.json") return json({ keys: [] }, 200, cacheable());
      if (p.startsWith("/oauth/")) {
        if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors() });
        if (p === "/oauth/register") return register(request, env);
        if (p === "/oauth/authorize") return authorize(request, env, url);
        if (p === "/oauth/token") return token(request, env);
        return json({ error: "not_found" }, 404);
      }
    } catch (e) {
      return json({ error: "server_error", error_description: "Unexpected error." }, 500);
    }
    return passthrough(request, url);
  }
};
async function passthrough(request, url) {
  const wantsMd = request.method === "GET" && prefersMarkdown(request.headers.get("accept") || "");
  const res = await fetch(request);
  const type = res.headers.get("content-type") || "";
  const forced = MEDIA_TYPES[url.pathname] || (url.pathname.startsWith("/.well-known/agent-skills/") && url.pathname.endsWith(".md") ? "text/markdown; charset=utf-8" : null);
  if (forced && res.ok) {
    const h2 = new Headers(res.headers);
    h2.set("content-type", forced);
    h2.set("access-control-allow-origin", "*");
    return new Response(res.body, { status: res.status, headers: h2 });
  }
  if (!type.includes("text/html")) return res;
  if (wantsMd && res.ok) {
    const html = await res.text();
    const md = htmlToMarkdown(html, url);
    const h2 = new Headers();
    h2.set("content-type", "text/markdown; charset=utf-8");
    h2.set("x-markdown-tokens", String(Math.ceil(md.length / 4)));
    h2.set("vary", "Accept");
    h2.set("cache-control", res.headers.get("cache-control") || "public, max-age=600");
    h2.set("link", LINKS);
    h2.set("content-location", url.pathname);
    h2.set("access-control-allow-origin", "*");
    return new Response(md, { status: 200, headers: h2 });
  }
  const h = new Headers(res.headers);
  h.append("link", LINKS);
  h.append("link", "<" + url.pathname + '>; rel="alternate"; type="text/markdown"');
  h.set("vary", appendVary(h.get("vary"), "Accept"));
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}
__name(passthrough, "passthrough");
function prefersMarkdown(accept) {
  let md = -1, html = -1;
  for (const part of accept.toLowerCase().split(",")) {
    const [type, ...params] = part.trim().split(";");
    const q = params.map((s) => s.trim()).find((s) => s.startsWith("q="));
    const weight = q ? parseFloat(q.slice(2)) || 0 : 1;
    if (type === "text/markdown" || type === "text/x-markdown") md = Math.max(md, weight);
    if (type === "text/html") html = Math.max(html, weight);
  }
  return md > 0 && md >= html;
}
__name(prefersMarkdown, "prefersMarkdown");
function appendVary(v, k) {
  if (!v) return k;
  return v.split(",").map((s) => s.trim().toLowerCase()).includes(k.toLowerCase()) ? v : v + ", " + k;
}
__name(appendVary, "appendVary");
var ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", mdash: "\u2014", ndash: "\u2013", hellip: "\u2026", rsquo: "\u2019", lsquo: "\u2018", rdquo: "\u201D", ldquo: "\u201C", middot: "\xB7", times: "\xD7", rarr: "\u2192", larr: "\u2190", copy: "\xA9", trade: "\u2122", bull: "\u2022" };
function decode(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === "#") {
      const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}
__name(decode, "decode");
function attr(tag, name) {
  const m = tag.match(new RegExp("\\s" + name + `\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s>]+))`, "i"));
  return m ? decode(m[2] ?? m[3] ?? m[4] ?? "") : "";
}
__name(attr, "attr");
function htmlToMarkdown(html, url) {
  const title = decode((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [, ""])[1]).trim();
  const desc = attr((html.match(/<meta[^>]+name=["']description["'][^>]*>/i) || [""])[0], "content");
  let body = (html.match(/<main[\s\S]*?<\/main>/i) || html.match(/<body[\s\S]*?<\/body>/i) || [html])[0];
  body = body.replace(/<!--[\s\S]*?-->/g, "").replace(/<(script|style|svg|noscript|template|iframe|form|button|select|nav|footer)\b[\s\S]*?<\/\1>/gi, "").replace(/<(header)\b[^>]*class=["'][^"']*(site|top|nav)[^"']*["'][\s\S]*?<\/header>/gi, "").replace(/<(a|span|p|small)\b[^>]*\shidden(?=[\s>=])[^>]*>[\s\S]*?<\/\1>/gi, "");
  const pres = [];
  body = body.replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, (_, inner) => {
    const lang = (inner.match(/class=["'][^"']*language-([\w-]+)/i) || [, ""])[1];
    const code = decode(inner.replace(/<[^>]+>/g, "")).replace(/\n+$/, "");
    pres.push("\n\n```" + lang + "\n" + code + "\n```\n\n");
    return "\0PRE" + (pres.length - 1) + "\0";
  });
  body = body.replace(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi, (_, n, t) => "\n\n" + "#".repeat(+n) + " " + inline(t.replace(/<br\s*\/?>/gi, " ")).replace(/\s+/g, " ").trim() + "\n\n").replace(/<(p|section|article|div|header|aside|figure|figcaption|dl|table|tr)\b[^>]*>/gi, "\n\n").replace(/<\/(p|section|article|div|header|aside|figure|figcaption|dl|table|tr)>/gi, "\n\n").replace(/<blockquote\b[^>]*>([\s\S]*?)<\/blockquote>/gi, (_, t) => "\n\n" + inline(t).trim().split("\n").map((l) => "> " + l).join("\n") + "\n\n").replace(/<li\b[^>]*>/gi, "\n- ").replace(/<\/li>/gi, "").replace(/<\/?(ul|ol)\b[^>]*>/gi, "\n").replace(/<dt\b[^>]*>([\s\S]*?)<\/dt>/gi, (_, t) => "\n**" + inline(t).trim() + "**\n").replace(/<dd\b[^>]*>/gi, ": ").replace(/<t[hd]\b[^>]*>([\s\S]*?)<\/t[hd]>/gi, (_, t) => " | " + inline(t).trim()).replace(/<br\s*\/?>/gi, "\n").replace(/<hr\s*\/?>/gi, "\n\n---\n\n");
  let md = inline(body).replace(/[ \t]+\n/g, "\n").replace(/\n[ \t]+(?=\S)/g, (m) => m.includes("- ") ? m : "\n").replace(/\n{3,}/g, "\n\n").trim();
  md = md.replace(/\u0000PRE(\d+)\u0000/g, (_, i) => pres[+i]).replace(/\n{3,}/g, "\n\n");
  let head = "";
  if (!/^#\s/m.test(md) && title) head += "# " + title + "\n\n";
  if (desc) head += "> " + desc + "\n\n";
  return head + md + "\n\n---\nSource: " + url.origin + url.pathname + "\n";
}
__name(htmlToMarkdown, "htmlToMarkdown");
function inline(s) {
  return decode(
    s.replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi, (_, a, t) => {
      const href = attr(" " + a, "href");
      const text = t.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
      if (!text) return "";
      if (!href || href.startsWith("#") || href.startsWith("javascript:")) return text;
      return "[" + text + "](" + href + ")";
    }).replace(/<img\b([^>]*)>/gi, (_, a) => {
      const alt = attr(" " + a, "alt");
      return alt ? "![" + alt + "](" + attr(" " + a, "src") + ")" : "";
    }).replace(/<(strong|b)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_, __, t) => t.trim() ? "**" + t.trim() + "**" : "").replace(/<(em|i)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_, __, t) => t.trim() ? "*" + t.trim() + "*" : "").replace(/<code\b[^>]*>([\s\S]*?)<\/code>/gi, (_, t) => "`" + t.replace(/<[^>]+>/g, "") + "`").replace(/<[^>]+>/g, "")
  ).replace(/[ \t\u00a0]{2,}/g, " ");
}
__name(inline, "inline");
function asMetadata() {
  return {
    issuer: ISSUER,
    authorization_endpoint: ISSUER + "/oauth/authorize",
    token_endpoint: ISSUER + "/oauth/token",
    registration_endpoint: ISSUER + "/oauth/register",
    jwks_uri: ISSUER + "/oauth/jwks.json",
    scopes_supported: SCOPES,
    response_types_supported: ["code"],
    response_modes_supported: ["query"],
    grant_types_supported: ["authorization_code"],
    code_challenge_methods_supported: ["S256"],
    token_endpoint_auth_methods_supported: ["none"],
    authorization_response_iss_parameter_supported: true,
    service_documentation: ISSUER + "/auth.md",
    op_policy_uri: ISSUER + "/privacy/",
    op_tos_uri: ISSUER + "/terms/",
    agent_auth: {
      skill: ISSUER + "/auth.md",
      register_uri: ISSUER + "/oauth/register",
      identity_types_supported: ["anonymous"],
      anonymous: {
        credential_types_supported: ["oauth_client_id"],
        claim_uri: ISSUER + "/oauth/authorize"
      },
      credential_use: "Authorization: Bearer <access_token> on https://api.blvkware.dev/hallux and https://cordon.blvkware.dev"
    }
  };
}
__name(asMetadata, "asMetadata");
function prMetadata() {
  return {
    resource: ISSUER,
    resource_name: "BlvkWare APIs (HALLUX and CORDON)",
    authorization_servers: [ISSUER],
    scopes_supported: SCOPES,
    bearer_methods_supported: ["header"],
    resource_documentation: ISSUER + "/auth.md",
    resource_policy_uri: ISSUER + "/privacy/",
    resource_tos_uri: ISSUER + "/terms/",
    protected_endpoints: [
      "https://api.blvkware.dev/hallux/v1",
      "https://api.blvkware.dev/hallux/mcp",
      "https://cordon.blvkware.dev/v1",
      "https://cordon.blvkware.dev/mcp"
    ]
  };
}
__name(prMetadata, "prMetadata");
async function sealKey(env) {
  if (!env.OAUTH_SECRET || env.OAUTH_SECRET.length < 32) throw new Error("OAUTH_SECRET missing");
  const raw = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("blvkware-oauth-v1:" + env.OAUTH_SECRET));
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}
__name(sealKey, "sealKey");
async function seal(env, purpose, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: new TextEncoder().encode(purpose) }, await sealKey(env), new TextEncoder().encode(JSON.stringify(obj)));
  return b64u(iv) + "." + b64u(new Uint8Array(ct));
}
__name(seal, "seal");
async function open(env, purpose, s) {
  try {
    const [a, b] = String(s || "").split(".");
    if (!a || !b) return null;
    const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: unb64u(a), additionalData: new TextEncoder().encode(purpose) }, await sealKey(env), unb64u(b));
    return JSON.parse(new TextDecoder().decode(pt));
  } catch {
    return null;
  }
}
__name(open, "open");
function b64u(bytes) {
  let s = "";
  for (const x of bytes) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
__name(b64u, "b64u");
function unb64u(s) {
  const t = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(t, (c) => c.charCodeAt(0));
}
__name(unb64u, "unb64u");
function validRedirect(u) {
  try {
    const x = new URL(u);
    if (x.hash) return false;
    if (x.protocol === "https:") return true;
    if (x.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(x.hostname)) return true;
    return /^[a-z][a-z0-9+.-]*\.[a-z0-9+.-]+:$/i.test(x.protocol);
  } catch {
    return false;
  }
}
__name(validRedirect, "validRedirect");
function redirectMatches(registered, given) {
  if (registered.includes(given)) return true;
  try {
    const g = new URL(given);
    if (g.protocol !== "http:" || !["localhost", "127.0.0.1", "[::1]"].includes(g.hostname)) return false;
    return registered.some((r) => {
      const x = new URL(r);
      return x.protocol === g.protocol && x.hostname === g.hostname && x.pathname === g.pathname && x.search === g.search;
    });
  } catch {
    return false;
  }
}
__name(redirectMatches, "redirectMatches");
async function register(request, env) {
  if (request.method !== "POST") return json({ error: "invalid_request", error_description: "POST a client metadata document." }, 405);
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "invalid_client_metadata", error_description: "Body must be JSON." }, 400);
  }
  const uris = Array.isArray(body.redirect_uris) ? body.redirect_uris.map(String) : [];
  if (!uris.length || uris.length > 10 || !uris.every(validRedirect)) {
    return json({ error: "invalid_redirect_uri", error_description: "Provide 1-10 redirect_uris: https, loopback http, or a private-use app scheme." }, 400);
  }
  const method = body.token_endpoint_auth_method || "none";
  if (method !== "none") return json({ error: "invalid_client_metadata", error_description: "Only public clients (token_endpoint_auth_method: none) are supported; PKCE is required." }, 400);
  const name = String(body.client_name || "").slice(0, 80);
  const now = Math.floor(Date.now() / 1e3);
  const client_id = "bwc_" + await seal(env, "client", { r: uris, n: name, t: now });
  return json({
    client_id,
    client_id_issued_at: now,
    client_name: name || void 0,
    redirect_uris: uris,
    token_endpoint_auth_method: "none",
    grant_types: ["authorization_code"],
    response_types: ["code"],
    scope: SCOPES.join(" ")
  }, 201, cors());
}
__name(register, "register");
async function client(env, id) {
  if (!String(id || "").startsWith("bwc_")) return null;
  return open(env, "client", String(id).slice(4));
}
__name(client, "client");
async function authorize(request, env, url) {
  const src = request.method === "POST" ? Object.fromEntries((await request.formData()).entries()) : Object.fromEntries(url.searchParams.entries());
  const q = {
    response_type: src.response_type,
    client_id: src.client_id,
    redirect_uri: src.redirect_uri,
    state: src.state || "",
    scope: src.scope || SCOPES.join(" "),
    code_challenge: src.code_challenge,
    code_challenge_method: src.code_challenge_method || ""
  };
  const c = await client(env, q.client_id);
  if (!c) return page(400, "Unknown client", "<p>This sign-in link names a client that was not registered with BlvkWare. Return to the app and try connecting again.</p>");
  if (!q.redirect_uri && c.r.length === 1) q.redirect_uri = c.r[0];
  if (!redirectMatches(c.r, q.redirect_uri)) return page(400, "Redirect not allowed", "<p>This app asked to return to an address it did not register. Nothing was shared.</p>");
  const fail = /* @__PURE__ */ __name((error, description) => redirectTo(q.redirect_uri, { error, error_description: description, state: q.state, iss: ISSUER }), "fail");
  if (q.response_type !== "code") return fail("unsupported_response_type", "Only response_type=code is supported.");
  if (q.code_challenge_method !== "S256" || !/^[A-Za-z0-9_-]{43,128}$/.test(q.code_challenge || "")) return fail("invalid_request", "PKCE with code_challenge_method=S256 is required.");
  const appName = c.n || new URL(q.redirect_uri).host || "This app";
  const returnHost = (() => {
    try {
      const u = new URL(q.redirect_uri);
      return u.protocol === "https:" || u.protocol === "http:" ? u.host : u.protocol.replace(":", "");
    } catch {
      return "the app";
    }
  })();
  if (request.method === "POST") {
    if (src.decision === "deny") return fail("access_denied", "The user declined.");
    const bound = await open(env, "form", src.form);
    if (!bound || bound.c !== q.client_id || bound.r !== q.redirect_uri || bound.p !== q.code_challenge || bound.e < Date.now() / 1e3) {
      return page(400, "This sign-in expired", "<p>Return to the app and start the connection again.</p>");
    }
    const key = String(src.api_key || "").trim();
    let ok = false;
    if (/^bk_[A-Za-z0-9_-]{16,128}$/.test(key)) {
      const r = await fetch(env.API_ACCOUNT_URL || API_ACCOUNT, { headers: { authorization: "Bearer " + key, accept: "application/json" } });
      ok = r.status === 200;
    }
    if (!ok) return consent(q, appName, returnHost, src.form, "That key was not accepted. Check it and try again, or buy one below.");
    const code = await seal(env, "code", { k: key, c: q.client_id, r: q.redirect_uri, p: q.code_challenge, s: q.scope, e: Math.floor(Date.now() / 1e3) + CODE_TTL });
    return redirectTo(q.redirect_uri, { code, state: q.state, iss: ISSUER });
  }
  const form = await seal(env, "form", { c: q.client_id, r: q.redirect_uri, p: q.code_challenge, e: Math.floor(Date.now() / 1e3) + 1800 });
  return consent(q, appName, returnHost, form, "");
}
__name(authorize, "authorize");
async function token(request, env) {
  if (request.method !== "POST") return json({ error: "invalid_request" }, 405, cors());
  const ct = request.headers.get("content-type") || "";
  const f = ct.includes("application/json") ? await request.json().catch(() => ({})) : Object.fromEntries((await request.formData().catch(() => new FormData())).entries());
  if (f.grant_type !== "authorization_code") return json({ error: "unsupported_grant_type" }, 400, cors());
  const code = await open(env, "code", f.code);
  if (!code || code.e < Date.now() / 1e3) return json({ error: "invalid_grant", error_description: "Code is invalid or expired." }, 400, cors());
  if (f.client_id && f.client_id !== code.c) return json({ error: "invalid_grant", error_description: "Code was issued to another client." }, 400, cors());
  if (f.redirect_uri && f.redirect_uri !== code.r) return json({ error: "invalid_grant", error_description: "redirect_uri does not match." }, 400, cors());
  const verifier = String(f.code_verifier || "");
  if (!/^[A-Za-z0-9._~-]{43,128}$/.test(verifier)) return json({ error: "invalid_grant", error_description: "code_verifier is required." }, 400, cors());
  const challenge = b64u(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  if (challenge !== code.p) return json({ error: "invalid_grant", error_description: "PKCE verification failed." }, 400, cors());
  return json({ access_token: code.k, token_type: "Bearer", scope: code.s }, 200, { ...cors(), "cache-control": "no-store", pragma: "no-cache" });
}
__name(token, "token");
function redirectTo(base, params) {
  const u = new URL(base);
  for (const [k, v] of Object.entries(params)) if (v !== void 0 && v !== "") u.searchParams.set(k, v);
  return new Response(null, { status: 302, headers: { location: u.toString(), "cache-control": "no-store", "referrer-policy": "no-referrer" } });
}
__name(redirectTo, "redirectTo");
function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}
__name(esc, "esc");
function consent(q, appName, returnHost, form, error) {
  const hidden = ["response_type", "client_id", "redirect_uri", "state", "scope", "code_challenge", "code_challenge_method"].map((k) => '<input type="hidden" name="' + k + '" value="' + esc(q[k] || "") + '">').join("");
  const body = '<p class="lede"><strong>' + esc(appName) + "</strong> wants to use HALLUX and CORDON on your behalf, with your BlvkWare API key.</p>" + (error ? '<p class="err" role="alert">' + esc(error) + "</p>" : "") + '<form method="post" action="/oauth/authorize">' + hidden + '<input type="hidden" name="form" value="' + esc(form) + `"><label for="k">Your API key</label><input id="k" name="api_key" type="password" autocomplete="off" spellcheck="false" placeholder="bk_live_..." required><p class="fine">We check the key with the API and hand it to the app; BlvkWare stores nothing here. The app will be able to spend this key's credit. After this you return to <strong>` + esc(returnHost) + '</strong>.</p><div class="row"><button class="btn" name="decision" value="allow">Connect</button><button class="btn ghost" name="decision" value="deny" formnovalidate>Cancel</button></div></form><p class="fine">No key? HALLUX and CORDON work without one on the free tier, so you can cancel. To buy credit: <a href="https://api.blvkware.dev/buy" target="_blank" rel="noopener">api.blvkware.dev/buy</a>. How this works: <a href="/auth.md" target="_blank" rel="noopener">auth.md</a>.</p>';
  return page(200, "Connect to BlvkWare", body);
}
__name(consent, "consent");
function page(status, title, inner) {
  const html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>' + esc(title) + ' | BlvkWare</title><link rel="icon" href="/assets/favicon-48.png"><style>:root{--bg:#0A0908;--s:#17140F;--a:#D4F24A;--b:#D9B65C;--i:#F5F0E6;--i2:#A89D8B;--l:rgba(245,240,230,.1)}*{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg);color:var(--i);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}.w{max-width:480px;margin:0 auto;padding:3rem 1.5rem}.top{display:flex;align-items:center;gap:.7rem;margin-bottom:2.2rem;color:inherit;text-decoration:none;font-weight:800;font-size:1.2rem}.top img{width:44px;height:44px;border-radius:12px}.top span{color:var(--a)}h1{font-size:1.7rem;letter-spacing:-.02em;margin-bottom:.8rem}p{color:var(--i2);margin-bottom:1rem}.lede{color:var(--i)}strong{color:var(--i)}a{color:var(--a)}label{display:block;font-weight:600;margin:.4rem 0}input[type=password]{width:100%;font:500 1rem ui-monospace,monospace;color:var(--i);background:var(--s);border:1px solid var(--l);border-radius:10px;padding:.75rem .9rem;margin-bottom:.8rem}input:focus{outline:2px solid var(--a);border-color:transparent}.row{display:flex;gap:.6rem;margin:1rem 0 1.4rem}.btn{font:700 .95rem system-ui,sans-serif;color:var(--bg);background:var(--a);border:0;border-radius:10px;padding:.75rem 1.2rem;cursor:pointer}.btn.ghost{background:none;color:var(--i);box-shadow:inset 0 0 0 1px var(--l)}.btn:focus-visible{outline:2px solid var(--i);outline-offset:2px}.fine{font-size:.85rem}.err{color:var(--i);background:rgba(232,101,79,.1);border:1px solid rgba(232,101,79,.4);border-radius:10px;padding:.7rem .9rem}</style></head><body><div class="w"><a class="top" href="/"><img src="/assets/logo-192.png" alt="">BlvkWare<span>.</span></a><h1>' + esc(title) + "</h1>" + inner + "</div></body></html>";
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-frame-options": "DENY",
      "content-security-policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
      "referrer-policy": "no-referrer"
    }
  });
}
__name(page, "page");
function cors() {
  return { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, POST, OPTIONS", "access-control-allow-headers": "content-type, authorization", "access-control-max-age": "86400" };
}
__name(cors, "cors");
function cacheable() {
  return { ...cors(), "cache-control": "public, max-age=3600" };
}
__name(cacheable, "cacheable");
function json(obj, status = 200, headers = {}) {
  return new Response(JSON.stringify(obj, null, 2) + "\n", { status, headers: { "content-type": "application/json; charset=utf-8", ...headers } });
}
__name(json, "json");

// ../../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/middleware-ensure-req-body-drained.ts
var drainBody = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } finally {
    try {
      if (request.body !== null && !request.bodyUsed) {
        const reader = request.body.getReader();
        while (!(await reader.read()).done) {
        }
      }
    } catch (e) {
      console.error("Failed to drain the unused request body.", e);
    }
  }
}, "drainBody");
var middleware_ensure_req_body_drained_default = drainBody;

// ../../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/middleware-miniflare3-json-error.ts
function reduceError(e) {
  return {
    name: e?.name,
    message: e?.message ?? String(e),
    stack: e?.stack,
    cause: e?.cause === void 0 ? void 0 : reduceError(e.cause)
  };
}
__name(reduceError, "reduceError");
var jsonError = /* @__PURE__ */ __name(async (request, env, _ctx, middlewareCtx) => {
  try {
    return await middlewareCtx.next(request, env);
  } catch (e) {
    const error = reduceError(e);
    const body = JSON.stringify(error);
    const headers = {
      "Content-Type": "application/json",
      "MF-Experimental-Error-Stack": "true"
    };
    const encoded = encodeURIComponent(body);
    if (encoded.length <= 8192) {
      headers["MF-Experimental-Error-Stack-Payload"] = encoded;
    }
    return new Response(body, { status: 500, headers });
  }
}, "jsonError");
var middleware_miniflare3_json_error_default = jsonError;

// .wrangler/tmp/bundle-WIoT81/middleware-insertion-facade.js
var __INTERNAL_WRANGLER_MIDDLEWARE__ = [
  middleware_ensure_req_body_drained_default,
  middleware_miniflare3_json_error_default
];
var middleware_insertion_facade_default = worker_default;

// ../../.npm/_npx/32026684e21afda6/node_modules/wrangler/templates/middleware/common.ts
var __facade_middleware__ = [];
function __facade_register__(...args) {
  __facade_middleware__.push(...args.flat());
}
__name(__facade_register__, "__facade_register__");
function __facade_invokeChain__(request, env, ctx, dispatch, middlewareChain) {
  const [head, ...tail] = middlewareChain;
  const middlewareCtx = {
    dispatch,
    next(newRequest, newEnv) {
      return __facade_invokeChain__(newRequest, newEnv, ctx, dispatch, tail);
    }
  };
  return head(request, env, ctx, middlewareCtx);
}
__name(__facade_invokeChain__, "__facade_invokeChain__");
function __facade_invoke__(request, env, ctx, dispatch, finalMiddleware) {
  return __facade_invokeChain__(request, env, ctx, dispatch, [
    ...__facade_middleware__,
    finalMiddleware
  ]);
}
__name(__facade_invoke__, "__facade_invoke__");

// .wrangler/tmp/bundle-WIoT81/middleware-loader.entry.ts
var __Facade_ScheduledController__ = class ___Facade_ScheduledController__ {
  constructor(scheduledTime, cron, noRetry) {
    this.scheduledTime = scheduledTime;
    this.cron = cron;
    this.#noRetry = noRetry;
  }
  scheduledTime;
  cron;
  static {
    __name(this, "__Facade_ScheduledController__");
  }
  #noRetry;
  noRetry() {
    if (!(this instanceof ___Facade_ScheduledController__)) {
      throw new TypeError("Illegal invocation");
    }
    this.#noRetry();
  }
};
function wrapExportedHandler(worker) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return worker;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  const fetchDispatcher = /* @__PURE__ */ __name(function(request, env, ctx) {
    if (worker.fetch === void 0) {
      throw new Error("Handler does not export a fetch() function.");
    }
    return worker.fetch(request, env, ctx);
  }, "fetchDispatcher");
  return {
    ...worker,
    fetch(request, env, ctx) {
      const dispatcher = /* @__PURE__ */ __name(function(type, init) {
        if (type === "scheduled" && worker.scheduled !== void 0) {
          const controller = new __Facade_ScheduledController__(
            Date.now(),
            init.cron ?? "",
            () => {
            }
          );
          return worker.scheduled(controller, env, ctx);
        }
      }, "dispatcher");
      return __facade_invoke__(request, env, ctx, dispatcher, fetchDispatcher);
    }
  };
}
__name(wrapExportedHandler, "wrapExportedHandler");
function wrapWorkerEntrypoint(klass) {
  if (__INTERNAL_WRANGLER_MIDDLEWARE__ === void 0 || __INTERNAL_WRANGLER_MIDDLEWARE__.length === 0) {
    return klass;
  }
  for (const middleware of __INTERNAL_WRANGLER_MIDDLEWARE__) {
    __facade_register__(middleware);
  }
  return class extends klass {
    #fetchDispatcher = /* @__PURE__ */ __name((request, env, ctx) => {
      this.env = env;
      this.ctx = ctx;
      if (super.fetch === void 0) {
        throw new Error("Entrypoint class does not define a fetch() function.");
      }
      return super.fetch(request);
    }, "#fetchDispatcher");
    #dispatcher = /* @__PURE__ */ __name((type, init) => {
      if (type === "scheduled" && super.scheduled !== void 0) {
        const controller = new __Facade_ScheduledController__(
          Date.now(),
          init.cron ?? "",
          () => {
          }
        );
        return super.scheduled(controller);
      }
    }, "#dispatcher");
    fetch(request) {
      return __facade_invoke__(
        request,
        this.env,
        this.ctx,
        this.#dispatcher,
        this.#fetchDispatcher
      );
    }
  };
}
__name(wrapWorkerEntrypoint, "wrapWorkerEntrypoint");
var WRAPPED_ENTRY;
if (typeof middleware_insertion_facade_default === "object") {
  WRAPPED_ENTRY = wrapExportedHandler(middleware_insertion_facade_default);
} else if (typeof middleware_insertion_facade_default === "function") {
  WRAPPED_ENTRY = wrapWorkerEntrypoint(middleware_insertion_facade_default);
}
var middleware_loader_entry_default = WRAPPED_ENTRY;
export {
  __INTERNAL_WRANGLER_MIDDLEWARE__,
  middleware_loader_entry_default as default,
  htmlToMarkdown
};
//# sourceMappingURL=worker.js.map
