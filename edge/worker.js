// blvkware-edge: sits in front of GitHub Pages on blvkware.dev/*.
//
// The site stays a static build in docs/. This Worker adds only what a
// static host cannot do:
//   1. Link headers on HTML pages (RFC 8288 / RFC 9727 section 3).
//   2. Markdown for agents: `Accept: text/markdown` gets the page as Markdown.
//   3. Correct media types for extension-less discovery files.
//   4. An OAuth 2.1 authorization server (RFC 8414 metadata, RFC 7591 dynamic
//      registration, authorization code + PKCE) so MCP clients can sign in.
//      The access token it issues is the user's BlvkWare API key, validated
//      against the live API at sign-in. Nothing is stored: client ids and
//      codes are sealed with AES-GCM under OAUTH_SECRET, and codes expire in
//      five minutes. The raw key never touches storage or logs.
//   5. OAuth protected-resource metadata (RFC 9728).
//
// Anything else passes straight through to the origin unchanged.

const ISSUER = "https://blvkware.dev";
const API_ACCOUNT = "https://api.blvkware.dev/hallux/v1/account";
const SCOPES = ["hallux", "cordon"];
const CODE_TTL = 300; // seconds

const LINKS = [
  '</.well-known/api-catalog>; rel="api-catalog"; type="application/linkset+json"',
  '<https://api.blvkware.dev/hallux/openapi.json>; rel="service-desc"; type="application/openapi+json"',
  '<https://cordon.blvkware.dev/openapi.json>; rel="service-desc"; type="application/openapi+json"',
  '</docs/hallux-spec/>; rel="service-doc"; type="text/html"',
  '</llms.txt>; rel="describedby"; type="text/plain"',
  '</.well-known/ai-catalog.json>; rel="describedby"; type="application/json"',
  '</auth.md>; rel="describedby"; type="text/markdown"',
  '</.well-known/mcp/server-card.json>; rel="describedby"; type="application/json"',
].join(", ");

const MEDIA_TYPES = {
  "/.well-known/api-catalog": 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"',
  "/auth.md": "text/markdown; charset=utf-8",
  "/llms.txt": "text/plain; charset=utf-8",
};

export default {
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
  },
};

// ---------------------------------------------------------------- origin ----

async function passthrough(request, url) {
  const wantsMd = request.method === "GET" && prefersMarkdown(request.headers.get("accept") || "");
  const res = await fetch(request);
  const type = res.headers.get("content-type") || "";
  const forced = MEDIA_TYPES[url.pathname] || (url.pathname.startsWith("/.well-known/agent-skills/") && url.pathname.endsWith(".md") ? "text/markdown; charset=utf-8" : null);
  if (forced && res.ok) {
    const h = new Headers(res.headers);
    h.set("content-type", forced);
    h.set("access-control-allow-origin", "*");
    return new Response(res.body, { status: res.status, headers: h });
  }
  if (!type.includes("text/html")) return res;

  if (wantsMd && res.ok) {
    const html = await res.text();
    const md = htmlToMarkdown(html, url);
    const h = new Headers();
    h.set("content-type", "text/markdown; charset=utf-8");
    h.set("x-markdown-tokens", String(Math.ceil(md.length / 4)));
    h.set("vary", "Accept");
    h.set("cache-control", res.headers.get("cache-control") || "public, max-age=600");
    h.set("link", LINKS);
    h.set("content-location", url.pathname);
    h.set("access-control-allow-origin", "*");
    return new Response(md, { status: 200, headers: h });
  }
  const h = new Headers(res.headers);
  h.append("link", LINKS);
  h.append("link", '<' + url.pathname + '>; rel="alternate"; type="text/markdown"');
  h.set("vary", appendVary(h.get("vary"), "Accept"));
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers: h });
}

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

function appendVary(v, k) {
  if (!v) return k;
  return v.split(",").map((s) => s.trim().toLowerCase()).includes(k.toLowerCase()) ? v : v + ", " + k;
}

// ------------------------------------------------------ html -> markdown ----
// The site's pages are generated, well-formed HTML, so a careful
// tag-by-tag conversion is enough; no DOM is needed.

const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", mdash: "\u2014", ndash: "\u2013", hellip: "\u2026", rsquo: "\u2019", lsquo: "\u2018", rdquo: "\u201d", ldquo: "\u201c", middot: "\u00b7", times: "\u00d7", rarr: "\u2192", larr: "\u2190", copy: "\u00a9", trade: "\u2122", bull: "\u2022" };

