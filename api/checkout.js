/* Create a Stripe Checkout Session for an agent order.
 *
 * THE RULE THIS FILE EXISTS TO ENFORCE: the price is never taken from the
 * request. The browser sends a specification; this function re-derives the
 * whole quote from the catalog using the same engine the configurator uses, and
 * charges *that*. Anyone can open devtools and change what the page sends, so a
 * client-supplied amount is not a price, it is a suggestion.
 *
 * If the recomputed price differs from what the buyer was shown, the order is
 * refused rather than silently charged at the higher number. A buyer who is
 * charged something they did not see, even correctly, will dispute it — and
 * they would be right to.
 *
 * Deploy target: any Node serverless platform (Vercel, Netlify, Cloudflare
 * Workers with the node compat flag). GitHub Pages cannot run this, which is
 * why it lives outside docs/ and deploys separately. See api/README.md.
 *
 * Environment:
 *   STRIPE_SECRET_KEY   required
 *   PUBLIC_BASE_URL     defaults to https://blvkware.dev
 *   ALLOWED_ORIGIN      defaults to https://blvkware.dev
 */

const fs = require("fs");
const path = require("path");

// Compiled from dev/catalog.py and dev/engine.js by dev/build-static.py, so the
// server prices from the same source as the page. Nothing here holds its own
// copy of a number.
const CATALOG = JSON.parse(
  fs.readFileSync(path.join(__dirname, "_catalog.json"), "utf8"));
globalThis.BLVK_CATALOG = CATALOG;
require("./_engine.js");
const E = globalThis.BlvkEngine;

const BASE = process.env.PUBLIC_BASE_URL || "https://blvkware.dev";
const ORIGIN = process.env.ALLOWED_ORIGIN || "https://blvkware.dev";

function money(n) { return "$" + Number(n).toLocaleString("en-US"); }

/* Rebuild the engine's state object from a submitted specification. Only ids
 * the catalog knows are accepted; everything else is dropped, so a crafted
 * request cannot introduce a capability that does not exist. */
function stateFrom(spec) {
  const state = {
    roleId: spec.role && spec.role.id,
    caps: {}, systems: {}, channels: {},
    volumeId: (spec.volume || {}).id,
    autonomy: spec.autonomy || "L1",
    billing: (spec.commercial || {}).billing === "annual" ? "annual" : "monthly",
    trial: !!(spec.commercial || {}).trial,
    modifiers: { rush: !!(spec.delivery || {}).rush }
  };
  (spec.capabilities || []).forEach(c => {
    const id = c && (c.id || c);
    if (E.capById(id)) state.caps[id] = true;
  });
  (spec.integrations || []).forEach(i => {
    const id = i && (i.id || i);
    if (CATALOG.integrations.some(x => x.id === id)) state.systems[id] = true;
  });
  (spec.channels || []).forEach(c => {
    const id = c && (c.id || c);
    if (CATALOG.channels.some(x => x.id === id)) state.channels[id] = true;
  });
  return state;
}

function lineItems(q, role) {
  const items = [];
  if (q.trial) {
    items.push({
      quantity: 1,
      price_data: {
        currency: "usd",
        unit_amount: q.credit * 100,
        product_data: {
          name: "Agent Trial — 14 days",
          description:
            `${role.name}. Fourteen days on your real data at Draft autonomy. ` +
            `Credited in full against the ${money(q.build)} build if you continue.`
        }
      }
    });
    return items;
  }
  items.push({
    quantity: 1,
    price_data: {
      currency: "usd",
      unit_amount: q.build * 100,
      product_data: {
        name: `${role.name} — build`,
        description: `${q.def.label}. Live in ${q.days} business days. ` +
                     `Goes live at L1 Draft.`
      }
    }
  });
  items.push({
    quantity: 1,
    price_data: {
      currency: "usd",
      unit_amount: q.recurring * 100,
      product_data: {
        name: q.billing === "annual"
          ? "Agent Operations — first year"
          : "Agent Operations — first month",
        description:
          "Hosting, model costs, monitoring, unlimited tuning, integration " +
          "repairs, business-hours support, and a monthly report. " +
          (q.billing === "annual"
            ? "Twelve months for the price of ten."
            : "Cancel any month with thirty days' notice.")
      }
    }
  });
  return items;
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", ORIGIN);
  res.setHeader("Access-Control-Allow-Headers", "content-type");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  if (!process.env.STRIPE_SECRET_KEY) {
    return res.status(503).json({
      error: "Checkout is not configured yet.",
      detail: "Email russ@blvkware.dev and the order will be invoiced by hand."
    });
  }

  let spec = req.body;
  if (typeof spec === "string") {
    try { spec = JSON.parse(spec); }
    catch (e) { return res.status(400).json({ error: "Body is not JSON." }); }
  }
  if (!spec || spec.schema !== "blvkware.agent-order/1") {
    return res.status(400).json({ error: "Not a BlvkWare agent order." });
  }

  const role = E.roleById(spec.role && spec.role.id);
  if (!role) return res.status(400).json({ error: "Unknown role." });

  // The price, re-derived. This is the only number that is charged.
  const q = E.price(stateFrom(spec));
  if (!q) return res.status(400).json({ error: "That order cannot be priced." });

  // What the buyer was shown. If it disagrees, refuse — do not quietly charge
  // the correct amount for something they never saw.
  const shown = spec.commercial || {};
  const mismatch = [];
  if (shown.build != null && Number(shown.build) !== q.build) {
    mismatch.push({ line: "build", shown: shown.build, correct: q.build });
  }
  if (shown.dueNow != null && Number(shown.dueNow) !== q.dueNow) {
    mismatch.push({ line: "dueNow", shown: shown.dueNow, correct: q.dueNow });
  }
  if (mismatch.length) {
    return res.status(409).json({
      error: "The price on this order no longer matches the catalog.",
      detail: "Nothing has been charged. Reload the configurator and the " +
              "current price will be shown.",
      mismatch
    });
  }

  const ref = (typeof spec.ref === "string" && /^[A-Z0-9-]{4,32}$/.test(spec.ref))
    ? spec.ref
    : "BW-" + Date.now().toString(36).toUpperCase();

  try {
    const stripe = require("stripe")(process.env.STRIPE_SECRET_KEY);
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: lineItems(q, role),
      customer_email: (spec.business || {}).email || undefined,
      client_reference_id: ref,
      // The manifest is far larger than Stripe's metadata limits, so only the
      // reference travels. The buyer's browser keeps the specification and
      // hands it to the forge on return.
      metadata: {
        ref,
        role: role.id,
        tier: String(q.tier.key),
        build: String(q.build),
        recurring: String(q.recurring),
        billing: q.billing,
        trial: String(q.trial)
      },
      success_url: `${BASE}/hire/?paid=1&ref=${encodeURIComponent(ref)}`,
      cancel_url: `${BASE}/hire/?cancelled=1`
    });
    return res.status(200).json({ url: session.url, ref, quoted: q.dueNow });
  } catch (e) {
    // Never leak a Stripe error verbatim: it can carry account detail.
    console.error("checkout failed", e);
    return res.status(502).json({
      error: "Checkout could not be started.",
      detail: "Nothing has been charged. Email russ@blvkware.dev and the order " +
              "will be invoiced by hand."
    });
  }
};
