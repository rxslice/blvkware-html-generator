// node scenes.mjs <page.html> <count> <outdir> <size>
// Screenshots page.html?f=0..count-1 at size x size with headless Edge (DevTools),
// because Edge's --screenshot flag silently writes nothing on some installs.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [page, count, outdir, size] = process.argv.slice(2);
const S = +size;
const EDGE = ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe"].find(existsSync);
const profile = mkdtempSync(join(tmpdir(), "scn-"));
const port = 9200 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--window-size=${S},${S}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 80 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0; const waiting = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); } });
const send = (method, params = {}) => new Promise((r) => { const id = ++seq; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: S, height: S, deviceScaleFactor: 1, mobile: false });
const base = pathToFileURL(resolve(page)).href;
for (let f = 0; f < +count; f++) {
  await send("Page.navigate", { url: `${base}?f=${f}` });
  await sleep(900);
  await send("Runtime.evaluate", { expression: "document.fonts.ready.then(()=>1)", awaitPromise: true });
  await sleep(200);
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(outdir, `s${f}.png`), Buffer.from(shot.result.data, "base64"));
}
ws.close(); edge.kill();
await new Promise((r) => { edge.once("exit", r); setTimeout(r, 3000); });
try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
process.exit(0);