function decode(s) {
  return s.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) => {
    if (e[0] === "#") {
      const n = e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
      return Number.isFinite(n) ? String.fromCodePoint(n) : m;
    }
    return ENTITIES[e.toLowerCase()] ?? m;
  });
}

function attr(tag, name) {
  const m = tag.match(new RegExp("\\s" + name + "\\s*=\\s*(\"([^\"]*)\"|'([^']*)'|([^\\s>]+))", "i"));
  return m ? decode(m[2] ?? m[3] ?? m[4] ?? "") : "";
}

export function htmlToMarkdown(html, url) {
  const title = decode((html.match(/<title[^>]*>([\s\S]*?)<\/title>/i) || [, ""])[1]).trim();
  const desc = attr((html.match(/<meta[^>]+name=["']description["'][^>]*>/i) || [""])[0], "content");
  let body = (html.match(/<main[\s\S]*?<\/main>/i) || html.match(/<body[\s\S]*?<\/body>/i) || [html])[0];
  body = body
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<(script|style|svg|noscript|template|iframe|form|button|select|nav|footer)\b[\s\S]*?<\/\1>/gi, "")
    .replace(/<(header)\b[^>]*class=["'][^"']*(site|top|nav)[^"']*["'][\s\S]*?<\/header>/gi, "")
    // Elements the page hides (a banner shown only on launch day, say) are not content.
    .replace(/<(a|span|p|small)\b[^>]*\shidden(?=[\s>=])[^>]*>[\s\S]*?<\/\1>/gi, "");

  const pres = [];
  body = body.replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, (_, inner) => {
    const lang = (inner.match(/class=["'][^"']*language-([\w-]+)/i) || [, ""])[1];
    const code = decode(inner.replace(/<[^>]+>/g, "")).replace(/\n+$/, "");
    pres.push("\n\n```" + lang + "\n" + code + "\n```\n\n");
    return "\u0000PRE" + (pres.length - 1) + "\u0000";
  });

  body = body
    .replace(/<h([1-6])\b[^>]*>([\s\S]*?)<\/h\1>/gi, (_, n, t) => "\n\n" + "#".repeat(+n) + " " + inline(t.replace(/<br\s*\/?>/gi, " ")).replace(/\s+/g, " ").trim() + "\n\n")
    .replace(/<(p|section|article|div|header|aside|figure|figcaption|dl|table|tr)\b[^>]*>/gi, "\n\n")
    .replace(/<\/(p|section|article|div|header|aside|figure|figcaption|dl|table|tr)>/gi, "\n\n")
    .replace(/<blockquote\b[^>]*>([\s\S]*?)<\/blockquote>/gi, (_, t) => "\n\n" + inline(t).trim().split("\n").map((l) => "> " + l).join("\n") + "\n\n")
    .replace(/<li\b[^>]*>/gi, "\n- ")
    .replace(/<\/li>/gi, "")
    .replace(/<\/?(ul|ol)\b[^>]*>/gi, "\n")
    .replace(/<dt\b[^>]*>([\s\S]*?)<\/dt>/gi, (_, t) => "\n**" + inline(t).trim() + "**\n")
    .replace(/<dd\b[^>]*>/gi, ": ")
    .replace(/<t[hd]\b[^>]*>([\s\S]*?)<\/t[hd]>/gi, (_, t) => " | " + inline(t).trim())
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<hr\s*\/?>/gi, "\n\n---\n\n");

  let md = inline(body)
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n[ \t]+(?=\S)/g, (m) => (m.includes("- ") ? m : "\n"))
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  md = md.replace(/\u0000PRE(\d+)\u0000/g, (_, i) => pres[+i]).replace(/\n{3,}/g, "\n\n");

  let head = "";
  if (!/^#\s/m.test(md) && title) head += "# " + title + "\n\n";
  if (desc) head += "> " + desc + "\n\n";
  return head + md + "\n\n---\nSource: " + url.origin + url.pathname + "\n";
}

function inline(s) {
  return decode(
    s
      .replace(/<a\b([^>]*)>([\s\S]*?)<\/a>/gi, (_, a, t) => {
        const href = attr(" " + a, "href");
        const text = t.replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
        if (!text) return "";
        if (!href || href.startsWith("#") || href.startsWith("javascript:")) return text;
        return "[" + text + "](" + href + ")";
      })
      .replace(/<img\b([^>]*)>/gi, (_, a) => {
        const alt = attr(" " + a, "alt");
        return alt ? "![" + alt + "](" + attr(" " + a, "src") + ")" : "";
      })
      .replace(/<(strong|b)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_, __, t) => (t.trim() ? "**" + t.trim() + "**" : ""))
      .replace(/<(em|i)\b[^>]*>([\s\S]*?)<\/\1>/gi, (_, __, t) => (t.trim() ? "*" + t.trim() + "*" : ""))
      .replace(/<code\b[^>]*>([\s\S]*?)<\/code>/gi, (_, t) => "`" + t.replace(/<[^>]+>/g, "") + "`")
      .replace(/<[^>]+>/g, "")
  ).replace(/[ \t\u00a0]{2,}/g, " ");
}

// ----------------------------------------------------------------- oauth ----

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
        claim_uri: ISSUER + "/oauth/authorize",
      },
      credential_use: "Authorization: Bearer <access_token> on https://api.blvkware.dev/hallux and https://cordon.blvkware.dev",
    },
  };
}

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
      "https://cordon.blvkware.dev/mcp",
    ],
  };
}

