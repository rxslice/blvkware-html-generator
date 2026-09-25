// node marketing/video/record.mjs [baseUrl]
//
// Records the launch demo: a real walk through the live kit page, driven by
// script, with a drawn cursor, captions, and a title and end card painted into
// the page itself (so there is no white flash between scenes). Frames come from
// Edge's screencast with their timestamps, then ffmpeg turns them into a
// constant-rate 1080p H.264 MP4.
//
// Writes marketing/video/out/blvkware-kits-demo.mp4 (and a poster frame).
// Needs ffmpeg: set FFMPEG, or `pip install imageio-ffmpeg` and it is found.
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const BASE = (process.argv[2] || "https://blvkware.dev").replace(/\/$/, "");
const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "out");
const W = 1440, H = 810, SCALE = 4 / 3;            // 1920x1080 pixels
mkdirSync(OUT, { recursive: true });

const FFMPEG = process.env.FFMPEG || (() => {
  try { return execFileSync("python", ["-c", "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())"]).toString().trim(); }
  catch { return "ffmpeg"; }
})();

const EDGE = ["C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe"].find(existsSync);
if (!EDGE) { console.error("no Edge found"); process.exit(2); }
const profile = mkdtempSync(join(tmpdir(), "rec-"));
const frames = mkdtempSync(join(tmpdir(), "rec-frames-"));
const port = 9300 + Math.floor(Math.random() * 90);
const edge = spawn(EDGE, ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  `--window-size=${W},${H}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let target;
for (let i = 0; i < 80 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page"); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0; const waiting = new Map(); const errors = [];

// ---- the frame log: [{file, t}], t on a clock that stops while paused ----
const shots = []; let recording = false; let pausedFor = 0; let pauseAt = 0;
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  if (m.method === "Page.screencastFrame") {
    const { data, sessionId, metadata } = m.params;
    ws.send(JSON.stringify({ id: ++seq, method: "Page.screencastFrameAck", params: { sessionId } }));
    if (!recording) return;
    const file = join(frames, `f${String(shots.length).padStart(5, "0")}.jpg`);
    writeFileSync(file, Buffer.from(data, "base64"));
    shots.push({ file, t: metadata.timestamp - pausedFor });
  }
});
const send = (method, params = {}) => new Promise((r) => { const id = ++seq; waiting.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const ev = async (expr) => {
  const r = await send("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result?.exceptionDetails) throw new Error("eval: " + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text) + "\n" + expr.slice(0, 200));
  return r.result?.result?.value;
};
const pause = () => { recording = false; pauseAt = Date.now() / 1000; };
const resume = () => { if (pauseAt) pausedFor += Date.now() / 1000 - pauseAt; pauseAt = 0; recording = true; };

// ---- the stage: cursor, captions and cards, injected into every document ----
const STAGE = String.raw`
(() => {
  const css = document.createElement("style");
  css.textContent = ${"`"}
    html { scroll-behavior: auto !important; }
    #rec-cover { position: fixed; inset: 0; z-index: 2147483600; background: #0A0908; transition: opacity .7s ease; }
    #rec-cursor { position: fixed; left: 0; top: 0; z-index: 2147483647; width: 26px; height: 26px; pointer-events: none;
      transform: translate(${W / 2}px, ${H / 2 + 120}px); transition: transform .7s cubic-bezier(.45,.05,.2,1), opacity .3s; opacity: 0;
      filter: drop-shadow(0 2px 3px rgba(0,0,0,.6)); }
    #rec-cursor.press svg { transform: scale(.86); transform-origin: 3px 3px; }
    .rec-ring { position: fixed; z-index: 2147483646; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
      border: 3px solid #D4F24A; pointer-events: none; animation: rec-ring .55s ease-out forwards; }
    @keyframes rec-ring { from { transform: scale(.3); opacity: .95; } to { transform: scale(1.5); opacity: 0; } }
    #rec-cap { position: fixed; left: 0; right: 0; margin: 0 auto; width: fit-content; bottom: 34px; z-index: 2147483640; transform: translateY(16px); opacity: 0;
      transition: opacity .35s ease, transform .35s ease; max-width: 1240px; white-space: nowrap; pointer-events: none;
      display: flex; align-items: center; gap: 16px; padding: 16px 26px 17px 18px; border-radius: 16px;
      background: rgba(12,11,9,.93); border: 1px solid rgba(245,240,230,.14); box-shadow: 0 18px 50px -12px rgba(0,0,0,.85);
      font-family: Manrope, system-ui, sans-serif; color: #F5F0E6; font-size: 25px; font-weight: 700; letter-spacing: -.01em; line-height: 1.25; }
    #rec-cap.on { opacity: 1; transform: none; }
    #rec-cap b { flex: none; display: grid; place-items: center; min-width: 38px; height: 38px; padding: 0 9px; border-radius: 10px;
      background: #D4F24A; color: #15170A; font-size: 20px; font-weight: 800; }
    #rec-cap b:empty { display: none; }
    #rec-cap span i { font-style: normal; color: #D4F24A; }
    .rec-card { position: fixed; inset: 0; z-index: 2147483620; display: grid; place-content: center; justify-items: center; text-align: center;
      background: radial-gradient(900px 520px at 50% 38%, rgba(212,242,74,.10), transparent 70%), #0A0908;
      font-family: Manrope, system-ui, sans-serif; color: #F5F0E6; transition: opacity .8s ease; }
    .rec-card img { width: 112px; height: 112px; border-radius: 26px; margin-bottom: 30px; }
    .rec-card .eb { font-family: "Fira Code", ui-monospace, monospace; font-size: 17px; font-weight: 600; letter-spacing: .28em; color: #D4F24A; text-transform: uppercase; margin-bottom: 22px; }
    .rec-card h1 { font-size: 68px; line-height: 1.02; font-weight: 800; letter-spacing: -.045em; margin: 0 0 26px; max-width: 1060px; }
    .rec-card h1 em { font-style: normal; color: #D4F24A; }
    .rec-card p { font-size: 27px; font-weight: 600; color: #B3A894; margin: 0; line-height: 1.4; }
    .rec-card p b { color: #F5F0E6; }
    .rec-card .url { margin-top: 38px; display: inline-block; background: #D4F24A; color: #15170A; font-weight: 800; font-size: 30px;
      padding: 14px 26px 16px; border-radius: 14px; letter-spacing: -.01em; }
    .rec-card .small { margin-top: 20px; font-size: 21px; color: #7F7565; font-family: "Fira Code", ui-monospace, monospace; font-weight: 500; }
    .rec-card .small b { color: #B3A894; font-weight: 600; }
  ${"`"};
  const mount = () => {
    document.head.appendChild(css);
    const cover = document.createElement("div"); cover.id = "rec-cover"; document.body.appendChild(cover);
    const cur = document.createElement("div"); cur.id = "rec-cursor";
    cur.innerHTML = '<svg viewBox="0 0 26 26" width="26" height="26"><path d="M3 2 L3 21 L8.2 16.4 L11.6 24 L15 22.5 L11.7 15 L19 15 Z" fill="#F5F0E6" stroke="#0A0908" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.body.appendChild(cur);
    const cap = document.createElement("div"); cap.id = "rec-cap"; cap.innerHTML = "<b></b><span></span>"; document.body.appendChild(cap);
    // The screencast only sends a frame when something repaints, so a still
    // moment would vanish from the video. One pixel flickering between two
    // indistinguishable darks keeps frames coming at ~12 per second.
    const tick = document.createElement("div");
    tick.style.cssText = "position:fixed;right:0;bottom:0;width:1px;height:1px;z-index:2147483647;pointer-events:none";
    document.body.appendChild(tick);
    let odd = false; setInterval(() => { odd = !odd; tick.style.background = odd ? "#0A0908" : "#0B0A09"; }, 80);
  };
  if (document.body) mount(); else document.addEventListener("DOMContentLoaded", mount);

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  let at = [${W / 2}, ${H / 2 + 120}];
  window.rec = {
    reveal: async () => { const c = document.getElementById("rec-cover"); c.style.opacity = 0; await wait(750); c.remove(); },
    blackout: async () => { const c = document.createElement("div"); c.id = "rec-cover"; c.style.opacity = 0; document.body.appendChild(c);
      c.getBoundingClientRect(); c.style.opacity = 1; await wait(750); },
    cursor: (on) => { document.getElementById("rec-cursor").style.opacity = on ? 1 : 0; },
    moveTo: async (x, y, ms = 700) => {
      const c = document.getElementById("rec-cursor");
      c.style.transitionDuration = ms + "ms, .3s";
      c.style.transform = "translate(" + x + "px," + y + "px)"; at = [x, y]; await wait(ms + 40);
    },
    ring: () => { const r = document.createElement("div"); r.className = "rec-ring"; r.style.left = at[0] + "px"; r.style.top = at[1] + "px";
      document.body.appendChild(r); const c = document.getElementById("rec-cursor"); c.classList.add("press");
      setTimeout(() => c.classList.remove("press"), 140); setTimeout(() => r.remove(), 700); },
    point: (sel, fx = .5, fy = .5) => { const e = typeof sel === "string" ? document.querySelector(sel) : sel;
      const r = e.getBoundingClientRect(); return [Math.round(r.left + r.width * fx), Math.round(r.top + r.height * fy)]; },
    caption: async (num, html) => {
      const cap = document.getElementById("rec-cap");
      if (cap.classList.contains("on")) { cap.classList.remove("on"); await wait(360); }
      if (!html) return;
      cap.querySelector("b").textContent = num || ""; cap.querySelector("span").innerHTML = html;
      cap.getBoundingClientRect(); cap.classList.add("on"); await wait(360);
    },
    scrollTo: (y, ms = 1200) => new Promise((res) => {
      const s = scrollY, d = Math.max(0, Math.min(y, document.documentElement.scrollHeight - innerHeight)) - s, t0 = performance.now();
      if (Math.abs(d) < 2) return res();
      const f = (t) => { const p = Math.min(1, (t - t0) / ms), e = p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        scrollTo(0, s + d * e); p < 1 ? requestAnimationFrame(f) : res(); };
      requestAnimationFrame(f);
    }),
    top: (sel, pad = 90) => { const e = document.querySelector(sel); return Math.round(e.getBoundingClientRect().top + scrollY - pad); },
    card: async (html, fade = true) => {
      const c = document.createElement("div"); c.className = "rec-card"; c.innerHTML = html; if (fade) c.style.opacity = 0;
      document.body.appendChild(c); c.getBoundingClientRect(); c.style.opacity = 1; await wait(fade ? 820 : 0); return true;
    },
    uncard: async () => { const c = document.querySelector(".rec-card"); c.style.opacity = 0; await wait(820); c.remove(); },
  };
})();
`;

await send("Runtime.enable"); await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: SCALE, mobile: false });
await send("Page.addScriptToEvaluateOnNewDocument", { source: STAGE });
await send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });

const rec = (js) => ev(`(async()=>{ ${js} })()`);
const goto = async (path) => {
  await send("Page.navigate", { url: BASE + path });
  await sleep(3000);
  await ev("document.fonts.ready.then(()=>1)");
  await sleep(400);
};
// Real input at the drawn cursor, so hover and focus styles show as they would.
const mouse = async (x, y) => send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
const move = async (sel, ms = 700, fx = .5, fy = .5) => {
  const [x, y] = await ev(`rec.point(${JSON.stringify(sel)}, ${fx}, ${fy})`);
  await rec(`await rec.moveTo(${x}, ${y}, ${ms})`); await mouse(x, y); return [x, y];
};
const click = async (sel, ms = 700, fx = .5, fy = .5) => {
  const [x, y] = await move(sel, ms, fx, fy);
  await sleep(120); await ev("rec.ring()");
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(70);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
};
const type = async (text, per = 38) => { for (const ch of text) { await send("Input.insertText", { text: ch }); await sleep(per + Math.random() * 22); } };
const cap = (n, html) => rec(`await rec.caption(${JSON.stringify(n)}, ${JSON.stringify(html)})`);
const scrollTo = (sel, ms = 1200, pad = 90) => rec(`await rec.scrollTo(rec.top(${JSON.stringify(sel)}, ${pad}), ${ms})`);
const scrollBy = (dy, ms = 1200) => rec(`await rec.scrollTo(scrollY + ${dy}, ${ms})`);
const roleSel = (name) => `[...document.querySelectorAll('#roles .role')].find(r => r.innerText.split('\\n')[0].trim() === ${JSON.stringify(name)})`;
const optSel = (box, re) => `[...document.querySelectorAll('${box} .opt')].find(o => ${re}.test(o.innerText))`;
// rec.point takes a selector or an element; pass an expression that yields the element.
const moveEl = async (expr, ms = 700) => {
  const [x, y] = await ev(`rec.point(${expr}, .5, .5)`); await rec(`await rec.moveTo(${x}, ${y}, ${ms})`); await mouse(x, y); return [x, y];
};
const clickEl = async (expr, ms = 700) => {
  const [x, y] = await moveEl(expr, ms);
  await sleep(120); await ev("rec.ring()");
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(70);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
};

// ======================= the film =======================
await goto("/hire/");
await rec(`await rec.card(${JSON.stringify(`
  <img src="/assets/logo-512.png" alt="">
  <div class="eb">BlvkWare agent kits</div>
  <h1>Design an AI agent for <em>one job</em><br>in your business.</h1>
  <p>See every file it needs <b>before you pay</b>.</p>`)}, false)`);
await ev("document.getElementById('rec-cover').remove()");
resume();
await sleep(3600);
await rec("await rec.uncard()");

// 1. the job
await cap("", "Start at <i>blvkware.dev/hire</i>");
await ev("rec.cursor(true)");
await sleep(1300);
await scrollTo("#s-role", 1300, 40);
await cap("1", "Pick the job the agent should <i>own</i>");
await click("#role-find", 800);
await sleep(250);
await type("follow", 70);
await sleep(700);
await moveEl(roleSel("Follow-Up Agent"), 700);
await sleep(500);
await clickEl(roleSel("Follow-Up Agent"), 200);
await sleep(1800);                                     // the page scrolls itself to step 2

// 2. systems
await cap("2", "Tick the systems it may touch. Its tools are written for <i>those</i>.");
await clickEl(optSel("#systems", "/^Email/"), 700);  await sleep(350);
await clickEl(optSel("#systems", "/^CRM/"), 600);    await sleep(350);
await clickEl(optSel("#systems", "/^Accounting/"), 600); await sleep(900);

// 3. capabilities
await scrollTo("#s-caps", 1300);
await cap("3", "Choose what it handles. The core job is always in.");
await sleep(600);
// The job's recommended extras arrive ticked; only tick the ones that are not.
for (const re of ["/Interaction logging/", "/Document generation/"]) {
  const el = optSel("#suggested", re);
  if (await ev(`!!${el} && !${el}.querySelector('input').checked`)) await clickEl(el, 700);
  else if (await ev(`!!${el}`)) await moveEl(el, 700);
  await sleep(450);
}
await sleep(700);

// 4. autonomy
await scrollTo("#s-auto", 1300);
await cap("4", "Decide how much it may do alone. It <i>starts at Draft</i>.");
await sleep(500);
await clickEl(`document.querySelectorAll('#autonomy .rung')[2]`, 800); await sleep(1700);
await clickEl(`document.querySelectorAll('#autonomy .rung')[1]`, 600); await sleep(1100);

// 5. your business, your rules
await scrollTo("#s-you", 1300);
await cap("5", "Tell it about your business, and what it must <i>never</i> do");
await click("#f-biz", 700); await type("Delta Plumbing Co.", 34);
await click("#f-what", 500); await type("Plumbing, 6 vans, Jackson MS", 30);
await click("#f-never", 600); await type("Never quote a price. Never promise a date I haven't confirmed.", 24);
await sleep(700);

// the kit
await cap("", "Then see the kit");
await click("#go", 900);
await sleep(1600);
await cap("", "Every file your kit contains, shown <i>before you pay</i>");
for (let i = 0; i < 40; i++) {                        // wait for the file list
  if (await ev("!!document.querySelector('#kittree .f')")) break;
  await sleep(250);
}
await sleep(1500);
await scrollTo("#kittree", 1500, 150);
await sleep(1000);
await scrollBy(560, 3200);
await sleep(400);
await cap("", "The tests it must pass, and the rules it must never break");
await scrollTo(".speccard .tests", 2600, 200);
await sleep(1600);
await scrollTo("#buy", 1600, 330);
await cap("", "<i>$79</i> for one job, <i>$199</i> for a whole function. One-off.");
await move("#buy", 800);
await sleep(2400);

// the sample
await rec("await rec.caption('', ''); rec.cursor(false); await rec.blackout()");
pause();
await goto("/sample-kit/");
await ev("rec.cursor(false)");
resume();
await rec("await rec.reveal()");
await cap("", "Want to read one first? A complete sample kit is <i>free</i>.");
await sleep(900);
await scrollBy(700, 2800);
await sleep(500);
await scrollBy(700, 2800);
await sleep(900);

// end card
await rec("await rec.caption('', '')");
await rec(`await rec.card(${JSON.stringify(`
  <img src="/assets/logo-512.png" alt="">
  <h1>Design your agent.<br><em>Download the kit.</em></h1>
  <p>Instructions, tools, workflows, records, guardrails and tests.</p>
  <div class="url">blvkware.dev/hire</div>
  <div class="small">free sample kit: <b>blvkware.dev/sample-kit</b></div>`)})`);
await sleep(4200);
pause();

await send("Page.stopScreencast");
ws.close(); edge.kill();
await new Promise((r) => { edge.once("exit", r); setTimeout(r, 3000); });
try { rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 }); } catch {}
if (errors.length) console.error("page errors:\n" + errors.join("\n"));

// ---- encode ----
if (shots.length < 20) { console.error("only " + shots.length + " frames captured"); process.exit(1); }
const list = [];
for (let i = 0; i < shots.length; i++) {
  const d = i + 1 < shots.length ? Math.max(0.001, shots[i + 1].t - shots[i].t) : 0.5;
  list.push(`file '${shots[i].file.replace(/\\/g, "/")}'`, `duration ${d.toFixed(4)}`);
}
list.push(`file '${shots.at(-1).file.replace(/\\/g, "/")}'`);
writeFileSync(join(frames, "list.txt"), list.join("\n"));
const mp4 = join(OUT, "blvkware-kits-demo.mp4");
execFileSync(FFMPEG, ["-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", join(frames, "list.txt"),
  "-vf", "fps=30,scale=1920:1080:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
  "-profile:v", "high", "-movflags", "+faststart", mp4], { stdio: "inherit" });
const total = shots.at(-1).t - shots[0].t + 0.5;
console.log(`${shots.length} frames, ${total.toFixed(1)} s -> ${mp4}`);
rmSync(frames, { recursive: true, force: true });
process.exit(0);
