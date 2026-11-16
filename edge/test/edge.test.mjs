// Run: node --test edge/test/edge.test.mjs   (needs wrangler; starts a local dev server)
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { createHash, randomBytes } from "node:crypto";

const PORT = 8812, MOCK = 8813, B = `http://127.0.0.1:${PORT}`;
let dev, mock;
const b64u = (b) => Buffer.from(b).toString("base64url");

before(async () => {
  mock = createServer((req, res) => {
    const ok = req.headers.authorization === "Bearer bk_live_testkeytestkey123456";
    res.writeHead(ok ? 200 : 401, { "content-type": "application/json" }).end(ok ? '{"key_prefix":"bk_live_test"}' : '{"error":"invalid_api_key"}');
  }).listen(MOCK);
  dev = spawn("npx", ["wrangler", "dev", "--port", String(PORT), "--local", "--var", "OAUTH_SECRET:test-secret-test-secret-test-secret-0001", "--var", `API_ACCOUNT_URL:http://127.0.0.1:${MOCK}/account`], { cwd: new URL("..", import.meta.url).pathname, stdio: "ignore" });
  for (let i = 0; i < 60; i++) { try { await fetch(B + "/oauth/jwks.json"); return; } catch { await new Promise((r) => setTimeout(r, 1000)); } }
  throw new Error("wrangler dev did not start");
});
after(() => { dev?.kill(); mock?.close(); });

test("authorization server metadata", async () => {
  const m = await (await fetch(B + "/.well-known/oauth-authorization-server")).json();
  for (const k of ["issuer", "authorization_endpoint", "token_endpoint", "jwks_uri", "grant_types_supported", "response_types_supported"]) assert.ok(m[k], k);
  assert.equal(m.issuer, "https://blvkware.dev");
  const pr = await (await fetch(B + "/.well-known/oauth-protected-resource")).json();
  assert.deepEqual(pr.authorization_servers, [m.issuer]);
  assert.deepEqual(pr.bearer_methods_supported, ["header"]);
});

async function registerClient(redirect = "https://client.example/cb") {
  const r = await fetch(B + "/oauth/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ redirect_uris: [redirect], client_name: "Test" }) });
  assert.equal(r.status, 201);
  return (await r.json()).client_id;
}

test("registration rejects unsafe redirects and confidential clients", async () => {
  for (const u of ["javascript:alert(1)", "http://evil.example/cb", "data:text/html,x", "https://x.example/cb#frag"]) {
    const r = await fetch(B + "/oauth/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ redirect_uris: [u] }) });
    assert.equal(r.status, 400, u);
  }
  const r = await fetch(B + "/oauth/register", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ redirect_uris: ["https://a.example/cb"], token_endpoint_auth_method: "client_secret_basic" }) });
  assert.equal(r.status, 400);
});

test("full authorization code + PKCE flow returns the key as bearer", async () => {
  const client_id = await registerClient();
  const verifier = b64u(randomBytes(32));
  const challenge = b64u(createHash("sha256").update(verifier).digest());
  const q = new URLSearchParams({ response_type: "code", client_id, redirect_uri: "https://client.example/cb", state: "s1", code_challenge: challenge, code_challenge_method: "S256" });
  const pageRes = await fetch(B + "/oauth/authorize?" + q);
  assert.equal(pageRes.status, 200);
  const html = await pageRes.text();
  const form = html.match(/name="form" value="([^"]+)"/)[1];

  // wrong key: stays on the page
  let post = new URLSearchParams([...q, ["form", form], ["api_key", "bk_live_wrongwrongwrongwrong"], ["decision", "allow"]]);
  let r = await fetch(B + "/oauth/authorize", { method: "POST", body: post, redirect: "manual" });
  assert.equal(r.status, 200);
  assert.match(await r.text(), /not accepted/);

  // tampered redirect: refused, no redirect
  post = new URLSearchParams([...q, ["form", form], ["api_key", "bk_live_testkeytestkey123456"], ["decision", "allow"]]);
  post.set("redirect_uri", "https://evil.example/cb");
  r = await fetch(B + "/oauth/authorize", { method: "POST", body: post, redirect: "manual" });
  assert.equal(r.status, 400);

  post.set("redirect_uri", "https://client.example/cb");
  r = await fetch(B + "/oauth/authorize", { method: "POST", body: post, redirect: "manual" });
  assert.equal(r.status, 302);
  const loc = new URL(r.headers.get("location"));
  assert.equal(loc.origin + loc.pathname, "https://client.example/cb");
  assert.equal(loc.searchParams.get("state"), "s1");
  assert.equal(loc.searchParams.get("iss"), "https://blvkware.dev");
  const code = loc.searchParams.get("code");

  const bad = await fetch(B + "/oauth/token", { method: "POST", body: new URLSearchParams({ grant_type: "authorization_code", code, client_id, redirect_uri: "https://client.example/cb", code_verifier: b64u(randomBytes(32)) }) });
  assert.equal(bad.status, 400);

  const tok = await fetch(B + "/oauth/token", { method: "POST", body: new URLSearchParams({ grant_type: "authorization_code", code, client_id, redirect_uri: "https://client.example/cb", code_verifier: verifier }) });
  assert.equal(tok.status, 200);
  const t = await tok.json();
  assert.equal(t.access_token, "bk_live_testkeytestkey123456");
  assert.equal(t.token_type, "Bearer");
  assert.equal(tok.headers.get("cache-control"), "no-store");
});

test("unknown client and missing PKCE are refused", async () => {
  let r = await fetch(B + "/oauth/authorize?response_type=code&client_id=nope&redirect_uri=https://x.example/cb&code_challenge=" + "a".repeat(43) + "&code_challenge_method=S256");
  assert.equal(r.status, 400);
  const client_id = await registerClient();
  r = await fetch(B + "/oauth/authorize?" + new URLSearchParams({ response_type: "code", client_id, redirect_uri: "https://client.example/cb", state: "z" }), { redirect: "manual" });
  assert.equal(r.status, 302);
  assert.equal(new URL(r.headers.get("location")).searchParams.get("error"), "invalid_request");
});

test("loopback redirect may use any port", async () => {
  const client_id = await registerClient("http://127.0.0.1:3000/callback");
  const q = new URLSearchParams({ response_type: "code", client_id, redirect_uri: "http://127.0.0.1:54321/callback", code_challenge: "b".repeat(43), code_challenge_method: "S256" });
  assert.equal((await fetch(B + "/oauth/authorize?" + q)).status, 200);
});
