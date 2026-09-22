// Screenshot each card through one headless Edge over the DevTools protocol.
//   node shoot.mjs jobs.json
// jobs.json: [{"html": "C:/.../card.html", "out": "C:/.../slug.png"}, ...]
// Prints one line per card: "<fit|overflow> <out>". The template sets
// body[data-ready] once fonts have loaded and the text has been fitted, so a
// card is never captured mid-layout.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const EDGE = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
].find(existsSync);
if (!EDGE) { console.error("no Edge or Chrome found"); process.exit(2); }

const port = 9800 + Math.floor(Math.random() * 150);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars",
  "--allow-file-access-from-files", `--remote-debugging-port=${port}`,
  `--user-data-dir=${mkdtempSync(join(tmpdir(), "og-"))}`, "--window-size=1200,630", "about:blank"],
  { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 60 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0;
const waiting = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
});
const send = (method, params = {}) =>
  new Promise((r) => { const id = ++seq; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const value = async (expr) =>
  (await send("Runtime.evaluate", { expression: expr, returnByValue: true })).result?.result?.value;

await send("Emulation.setDeviceMetricsOverride", { width: 1200, height: 630, deviceScaleFactor: 1, mobile: false });
let failed = 0;
for (const job of jobs) {
  await send("Page.navigate", { url: pathToFileURL(job.html).href });
  let ready = null;
  for (let i = 0; i < 100 && !ready; i++) { await sleep(100); ready = await value("document.body && document.body.dataset.ready"); }
  const shot = await send("Page.captureScreenshot", { format: "png", clip: { x: 0, y: 0, width: 1200, height: 630, scale: 1 } });
  writeFileSync(job.out, Buffer.from(shot.result.data, "base64"));
  if (ready !== "fit") failed++;
  console.log(`${ready || "timeout"} ${job.out}`);
}
ws.close();
edge.kill();
process.exit(failed ? 1 : 0);
