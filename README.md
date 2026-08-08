# BlvkWare AI HTML Generator

Describe a website, game, tool or app in plain language — get a complete, working, single-file HTML page back, streamed live.

`app.html` is the deliverable. It keeps the original platform contract exactly:

```
$meta
  title = ...
  description = ...
  tags = ...

generateText = {import:ai-text-plugin}
```

…followed by the markup, calling `root.generateText({ instruction, startWith, onChunk })` the same way the starting version did. Paste it in as-is.

---

## Running it locally against a real model

`dev/serve.py` is a real harness — it streams from a live provider. There is no mock anywhere in this project.

```bash
python dev/serve.py
```

Then open <http://localhost:8777>. The server strips the `$meta` header, injects a genuine `root.generateText` implementation, and proxies generation with `stream: true`. Stdlib only — nothing to install.

### It runs on a free API key

The server is multi-provider and auto-detects whichever key you have, preferring free ones:

| Provider | Free | Default model | Env var |
|---|---|---|---|
| **Google AI Studio** | yes, no card | `gemini-3.5-flash` | `GEMINI_API_KEY` |
| OpenRouter | yes, no card | `nvidia/nemotron-3-super-120b-a12b:free` | `OPENROUTER_API_KEY` |
| Groq | yes | `llama-3.3-70b-versatile` | `GROQ_API_KEY` |
| Cerebras | yes | `llama-3.3-70b` | `CEREBRAS_API_KEY` |
| Mistral | yes (opts into training) | `mistral-large-latest` | `MISTRAL_API_KEY` |
| Anthropic | no | `claude-opus-5` | `ANTHROPIC_API_KEY` |

Get a free Google key at <https://aistudio.google.com/apikey> (no credit card). Put it in a `.env` next to `app.html` — see `.env.example` — or export it.

```bash
python dev/serve.py --list                                  # all providers
python dev/serve.py --provider openrouter --model cohere/north-mini-code:free
python dev/serve.py --max-tokens 8000
```

