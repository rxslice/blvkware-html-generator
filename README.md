# The Blvk Lab

Three browser-only tools that read a business, find the software it should have, and build it.

**Live: [blvkware.dev](https://blvkware.dev)** · Built by [BlvkWare](https://blvkware.dev) — bespoke AI agents that do the work, at flat prices. Browse the [agent catalog](https://blvkware.dev/agents/) or [configure and order one](https://blvkware.dev/hire/) without a call.

| | Tool | What it does | Live |
|---|---|---|---|
| **01** | **AUGUR** — *Analyse* | Reads a company's live public website and reports the revenue and automation systems it should be running but isn't | [blvkware.dev/augur](https://blvkware.dev/augur/) |
| **02** | **SCRY** — *Architect* | Maps how a business actually operates, finds the missing systems, and turns them into a clickable operating console | [blvkware.dev/scry](https://blvkware.dev/scry/) |
| **03** | **SIGIL** — *Build* | Streams a complete, working, single-file application into the page — then runs it, reads its own console, and repairs what it broke | [blvkware.dev/sigil](https://blvkware.dev/sigil/) |

No sign-up, no account, no server. Each tool is one HTML file that runs entirely in your browser using an API key you supply, stored only in your own `localStorage`.

---

## Why these exist

They are the portfolio. Rather than a logo wall and case studies nobody can verify, the argument is: here is working software, go use it right now, judge the standard for yourself.

They also happen to be the sales pipeline in order. AUGUR finds the problem, SCRY designs the fix, SIGIL builds it. Which is the same sequence used on a paying client.

---

## Architecture

Each tool is a **single, self-contained HTML file** — markup, styles, and logic in one document, no build step, no framework, no dependencies. Open the file and it works.

```
app.html      → SIGIL   (156 KB)
augur.html    → AUGUR   (113 KB)
scry.html     → SCRY    (61 KB)
site/         → the marketing site source
dev/          → build and asset tooling
docs/         → the built, published site (GitHub Pages serves this)
```

`dev/build-static.py` compiles the sources into `docs/`: injecting per-page metadata, canonicals and structured data, generating `sitemap.xml`, `robots.txt`, `llms.txt` and the IndexNow key, and wrapping each tool with a browser-side model runtime.

### Bring-your-own-key runtime

GitHub Pages is static hosting — there is no server to proxy generation through. So the build injects a shim implementing the same contract the tools were written against:

```js
root.generateText({ instruction, startWith, onChunk }) → Promise<{ text, generatedText }>
```

…but pointed at whichever provider the *visitor* has a key for. The key lives in their `localStorage` and is sent only to that provider.

**No developer key is ever embedded.** A key baked into a public page is scraped and drained within hours; the build refuses to emit one.

Only providers that permit cross-origin browser calls are offered. Anthropic is deliberately absent — it blocks browser origins unless you opt into an override, and encouraging users to paste a paid key into someone else's website is not a pattern worth shipping.

---

## Technical decisions worth explaining

**Single-file, no framework.** These tools have to be readable and runnable by anyone who opens the file, including a prospective client who wants to check what it does before running it. A build step and a `node_modules` tree would defeat that.

**AUGUR reads pages through a CORS relay chain.** Browsers cannot fetch arbitrary origins. AUGUR tries relays in order and falls back to a readability service, so a site that blocks one path is still readable. It crawls several pages, not just the homepage — the difference is not cosmetic: on one test site the homepage alone surfaced *0 prices*, while five pages surfaced *3*, moving the evidence from banner copy to the actual pricing model and cancellation policy.

**AUGUR's copy budget is explicit.** Page text is truncated against a token budget, and any trimmed page is reported in the scan log rather than silently dropped. A report that quietly analysed less than it claimed would be worse than no report.

**Shareable reports live in the URL fragment.** A report is gzipped and base64url-encoded into `#r=…`. Fragments are never transmitted to a server, which is what makes the published privacy policy literally true — there is no backend that *could* retain a report. The alternative (a Worker plus KV) would have been easier and would have made the privacy claim false.

**SIGIL audits and repairs its own output.** It runs what it generated, reads the runtime console, and feeds its own errors back for repair. Generating code that looks plausible is easy; noticing it threw on load is the part that matters.

**A tokenizer trap the hard way.** A literal `<!--` or `<script>`/`</script>` sequence inside an inline script silently breaks HTML parsing — the page loads and does nothing, with no error. Every generated script block splits those sequences (`"<" + "/script>"`). This cost real debugging time before it was understood.

**`node --check` gates every build.** A syntax error I introduced once shipped a page that loaded fine and did nothing at all. The build now refuses to emit any tool whose JavaScript does not parse, so that failure mode cannot recur.

**FAQ structured data is regenerated from the rendered HTML on every build.** Hand-maintained JSON-LD drifts from the visible page the first time someone edits the copy and forgets the schema — which is exactly what happened here. It is now derived, not maintained.

**The logo is resampled in linear light.** The mark is thin brass linework on black. Averaging those strokes in sRGB space crushes them toward black, and below ~48px the emblem turns into a dark smudge. Converting to linear, resampling, then converting back preserves their true luminance. The difference at favicon size is dramatic. `dev/embed-logo.py` derives every size from one master.

---

## Running locally

Open any of `app.html`, `augur.html`, or `scry.html` directly in a browser. That is the whole setup — they will prompt for an API key.

For a real streaming harness against a live provider (no mocks anywhere in this project):

```bash
python dev/serve.py      # http://localhost:8777
```

It auto-detects whichever key you have, preferring free ones:

| Provider | Free tier | Env var |
|---|---|---|
| Google AI Studio | yes, no card | `GEMINI_API_KEY` |
| OpenRouter | yes, no card | `OPENROUTER_API_KEY` |
| Groq | yes | `GROQ_API_KEY` |
| Cerebras | yes | `CEREBRAS_API_KEY` |
| Anthropic | no | `ANTHROPIC_API_KEY` |

Get a free Google key at <https://aistudio.google.com/apikey> (no credit card). Put it in a `.env`, or export it.

To build the published site:

```bash
python dev/build-static.py     # → docs/
python dev/embed-logo.py       # regenerate logo assets from the master
```

Stdlib only for the server; the logo tooling needs Pillow and numpy.

---

## Limitations

Worth stating plainly, since the point of publishing these is that you can check them.

- **Output quality tracks the model behind the key.** A free-tier model produces free-tier results. This is the largest single variable and it is not under the tool's control.
- **AUGUR can only read what is public and server-rendered.** A site that renders entirely client-side, or that blocks every relay, will yield a thin report. It says so rather than inventing findings.
- **SCRY's operating console is projected, not connected.** It models what your systems *would* show, from what you describe. It has no access to your real data and does not pretend otherwise.
- **SIGIL builds single-file front-ends.** No backend, no database, no auth. It is a fast way to get to a working artefact, not a replacement for building a product.
- **Everything is browser-side**, so anything a browser cannot do, these cannot do.

---

## Roadmap

- Screenshots and a recorded walkthrough in this README
- Per-tool documentation pages with worked examples
- A changelog, once the tools stabilise enough to have one
- AUGUR: aggregate scanning, to publish findings across a whole industry rather than one company at a time

---

## Author

Built and maintained by **W. Russell Wheeler** — [blvkware.dev](https://blvkware.dev) · <russ@blvkware.dev> · Mississippi, serving the United States remotely.

BlvkWare builds AI automation and custom software for small businesses: automated quote follow-up, review requests, business process automation, and the internal tools you keep meaning to build. Fixed prices, published on the site.

If you want the underlying business process found and turned into software rather than doing it yourself, that is the actual service — [see what it costs](https://blvkware.dev/#services).