// Sealed blobs: AES-GCM under a key derived from OAUTH_SECRET, with a purpose
// label in the additional data so a client id can never be replayed as a code.
async function sealKey(env) {
  if (!env.OAUTH_SECRET || env.OAUTH_SECRET.length < 32) throw new Error("OAUTH_SECRET missing");
  const raw = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("blvkware-oauth-v1:" + env.OAUTH_SECRET));
  return crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["encrypt", "decrypt"]);
}
async function seal(env, purpose, obj) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: new TextEncoder().encode(purpose) }, await sealKey(env), new TextEncoder().encode(JSON.stringify(obj)));
  return b64u(iv) + "." + b64u(new Uint8Array(ct));
}
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
function b64u(bytes) {
  let s = "";
  for (const x of bytes) s += String.fromCharCode(x);
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function unb64u(s) {
  const t = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(t, (c) => c.charCodeAt(0));
}

function validRedirect(u) {
  try {
    const x = new URL(u);
    if (x.hash) return false;
    if (x.protocol === "https:") return true;
    if (x.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(x.hostname)) return true;
    // Native apps: private-use schemes (RFC 8252 section 7.1), never javascript/data/file.
    return /^[a-z][a-z0-9+.-]*\.[a-z0-9+.-]+:$/i.test(x.protocol);
  } catch {
    return false;
  }
}
// RFC 8252 7.3: loopback redirects may use any port.
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

async function register(request, env) {
  if (request.method !== "POST") return json({ error: "invalid_request", error_description: "POST a client metadata document." }, 405);
  let body;
  try { body = await request.json(); } catch { return json({ error: "invalid_client_metadata", error_description: "Body must be JSON." }, 400); }
  const uris = Array.isArray(body.redirect_uris) ? body.redirect_uris.map(String) : [];
  if (!uris.length || uris.length > 10 || !uris.every(validRedirect)) {
    return json({ error: "invalid_redirect_uri", error_description: "Provide 1-10 redirect_uris: https, loopback http, or a private-use app scheme." }, 400);
  }
  const method = body.token_endpoint_auth_method || "none";
  if (method !== "none") return json({ error: "invalid_client_metadata", error_description: "Only public clients (token_endpoint_auth_method: none) are supported; PKCE is required." }, 400);
  const name = String(body.client_name || "").slice(0, 80);
  const now = Math.floor(Date.now() / 1000);
  const client_id = "bwc_" + (await seal(env, "client", { r: uris, n: name, t: now }));
  return json({
    client_id,
    client_id_issued_at: now,
    client_name: name || undefined,
    redirect_uris: uris,
    token_endpoint_auth_method: "none",
    grant_types: ["authorization_code"],
    response_types: ["code"],
    scope: SCOPES.join(" "),
  }, 201, cors());
}

async function client(env, id) {
  if (!String(id || "").startsWith("bwc_")) return null;
  return open(env, "client", String(id).slice(4));
}

async function authorize(request, env, url) {
  const src = request.method === "POST" ? Object.fromEntries((await request.formData()).entries()) : Object.fromEntries(url.searchParams.entries());
  const q = {
    response_type: src.response_type, client_id: src.client_id, redirect_uri: src.redirect_uri, state: src.state || "",
    scope: src.scope || SCOPES.join(" "), code_challenge: src.code_challenge, code_challenge_method: src.code_challenge_method || "",
  };
  const c = await client(env, q.client_id);
  // Errors about the client or redirect go to the user, never to an unverified redirect (RFC 6749 4.1.2.1).
  if (!c) return page(400, "Unknown client", "<p>This sign-in link names a client that was not registered with BlvkWare. Return to the app and try connecting again.</p>");
  if (!q.redirect_uri && c.r.length === 1) q.redirect_uri = c.r[0];
  if (!redirectMatches(c.r, q.redirect_uri)) return page(400, "Redirect not allowed", "<p>This app asked to return to an address it did not register. Nothing was shared.</p>");
  const fail = (error, description) => redirectTo(q.redirect_uri, { error, error_description: description, state: q.state, iss: ISSUER });
  if (q.response_type !== "code") return fail("unsupported_response_type", "Only response_type=code is supported.");
  if (q.code_challenge_method !== "S256" || !/^[A-Za-z0-9_-]{43,128}$/.test(q.code_challenge || "")) return fail("invalid_request", "PKCE with code_challenge_method=S256 is required.");

  const appName = c.n || new URL(q.redirect_uri).host || "This app";
  const returnHost = (() => { try { const u = new URL(q.redirect_uri); return u.protocol === "https:" || u.protocol === "http:" ? u.host : u.protocol.replace(":", ""); } catch { return "the app"; } })();

  if (request.method === "POST") {
    if (src.decision === "deny") return fail("access_denied", "The user declined.");
    // Bind the form to the request it was shown for, so a forged POST cannot swap the redirect.
    const bound = await open(env, "form", src.form);
    if (!bound || bound.c !== q.client_id || bound.r !== q.redirect_uri || bound.p !== q.code_challenge || bound.e < Date.now() / 1000) {
      return page(400, "This sign-in expired", "<p>Return to the app and start the connection again.</p>");
    }
    const key = String(src.api_key || "").trim();
    let ok = false;
    if (/^bk_[A-Za-z0-9_-]{16,128}$/.test(key)) {
      const r = await fetch(env.API_ACCOUNT_URL || API_ACCOUNT, { headers: { authorization: "Bearer " + key, accept: "application/json" } });
      ok = r.status === 200;
    }
    if (!ok) return consent(q, appName, returnHost, src.form, "That key was not accepted. Check it and try again, or buy one below.");
    const code = await seal(env, "code", { k: key, c: q.client_id, r: q.redirect_uri, p: q.code_challenge, s: q.scope, e: Math.floor(Date.now() / 1000) + CODE_TTL });
    return redirectTo(q.redirect_uri, { code, state: q.state, iss: ISSUER });
  }
  const form = await seal(env, "form", { c: q.client_id, r: q.redirect_uri, p: q.code_challenge, e: Math.floor(Date.now() / 1000) + 1800 });
  return consent(q, appName, returnHost, form, "");
}

async function token(request, env) {
  if (request.method !== "POST") return json({ error: "invalid_request" }, 405, cors());
  const ct = request.headers.get("content-type") || "";
  const f = ct.includes("application/json") ? await request.json().catch(() => ({})) : Object.fromEntries((await request.formData().catch(() => new FormData())).entries());
  if (f.grant_type !== "authorization_code") return json({ error: "unsupported_grant_type" }, 400, cors());
  const code = await open(env, "code", f.code);
  if (!code || code.e < Date.now() / 1000) return json({ error: "invalid_grant", error_description: "Code is invalid or expired." }, 400, cors());
  if (f.client_id && f.client_id !== code.c) return json({ error: "invalid_grant", error_description: "Code was issued to another client." }, 400, cors());
  if (f.redirect_uri && f.redirect_uri !== code.r) return json({ error: "invalid_grant", error_description: "redirect_uri does not match." }, 400, cors());
  const verifier = String(f.code_verifier || "");
  if (!/^[A-Za-z0-9._~-]{43,128}$/.test(verifier)) return json({ error: "invalid_grant", error_description: "code_verifier is required." }, 400, cors());
  const challenge = b64u(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier))));
  if (challenge !== code.p) return json({ error: "invalid_grant", error_description: "PKCE verification failed." }, 400, cors());
  return json({ access_token: code.k, token_type: "Bearer", scope: code.s }, 200, { ...cors(), "cache-control": "no-store", pragma: "no-cache" });
}