A **provider picker** appears in the composer whenever the host exposes `/api/providers` (the dev server does; the plugin platform doesn't, so it stays hidden there). Leave it on *Auto* for retry + failover, or pin one provider for a run — the choice persists. After each build the subtitle names the model that actually served it, which matters once failover can silently move you.

**Free tiers rate-limit, so the server is built for it.** Each request retries with exponential backoff on 429/5xx, then fails over to your next available provider — but only while nothing has been streamed yet, so a partial page on screen is never yanked out from under you. The UI shows which provider actually served the run.

**Verified working**: Gemini free tier produced a complete 46.5 KB / 1,430-line pomodoro app in 52.9s — audit score 100, zero runtime errors, working timer, self-contained. Failover verified by forcing a bad model: Gemini failed, OpenRouter served it, the user saw a note rather than an error.

Two wire formats are implemented — `openai` (covers Gemini, OpenRouter, Groq, Cerebras, Mistral) and `anthropic`. Adding a provider is one entry in `PROVIDERS`.

GitHub Models is **retired** (`410 github_models_retirement_brownout` as of Aug 2026) and is never auto-selected.

### Two constraints worth knowing

**Assistant prefill is unsupported on several current models** — Claude Opus 5 returns a 400 for a trailing assistant turn. The platform's `startWith` parameter is prefill-shaped, so the server never passes it through as one. Continuations hand the partial file back inside the **user** turn between explicit markers. That's `CONTINUE_TEMPLATE`.

**Some providers sit behind a WAF that rejects urllib's default user-agent** — Groq answers Cloudflare `1010`. Every request sends a real `User-Agent`.

---

## What it does

**Generate**
- Six form factors (Auto / Game / Site / App / Landing / Visual), each with a tailored instruction block
- Nine aesthetic presets plus an accent-colour picker
- Seven build rules that rewrite the prompt: animations, responsive, accessible, forced dark UI, CDN libraries, commented code, live preview
- Auto-continuation — if the model runs out of room mid-file it reseeds and keeps going (up to 6 passes) instead of handing you a truncated page

**Watch it build**
- Code streams in with live syntax highlighting and line numbers
- Switch to Preview mid-run and it mounts live, throttled, so you watch the page assemble itself — but only while that tab is actually open, since re-parsing a growing document nobody is looking at is pure waste
- Live KB counter and elapsed timer

**Verify — two independent checks**
- A **runtime console** captures `log` / `warn` / `error` / unhandled rejections from inside the sandboxed preview, with filters — the generated page's actual errors, not just its markup
- An **audit** statically inspects the file for what the console can't see: truncated documents, unbalanced tags, missing doctype/charset/viewport/title/lang, buttons wired to nothing, unlabelled inputs, images without alt, missing focus styles, absent media queries, ungated motion, leftover `TODO`/Lorem ipsum, and external resources when you asked for self-contained. Scored 0–100 with severity-ranked findings.

**Fix and iterate**
- **Repair with AI** — feeds captured runtime errors back to the model
- **Fix with AI** — feeds the audit findings back as a repair brief (informational notes are left alone)
- **Refine** — "add a scoreboard", "make it feel more premium"; each pass returns a full updated file
- **Version chips** (v1, v2, v3…) label every pass and restore instantly

The two checks are complementary: a page can run without throwing and still be inaccessible, truncated, or full of dead buttons.

**Ship**
- Download, copy, or open in a new tab
- Viewport switcher: full width / tablet 834px / mobile 390px, with browser chrome around the framed preview
- Library of your last 14 builds in `localStorage` — nothing leaves the browser

---

## Support screen

A donation screen appears on load: a custom gear-motif header, the brand mark, a short pitch, your PayPal QR on a white panel (QR codes need a light background and quiet zone to scan reliably), and an optional **Open PayPal** button.

It's dismissible, has a **Don't show this again** opt-out persisted in `localStorage`, and stays reachable afterwards from the heart icon in the sidebar footer. Escape, the backdrop and the close button all dismiss it; focus is trapped while it's open and restored on close.

**Adding your QR:**

```bash
# 1. save your PayPal QR image here
assets/paypal-qr.png

# 2. embed it
python dev/embed-qr.py --paypal https://paypal.me/yourhandle
```

Your image is embedded **verbatim** as a data URI — never decoded, never re-encoded, so the payment destination cannot be altered by the tooling. The only processing is an optional nearest-neighbour downscale if the source is over 512px (nearest, because smooth filters blur module edges and cost you scans). Until you run it, the panel shows a labelled placeholder rather than a fake code.

---

## Keyboard

| | |
|---|---|
| `Ctrl K` | Focus the prompt |
| `Ctrl ⏎` | Generate |
| `Esc` | Stop / close overlay / exit focus mode |
| `Ctrl 1–4` | Preview / Code / Console / Audit |
| `Ctrl S` | Download |
| `Ctrl Shift C` | Copy code |
| `Ctrl R` | Reload preview |
| `Ctrl O` | Toggle options |
| `Ctrl .` | Focus mode |
| `?` | Shortcuts |

---

## The instruction prompt is the product

`buildInstruction()` in `app.html` is the single biggest lever on output quality, and it is written to fight the two default failure modes of every model on this task:

1. **Generic "AI slop" design.** Models converge hard on a recognisable default look, so the prompt explicitly bans it — overused font stacks, purple/indigo gradients, predictable card-grid-hero layouts, components with no point of view — and demands one signature detail the user didn't ask for.
2. **Skeletons that look finished but do nothing.** It requires every control wired to real behaviour, real seeded content instead of Lorem ipsum, and the unhappy paths handled.

It closes with a short self-check (every control does something, no undefined references, layout holds at 360px, document complete through `</html>`), which measurably reduces dead controls and truncated files.

Edit that function, not the UI, when you want different output.

## Design notes

**Palette — "Carbon & Acid."** Warm near-black (`#0a0908`, not blue-black), bone ink, and acid chartreuse (`#d4f24a`) as the primary, with clay and jade secondaries. Primary buttons are an acid fill with *dark* ink rather than white-on-gradient. The light theme is warm parchment (`#f2efe6`) with a darkened olive (`#5c7407`) for accent-coloured text, so contrast holds while the brand fill stays identical across themes.

**Layout.** A fixed-height app shell — nothing scrolls but the panes that should. After the first build the composer collapses to a single line (prompt + Edit + Rebuild) and the workspace takes the entire remaining viewport, so you're never scrolling past the input to see your output.

**Icons.** No emoji anywhere. Every glyph is a hand-authored SVG symbol on a 24px grid at 1.65 stroke weight, defined once in a sprite and referenced with `<use>`.

**Brand mark.** `#i-blvkmark` is the BlvkWare artificer as vector art on a 64px grid — pointed wide-brim hat, brass-studded band, crown cog, goggles, and a coat with a shoulder cog. It's a bust rather than a face: a floating head reads as a cartoon mascot at small sizes, whereas the hat-and-shoulders silhouette stays legible down to ~24px. Full colour by design (it's a logo, not a `currentColor` UI icon), on a dark tile so it reads as it does on its own black field. The favicon is derived from the same symbol at serve time, so the tab icon can't drift from the rail.

Self-contained: no external fonts, stylesheets, scripts or images. `prefers-reduced-motion` respected, `:focus-visible` rings throughout, tabs carry `role`/`aria-selected`, status changes announced via an `aria-live` region.

---

## Three things worth knowing if you edit `app.html`

**1. Never write an HTML open-comment or a script open/close tag literally inside the main `<script>` block.**

This is not style advice — it silently destroys the file. An open-comment sequence puts the HTML tokenizer into *script data escaped* state; a following script open tag escalates to *double escaped*, where the real closing tag stops terminating the element and the rest of the document is swallowed as script text. The app simply never boots, with no console error.

The code works around this in three places (the highlighter regex, the comment-detection compare, and the console probe builder) — see the note above `highlight()`. Keep it that way. The same rule applies to the injected shim in `dev/serve.py`.

**2. `<html>` needs `overflow: hidden`, not just `<body>`.**

The out-of-flow toast and live-region nodes leave trailing whitespace that forms an anonymous line box after `#app`. Without it on the root element the whole document scrolls by a stray line-height even though the body can't.

**3. Runs are tagged with a token.**

A stopped generation's promise still settles afterwards. Without the token guard, a stale run's `finally` would clear the busy state and stream buffer of a *newer* run started right after a stop. `runToken` / `stale()` prevent that.
