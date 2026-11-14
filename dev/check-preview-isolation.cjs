#!/usr/bin/env node
// Regression check for the generated-code trust boundary in the App Builder.
//
//   node dev/check-preview-isolation.cjs        (needs Playwright + Chromium)
//
// Seeds a synthetic provider key and a saved build into the builder's storage,
// opens the build in the preview and in "open in new tab", and asserts that the
// generated code cannot read the key through parent, top or its own storage,
// while an ordinary app can still use localStorage and the builder console
// still receives the app's console output. Exits 1 on any failure.
"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.join(__dirname, "..", "docs");
const KEY = "SYNTHETIC_KEY_NOT_A_SECRET";
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json", ".webp": "image/webp", ".png": "image/png" };

const payload = '<!doctype html><html><head><title>t</title></head><body><p id="r">...</p><script>' +
  'var o=[];' +
  'try{o.push("PARENT:"+parent.localStorage.getItem("blvkware.byok.key"))}catch(e){o.push("PARENT_BLOCKED")}' +
  'try{o.push("TOP:"+top.localStorage.getItem("blvkware.byok.key"))}catch(e){o.push("TOP_BLOCKED")}' +
  'try{o.push("OWN:"+localStorage.getItem("blvkware.byok.key"))}catch(e){o.push("OWN_THROWS")}' +
  'try{localStorage.setItem("todo","milk");o.push("APPSTORE:"+localStorage.getItem("todo"))}catch(e){o.push("APPSTORE_THROWS")}' +
  'document.getElementById("r").textContent=o.join("|");console.log("isolation-probe-ok");' +
  "<" + "/script></body></html>";

function serve() {
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
    if (p.endsWith("/")) p += "index.html";
    const file = path.join(ROOT, p);
    if (!file.startsWith(ROOT) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
    res.writeHead(200, { "content-type": TYPES[path.extname(file)] || "application/octet-stream" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((ok) => server.listen(0, "127.0.0.1", () => ok(server)));
}

const failures = [];
function expect(label, text) {
  if (text.includes(KEY)) failures.push(`${label}: generated code read the key (${text})`);
  if (!text.includes("PARENT_BLOCKED") || !text.includes("TOP_BLOCKED")) failures.push(`${label}: parent/top storage reachable (${text})`);
  if (!text.includes("APPSTORE:milk")) failures.push(`${label}: app localStorage broken (${text})`);
  console.log(`${label}: ${text}`);
}

(async () => {
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch();
  try {
    const ctx = await browser.newContext();
    await ctx.addInitScript(([p, k]) => {
      if (!location.pathname.startsWith("/build")) return;
      localStorage.setItem("blvkware.byok.key", k);
      localStorage.setItem("blvkware.htmlgen.v1", JSON.stringify([{ id: "isolation", title: "Isolation check", prompt: "x", html: p, size: p.length, ts: Date.now(), type: "app" }]));
    }, [payload, KEY]);
    const page = await ctx.newPage();
    await page.goto(base + "/build/");
    await page.evaluate(() => document.querySelector('.hist-item[data-id="isolation"]').click());
    expect("preview", await page.frameLocator("#preview").locator("#r").textContent({ timeout: 10000 }));
    await page.waitForTimeout(400);
    if (!(await page.evaluate(() => document.getElementById("logList").textContent.includes("isolation-probe-ok"))))
      failures.push("console: preview output did not reach the builder console");
    else console.log("console: preview output reaches the builder console");
    const [tab] = await Promise.all([ctx.waitForEvent("page", { timeout: 10000 }), page.evaluate(() => document.getElementById("openBtn").click())]).catch(() => [null]);
    if (!tab) failures.push("new tab: could not open");
    else {
      await tab.waitForLoadState();
      // The isolated page wraps the app in a sandboxed iframe; an unisolated one
      // runs it at the top level, which is itself the failure.
      const framed = (await tab.locator("iframe").count()) > 0;
      const where = framed ? tab.frameLocator("iframe").first() : tab;
      expect("new tab", await where.locator("#r").textContent({ timeout: 10000 }));
    }
  } finally {
    await browser.close();
    server.close();
  }
  if (failures.length) { console.error("FAIL\n  " + failures.join("\n  ")); process.exit(1); }
  console.log("PASS: generated code cannot read the builder's storage");
})().catch((e) => { console.error(e); process.exit(1); });
