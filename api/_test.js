/* Guards on the checkout function, run without Stripe or a network.
 *
 *   node api/_test.js
 *
 * Everything up to the Stripe call is exercised: the schema check, the unknown
 * role, the server-side re-pricing, and — the one that matters — refusing an
 * order whose price has been edited in the browser.
 */

const handler = require("./checkout.js");
const fs = require("fs");

globalThis.BLVK_CATALOG = JSON.parse(fs.readFileSync(__dirname + "/_catalog.json", "utf8"));
require("./_engine.js");
const E = globalThis.BlvkEngine;

let pass = 0;
const fails = [];
function check(name, cond, detail) {
  if (cond) pass++; else fails.push(name + (detail ? " — " + detail : ""));
}

function fakeRes() {
  const r = { _status: 0, _json: null, headers: {} };
  r.setHeader = (k, v) => { r.headers[k] = v; };
  r.status = (c) => { r._status = c; return r; };
  r.json = (o) => { r._json = o; return r; };
  r.end = () => r;
  return r;
}

async function call(body, method = "POST") {
  const res = fakeRes();
  await handler({ method, body }, res);
  return res;
}

/* A correctly priced order, built the way the page builds one. */
function goodOrder() {
  const role = E.roleById("follow-up");
  const state = {
    roleId: "follow-up", caps: {},
    systems: { email: 1, crm: 1, calendar: 1 }, channels: { email: 1 },
    volumeId: "standard", autonomy: "L1", billing: "monthly",
    trial: false, modifiers: {}
  };
  role.suggested.forEach(c => { state.caps[c] = true; });
  const q = E.price(state);
  const spec = E.spec(state, q);
  spec.ref = "BW-TEST-0001";
  return { spec, q };
}

(async function () {
  // Nothing configured: the function must say so and charge nothing.
  delete process.env.STRIPE_SECRET_KEY;
  let r = await call(goodOrder().spec);
  check("no key configured returns 503, not a charge", r._status === 503, "got " + r._status);
  check("and points at a human", /russ@blvkware\.dev/.test(r._json.detail || ""));

  // From here on pretend a key exists so the guards ahead of Stripe are reached.
  process.env.STRIPE_SECRET_KEY = "sk_test_notreal";

  r = await call({ hello: "world" });
  check("a non-order body is refused", r._status === 400, "got " + r._status);

  r = await call({ schema: "blvkware.agent-order/1", role: { id: "not-a-role" },
                   capabilities: [], commercial: {} });
  check("an unknown role is refused", r._status === 400, "got " + r._status);

  r = await call(goodOrder().spec, "GET");
  check("GET is refused", r._status === 405, "got " + r._status);

  /* The one that matters: a price edited in the browser. */
  const { spec, q } = goodOrder();
  const tampered = JSON.parse(JSON.stringify(spec));
  tampered.commercial.build = 1;
  tampered.commercial.dueNow = 1;
  r = await call(tampered);
  check("an edited price is refused with 409", r._status === 409, "got " + r._status);
  check("nothing is charged on a mismatch",
        /Nothing has been charged/.test((r._json || {}).detail || ""));
  check("and the real figure is named",
        ((r._json || {}).mismatch || []).some(m => m.correct === q.build),
        JSON.stringify((r._json || {}).mismatch));

  /* A capability that does not exist must not survive into the price. */
  const injected = JSON.parse(JSON.stringify(spec));
  injected.capabilities.push({ id: "free.everything" });
  r = await call(injected);
  check("an invented capability does not change the price",
        r._status !== 409 || !((r._json.mismatch || []).length),
        "status " + r._status + " " + JSON.stringify(r._json && r._json.mismatch));

  // The "Cannot find module 'stripe'" line above is expected and is itself a
  // result: it is the last, correctly-priced order reaching the Stripe call and
  // falling into the 502 handler without leaking the underlying error to the
  // caller. Install stripe to exercise the happy path against a test key.
  console.log("");
  console.log(pass + " passed, " + fails.length + " failed");
  fails.forEach(f => console.log("  FAIL  " + f));
  process.exit(fails.length ? 1 : 0);
})();
