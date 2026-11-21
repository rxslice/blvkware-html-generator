// x402 v2 pay-per-call gateway at https://blvkware.dev/api/v1.
//
// The paid work is done by CORDON, which already verifies and settles x402
// itself. This gateway has no free tier: an unpaid call gets a 402 with the
// exact requirements CORDON will accept (same network, asset, amount and
// payTo, read from CORDON's public pricing), and a paid call is forwarded to
// CORDON with its PAYMENT-SIGNATURE. CORDON settles only after it has done the
// work, and returns PAYMENT-RESPONSE, which is passed back unchanged. This
// gateway never holds funds or keys.

export const CORDON = "https://cordon.blvkware.dev";
const ASSETS = {
  "eip155:8453": { asset: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", name: "USD Coin", version: "2" },
  "eip155:84532": { asset: "0x036CbD53842c5426634e7929541eC2318f3dCF7e", name: "USDC", version: "2" },
};
export const READ_UNITS = 2; // CORDON charges 2 units for a page read

let cached = null;
export async function cordonX402() {
  if (cached && cached.at > Date.now() - 600000) return cached.x;
  const r = await fetch(CORDON + "/v1/pricing", { headers: { accept: "application/json" }, cf: { cacheTtl: 300 } });
  const p = await r.json();
  const x = p && p.x402 && p.x402.enabled && ASSETS[p.x402.network] && /^0x[a-fA-F0-9]{40}$/.test(p.x402.payTo || "")
    ? { network: p.x402.network, payTo: p.x402.payTo, atomicPerUnit: parseInt(p.x402.atomic_per_unit, 10), usdPerUnit: p.x402.usd_per_unit }
    : null;
  cached = { at: Date.now(), x };
  return x;
}

export function requirements(x, units) {
  const a = ASSETS[x.network];
  return { scheme: "exact", network: x.network, asset: a.asset, amount: String(units * x.atomicPerUnit), payTo: x.payTo, maxTimeoutSeconds: 120, extra: { name: a.name, version: a.version } };
}

export function paymentRequired(x, resourceUrl, description, units, reason) {
  return {
    x402Version: 2,
    error: reason || "payment_required",
    resource: { url: resourceUrl, description, mimeType: "application/json" },
    accepts: [requirements(x, units)],
  };
}

const b64 = (s) => btoa(String.fromCharCode(...new TextEncoder().encode(s)));

function reply(body, status, extra = {}) {
  return new Response(JSON.stringify(body, null, 2) + "\n", {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "content-type, payment-signature",
      "access-control-expose-headers": "payment-required, payment-response",
      "cache-control": "no-store",
      ...extra,
    },
  });
}

export async function handleApi(request, url) {
  if (request.method === "OPTIONS") return reply(null, 204);
  const x = await cordonX402();
  if (!x) return reply({ error: "x402_unavailable", message: "Pay-per-call is temporarily unavailable. CORDON's free tier and API keys still work at " + CORDON }, 503);
  const p = url.pathname.replace(/\/+$/, "");
  const readUrl = url.origin + "/api/v1/read";
  const index = {
    service: "BlvkWare pay-per-call API (x402 v2)",
    description: "No account, no key: pay per call in USDC on Base with x402. Each call is served by CORDON, which strips hidden prompt-injection payloads from web content before an agent reads it.",
    endpoints: {
      read: { method: "GET", url: readUrl + "?url=<absolute url>", price_usd: (READ_UNITS * Number(x.usdPerUnit)).toFixed(4), returns: "verdict (clean | suspicious | hostile) and cleaned markdown" },
    },
    how_to_pay: "Call without payment to receive 402 with a PAYMENT-REQUIRED header (base64 JSON, x402 v2). Sign the payment and retry with PAYMENT-SIGNATURE. The response carries PAYMENT-RESPONSE with the settlement transaction.",
    free_alternative: CORDON + "/v1/read?url= (50 units per day per address, no payment)",
    docs: "https://blvkware.dev/auth.md",
  };

  if (p === "/api" || p === "/api/v1") {
    // The service root advertises its default paid operation, the x402 way.
    const pr = paymentRequired(x, readUrl, "CORDON safe read: one web page, cleaned of hidden instructions", READ_UNITS);
    return reply({ ...index, ...pr }, 402, { "payment-required": b64(JSON.stringify(pr)) });
  }
  if (p !== "/api/v1/read") return reply({ error: "not_found", ...index }, 404);
  if (request.method !== "GET") return reply({ error: "method_not_allowed" }, 405, { allow: "GET, OPTIONS" });

  const target = url.searchParams.get("url") || "";
  if (!/^https?:\/\//i.test(target)) return reply({ error: "invalid_request", message: "Pass ?url= with an absolute http(s) URL. Nothing was charged." }, 400);
  const resource = readUrl + "?url=" + encodeURIComponent(target);
  const sig = request.headers.get("payment-signature") || request.headers.get("x-payment");
  if (!sig) {
    const pr = paymentRequired(x, resource, "CORDON safe read of " + target, READ_UNITS);
    return reply({ error: "payment_required", ...pr }, 402, { "payment-required": b64(JSON.stringify(pr)) });
  }
  const fwd = new URL(CORDON + "/v1/read");
  for (const [k, v] of url.searchParams) fwd.searchParams.set(k, v);
  const r = await fetch(fwd, { headers: { "payment-signature": sig, accept: "application/json", "user-agent": "blvkware-edge-x402-gateway" } });
  const h = {};
  for (const k of ["payment-required", "payment-response"]) { const v = r.headers.get(k); if (v) h[k] = v; }
  return reply(await r.json().catch(() => ({ error: "upstream_error" })), r.status, h);
}