function redirectTo(base, params) {
  const u = new URL(base);
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") u.searchParams.set(k, v);
  return new Response(null, { status: 302, headers: { location: u.toString(), "cache-control": "no-store", "referrer-policy": "no-referrer" } });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function consent(q, appName, returnHost, form, error) {
  const hidden = ["response_type", "client_id", "redirect_uri", "state", "scope", "code_challenge", "code_challenge_method"]
    .map((k) => '<input type="hidden" name="' + k + '" value="' + esc(q[k] || "") + '">').join("");
  const body =
    '<p class="lede"><strong>' + esc(appName) + "</strong> wants to use HALLUX and CORDON on your behalf, with your BlvkWare API key.</p>" +
    (error ? '<p class="err" role="alert">' + esc(error) + "</p>" : "") +
    '<form method="post" action="/oauth/authorize">' + hidden + '<input type="hidden" name="form" value="' + esc(form) + '">' +
    '<label for="k">Your API key</label><input id="k" name="api_key" type="password" autocomplete="off" spellcheck="false" placeholder="bk_live_..." required>' +
    '<p class="fine">We check the key with the API and hand it to the app; BlvkWare stores nothing here. The app will be able to spend this key\'s credit. After this you return to <strong>' + esc(returnHost) + "</strong>.</p>" +
    '<div class="row"><button class="btn" name="decision" value="allow">Connect</button><button class="btn ghost" name="decision" value="deny" formnovalidate>Cancel</button></div></form>' +
    '<p class="fine">No key? HALLUX and CORDON work without one on the free tier, so you can cancel. To buy credit: <a href="https://api.blvkware.dev/buy" target="_blank" rel="noopener">api.blvkware.dev/buy</a>. How this works: <a href="/auth.md" target="_blank" rel="noopener">auth.md</a>.</p>';
  return page(200, "Connect to BlvkWare", body);
}

function page(status, title, inner) {
  const html = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>' + esc(title) + ' | BlvkWare</title><link rel="icon" href="/assets/favicon-48.png"><style>' +
    ':root{--bg:#0A0908;--s:#17140F;--a:#D4F24A;--b:#D9B65C;--i:#F5F0E6;--i2:#A89D8B;--l:rgba(245,240,230,.1)}*{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg);color:var(--i);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}' +
    '.w{max-width:480px;margin:0 auto;padding:3rem 1.5rem}.top{display:flex;align-items:center;gap:.7rem;margin-bottom:2.2rem;color:inherit;text-decoration:none;font-weight:800;font-size:1.2rem}.top img{width:44px;height:44px;border-radius:12px}.top span{color:var(--a)}' +
    'h1{font-size:1.7rem;letter-spacing:-.02em;margin-bottom:.8rem}p{color:var(--i2);margin-bottom:1rem}.lede{color:var(--i)}strong{color:var(--i)}a{color:var(--a)}label{display:block;font-weight:600;margin:.4rem 0}' +
    'input[type=password]{width:100%;font:500 1rem ui-monospace,monospace;color:var(--i);background:var(--s);border:1px solid var(--l);border-radius:10px;padding:.75rem .9rem;margin-bottom:.8rem}input:focus{outline:2px solid var(--a);border-color:transparent}' +
    '.row{display:flex;gap:.6rem;margin:1rem 0 1.4rem}.btn{font:700 .95rem system-ui,sans-serif;color:var(--bg);background:var(--a);border:0;border-radius:10px;padding:.75rem 1.2rem;cursor:pointer}.btn.ghost{background:none;color:var(--i);box-shadow:inset 0 0 0 1px var(--l)}.btn:focus-visible{outline:2px solid var(--i);outline-offset:2px}' +
    '.fine{font-size:.85rem}.err{color:var(--i);background:rgba(232,101,79,.1);border:1px solid rgba(232,101,79,.4);border-radius:10px;padding:.7rem .9rem}</style></head><body><div class="w">' +
    '<a class="top" href="/"><img src="/assets/logo-192.png" alt="">BlvkWare<span>.</span></a><h1>' + esc(title) + "</h1>" + inner + "</div></body></html>";
  return new Response(html, {
    status,
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "no-store",
      "x-frame-options": "DENY",
      "content-security-policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
      "referrer-policy": "no-referrer",
    },
  });
}

// ----------------------------------------------------------------- util ----

function cors() {
  return { "access-control-allow-origin": "*", "access-control-allow-methods": "GET, POST, OPTIONS", "access-control-allow-headers": "content-type, authorization", "access-control-max-age": "86400" };
}
function cacheable() {
  return { ...cors(), "cache-control": "public, max-age=3600" };
}
function json(obj, status = 200, headers = {}) {
  return new Response(JSON.stringify(obj, null, 2) + "\n", { status, headers: { "content-type": "application/json; charset=utf-8", ...headers } });
}
