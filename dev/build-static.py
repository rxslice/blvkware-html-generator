#!/usr/bin/env python3
"""
Build the static, publicly hostable version of the app into docs/.

    python dev/build-static.py

GitHub Pages is static hosting — there is no dev/serve.py to proxy generation.
So the static build ships a browser-side runtime that talks to the provider
directly, using a key the *visitor* supplies and which is stored only in their
own browser (localStorage).

The developer's own keys are never embedded. A key baked into a public page is
scraped and drained within hours.
"""

import datetime
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site", "index.html")
OUT_DIR = os.path.join(ROOT, "docs")            # blvkware.dev/
CUSTOM_DOMAIN = "blvkware.dev"
BUILD_DATE = datetime.date.today().isoformat()

# IndexNow lets us tell Bing (and Yandex, Seznam, Naver) about a change the
# moment it ships, instead of waiting to be crawled. Bing feeds ChatGPT's web
# results, so this is the shortest path from "deployed" to "an assistant can
# cite it". The key is published as a text file at the site root — that file
# IS the proof of ownership, so it must stay deployed.
INDEXNOW_KEY = "444ff8a4e1c76e0935d7c8e40fa40ccd"

# Each tool is a single source file built into its own sub-directory of the
# site. Adding a tool means adding a row here and a card to site/index.html.
TOOLS = [
    {
        "src": "app.html",
        "slug": "sigil",
        "title": "BlvkWare SIGIL — Describe it, watch it get built",
        "desc": ("Write down what you want and watch it become real software — a complete, "
                 "working, single-file application streamed into the page, then run, audited "
                 "and repaired."),
    },
    {
        "src": "augur.html",
        "slug": "augur",
        "title": "BlvkWare AUGUR — Read a company from the outside",
        "desc": ("Point AUGUR at a company's website. It reads the public page, extracts the "
                 "real technical signals, and returns the revenue, operational and competitive "
                 "systems that business should be running but isn't."),
    },
    {
        "src": "scry.html",
        "slug": "scry",
        "title": "BlvkWare SCRY — Find the software hiding in your business",
        "desc": ("Describe how your business works. SCRY maps the operation, finds the "
                 "bottlenecks and missing systems, and turns them into a live operating "
                 "console you can click through."),
    },
]

# Browser-side runtime. Same contract as the platform's ai-text-plugin:
#   root.generateText({instruction, startWith, onChunk}) -> Promise<{text, generatedText}>
#
# Only providers that permit cross-origin browser calls are offered. Anthropic
# is deliberately absent: it blocks browser origins unless you opt into an
# override, and doing that on a public page encourages users to paste a paid
# key into someone else's website.
#
# Same tokenizer rule as app.html: no HTML open-comment sequence and no literal
# script open/close tag anywhere in this JS.
SHIM = r"""
(function () {
  var LS_P = "blvkware.byok.provider", LS_K = "blvkware.byok.key";

  var PROVIDERS = {
    gemini: {
      label: "Google AI Studio (Gemini)",
      url: "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
      model: "gemini-3.5-flash",
      max: 32000,
      get: "https://aistudio.google.com/apikey",
      hint: "starts with AIza"
    },
    openrouter: {
      label: "OpenRouter",
      url: "https://openrouter.ai/api/v1/chat/completions",
      model: "nvidia/nemotron-3-super-120b-a12b:free",
      max: 32000,
      get: "https://openrouter.ai/keys",
      hint: "starts with sk-or-"
    },
    groq: {
      label: "Groq",
      url: "https://api.groq.com/openai/v1/chat/completions",
      model: "llama-3.3-70b-versatile",
      max: 8000,
      get: "https://console.groq.com/keys",
      hint: "starts with gsk_"
    }
  };

  var SYSTEM = "You are a world-class front-end engineer and product designer. " +
    "You output complete, self-contained, single-file HTML documents and nothing else.";

  // A tool that needs a different persona (SCRY asks for JSON, not HTML) sets
  // window.__blvkSystem before calling and clears it afterwards.
  function system() { return window.__blvkSystem || SYSTEM; }

  function creds() {
    try {
      return { p: localStorage.getItem(LS_P) || "gemini", k: localStorage.getItem(LS_K) || "" };
    } catch (e) { return { p: "gemini", k: "" }; }
  }

  function guessProvider(key) {
    if (/^AIza/.test(key)) return "gemini";
    if (/^sk-or-/.test(key)) return "openrouter";
    if (/^gsk_/.test(key)) return "groq";
    return "";
  }

  /* ---------------- key dialog ---------------- */
  function keyDialog() {
    if (document.getElementById("byokBack")) return;
    var c = creds();
    var opts = "";
    for (var id in PROVIDERS) {
      opts += '<option value="' + id + '"' + (id === c.p ? " selected" : "") + '>' +
              PROVIDERS[id].label + "</option>";
    }
    var back = document.createElement("div");
    back.id = "byokBack";
    back.className = "modal-back";
    back.innerHTML =
      '<div class="modal" role="dialog" aria-modal="true" aria-label="Connect an API key" style="width:min(520px,100%)">' +
        '<div class="modal-head">' +
          '<svg class="ic ic-20" style="color:var(--accent-ink)"><use href="#i-cpu"/></svg>' +
          "<h3>Connect a model</h3><div class=\"spacer\"></div>" +
          '<button class="btn ghost sm icon" data-x aria-label="Close"><svg class="ic ic-16"><use href="#i-close"/></svg></button>' +
        "</div>" +
        '<div class="modal-body">' +
          '<p style="margin:0 0 16px;font-size:13px;line-height:1.6;color:var(--ink-2)">' +
            "This is a static site with no server, so generation runs from your browser using your own key. " +
            "It is stored only in this browser and sent only to the provider you pick — never to this site or anyone else." +
          "</p>" +
          '<div class="opt-title">Provider</div>' +
          '<select class="picker" id="byokProv" style="max-width:none;width:100%;height:36px;margin-bottom:14px">' + opts + "</select>" +
          '<div class="opt-title">API key</div>' +
          '<input class="refine-input" id="byokKey" type="password" autocomplete="off" spellcheck="false" ' +
            'placeholder="paste your key" style="width:100%;height:36px;margin-bottom:8px" value="' +
            (c.k ? c.k.replace(/"/g, "&quot;") : "") + '">' +
          '<p id="byokHint" style="margin:0 0 18px;font-size:11.5px;color:var(--ink-3)"></p>' +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
            '<button class="btn primary" id="byokSave"><svg class="ic ic-16"><use href="#i-check"/></svg> Save key</button>' +
            '<a class="btn" id="byokGet" href="#" target="_blank" rel="noopener noreferrer">' +
              '<svg class="ic ic-16"><use href="#i-external"/></svg> Get a free key</a>' +
            '<div class="spacer"></div>' +
            '<button class="btn ghost" id="byokClear">Forget key</button>' +
          "</div>" +
        "</div>" +
      "</div>";
    document.body.appendChild(back);

    var sel = back.querySelector("#byokProv");
    var inp = back.querySelector("#byokKey");
    var hint = back.querySelector("#byokHint");
    var get = back.querySelector("#byokGet");

    function sync() {
      var cfg = PROVIDERS[sel.value];
      hint.textContent = "Free tier, no credit card. Key " + cfg.hint + ". Model: " + cfg.model + ".";
      get.href = cfg.get;
    }
    sync();
    sel.addEventListener("change", sync);

    inp.addEventListener("input", function () {
      var g = guessProvider(inp.value.trim());
      if (g && g !== sel.value) { sel.value = g; sync(); }
    });

    function close() { back.remove(); }
    back.addEventListener("click", function (e) {
      if (e.target === back || e.target.closest("[data-x]")) close();
    });
    back.querySelector("#byokSave").addEventListener("click", function () {
      var k = inp.value.trim();
      if (!k) return;
      try {
        localStorage.setItem(LS_P, sel.value);
        localStorage.setItem(LS_K, k);
      } catch (e) {}
      close();
      if (window.__blvkToast) window.__blvkToast("Key saved — you're ready to generate", "ok");
    });
    back.querySelector("#byokClear").addEventListener("click", function () {
      try { localStorage.removeItem(LS_K); } catch (e) {}
      inp.value = "";
      close();
      if (window.__blvkToast) window.__blvkToast("Key removed from this browser", "info");
    });
    setTimeout(function () { inp.focus(); }, 60);
  }

  window.__blvkKeyDialog = keyDialog;

  /* ---------------- generation ---------------- */
  var CONTINUE = "\n\nYou have already written the beginning of this file. Here it is, " +
    "verbatim, between markers:\n\n<<<PARTIAL_FILE_START>>>\n{P}\n<<<PARTIAL_FILE_END>>>\n\n" +
    "Continue the file from exactly where it stops. Output ONLY the continuation — do not " +
    "repeat any of the text above, do not restart the document, do not explain. Your first " +
    "character must be the character that comes next.";

  window.root = {
    generateText: function (o) {
      var instruction = o.instruction || "";
      var startWith = o.startWith || "";
      var onChunk = o.onChunk;
      var ctrl = new AbortController();
      var generated = "";

      var c = creds();
      if (!c.k) {
        keyDialog();
        var p0 = Promise.reject(new Error(
          "No API key connected. Add a free key to generate — it stays in your browser."));
        p0.stop = function () {};
        return p0;
      }

      var cfg = PROVIDERS[c.p] || PROVIDERS.gemini;
      var content = startWith ? instruction + CONTINUE.replace("{P}", startWith) : instruction;

      var p = fetch(cfg.url, {
        method: "POST",
        headers: { "content-type": "application/json", "authorization": "Bearer " + c.k },
        signal: ctrl.signal,
        body: JSON.stringify({
          model: cfg.model,
          max_tokens: cfg.max,
          stream: true,
          messages: [
            { role: "system", content: system() },
            { role: "user", content: content }
          ]
        })
      }).then(function (res) {
        if (!res.ok) {
          return res.text().then(function (t) {
            var msg = t.slice(0, 300);
            if (res.status === 401 || res.status === 403) {
              keyDialog();
              msg = "That key was rejected by " + cfg.label + ". Check it and try again.";
            } else if (res.status === 429) {
              msg = cfg.label + " rate limit reached. Wait a moment, or connect a different provider.";
            }
            throw new Error(msg);
          });
        }
        var reader = res.body.getReader();
        var dec = new TextDecoder();
        var buf = "";

        function handle(line) {
          line = line.trim();
          if (line.indexOf("data:") !== 0) return;
          var d = line.slice(5).trim();
          if (!d || d === "[DONE]") return;
          var ev;
          try { ev = JSON.parse(d); } catch (e) { return; }
          if (ev.error) throw new Error(ev.error.message || "stream error");
          var ch = ev.choices && ev.choices[0];
          var piece = ch && ch.delta && ch.delta.content;
          if (typeof piece === "string" && piece) {
            generated += piece;
            if (onChunk) onChunk({ fullTextSoFar: startWith + generated, isFromStartWith: false });
          }
        }

        function pump() {
          return reader.read().then(function (r) {
            if (r.done) {
              if (buf.trim()) handle(buf);
              return { text: startWith + generated, generatedText: generated };
            }
            buf += dec.decode(r.value, { stream: true });
            var lines = buf.split("\n");
            buf = lines.pop();
            for (var i = 0; i < lines.length; i++) handle(lines[i]);
            return pump();
          });
        }
        return pump();
      });

      p.stop = function () { try { ctrl.abort(); } catch (e) {} };
      return p;
    }
  };

  /* a way back into the key dialog once a key is set, plus a route home */
  document.addEventListener("DOMContentLoaded", function () {
    var foot = document.querySelector(".rail-foot");
    if (!foot) return;
    var home = document.createElement("a");
    home.className = "btn ghost icon";
    home.href = "/";
    home.setAttribute("data-tip", "BlvkWare home");
    home.setAttribute("aria-label", "Back to BlvkWare");
    home.innerHTML = '<svg class="ic ic-16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="M3.6 10.4 12 3.6l8.4 6.8V20a1.4 1.4 0 0 1-1.4 1.4H5A1.4 1.4 0 0 1 3.6 20Z"/><path d="M9.6 21.4v-7h4.8v7"/></svg>';
    foot.insertBefore(home, foot.querySelector(".spacer"));
    var b = document.createElement("button");
    b.className = "btn ghost icon";
    b.setAttribute("data-tip", "Model / API key");
    b.setAttribute("aria-label", "Model and API key");
    b.innerHTML = '<svg class="ic ic-16"><use href="#i-cpu"/></svg>';
    b.addEventListener("click", keyDialog);
    foot.insertBefore(b, foot.querySelector(".spacer"));
  });
})();
"""


# old path -> current slug. Static hosting has no rewrite rules, so a renamed
# tool keeps its previous address alive with a real page that forwards.
REDIRECTS = [("html-generator", "sigil")]

# Standalone pages copied verbatim to their own directory URL.
MARKETING_PAGES = [("privacy.html", "privacy"), ("terms.html", "terms")]

# Every canonical URL on the site, with a crawl priority.
SITEMAP = [
    ("/", "1.0", "weekly"),
    ("/augur/", "0.9", "monthly"),
    ("/scry/", "0.9", "monthly"),
    ("/sigil/", "0.9", "monthly"),
    ("/privacy/", "0.3", "yearly"),
    ("/terms/", "0.3", "yearly"),
]


def sync_faq_schema(html):
    """Rebuild the FAQPage node from the FAQ a visitor actually reads.

    The structured data and the visible copy have to say the same thing —
    Google treats a mismatch as a markup violation, and an assistant quoting
    stale schema would misrepresent the business. Generating one from the other
    on every build makes drift impossible rather than merely unlikely.
    """
    import json

    pairs = re.findall(
        r'<summary class="faq-q">(.*?)</summary>\s*<div class="faq-a">(.*?)</div>',
        html, re.S)
    if not pairs:
        print("WARNING: no FAQ found in site/index.html - schema left as-is")
        return html

    def plain(fragment):
        text = re.sub(r"<[^>]+>", " ", fragment)
        text = (text.replace("&mdash;", "—").replace("&ndash;", "–")
                    .replace("&amp;", "&").replace("&nbsp;", " ")
                    .replace("&quot;", '"').replace("&#39;", "'"))
        return re.sub(r"\s+", " ", text).strip()

    m = re.search(r'<script type="application/ld\+json">\s*(\{[\s\S]*?\})\s*<' + r'/script>', html)
    if not m:
        print("WARNING: no JSON-LD block found - FAQ schema not synced")
        return html

    data = json.loads(m.group(1))
    for node in data.get("@graph", []):
        if node.get("@type") == "FAQPage":
            node["mainEntity"] = [
                {"@type": "Question", "name": plain(q),
                 "acceptedAnswer": {"@type": "Answer", "text": plain(a)}}
                for q, a in pairs
            ]
            break
    else:
        print("WARNING: no FAQPage node in JSON-LD")
        return html

    blob = json.dumps(data, ensure_ascii=False, indent=2)
    if "</" in blob:
        print("ABORTED: JSON-LD contains a closing tag sequence")
        raise SystemExit(1)
    print("Synced FAQ schema (%d questions) from rendered HTML" % len(pairs))
    return html[:m.start(1)] + blob + html[m.end(1):]


def write_seo_files():
    """robots.txt, sitemap.xml and llms.txt.

    llms.txt is the emerging convention for describing a site to language models
    and agentic search tools in plain markdown, rather than making them infer it
    from rendered HTML. It costs nothing and it is what an AI assistant reads
    when someone asks it to recommend a developer.
    """
    base = "https://" + CUSTOM_DOMAIN

    robots = (
        "User-agent: *\n"
        "Allow: /\n\n"
        "# Assistants and agentic search are welcome here.\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: OAI-SearchBot\nAllow: /\n\n"
        "User-agent: ChatGPT-User\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: Claude-User\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        "User-agent: Applebot-Extended\nAllow: /\n\n"
        "Sitemap: " + base + "/sitemap.xml\n"
    )
    with io.open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as fh:
        fh.write(robots)

    today = BUILD_DATE
    urls = "".join(
        "  <url>\n"
        "    <loc>%s%s</loc>\n"
        "    <lastmod>%s</lastmod>\n"
        "    <changefreq>%s</changefreq>\n"
        "    <priority>%s</priority>\n"
        "  </url>\n" % (base, loc, today, freq, pri)
        for loc, pri, freq in SITEMAP
    )
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + urls + '</urlset>\n')
    with io.open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sitemap)

    llms = """# BlvkWare

> AI automation and custom software for small businesses, built by one engineer.
> Missed-call recovery, AI receptionists and bespoke internal tools, at published
> fixed prices. Also publishes three free browser-based business analysis tools.

BlvkWare is a solo software engineering practice run by William Russell Wheeler,
based in Mississippi and working remotely with small businesses across the United
States — home services, trades, clinics, professional practices and agencies. All
work is delivered remotely; there is nothing requiring an on-site visit.
Contact: russ@blvkware.dev

## Services and prices

- **Missed-Call Recovery** — $499 setup, then $149/month. Every unanswered call
  gets an automatic text back within 60 seconds; two-way texting from the
  business's existing number; automatic follow-up until the customer replies or
  opts out; dashboard of calls recovered. Live in about 1 week. BlvkWare publishes no
  recovery-rate statistic and makes no performance claim: how many calls a business
  recovers depends on its own call volume. The stated arithmetic is that at $149/month
  the service costs less than one average service call in most trades.
- **AI Front Desk** — $1,500 setup, then $349/month. An AI receptionist answering
  calls, texts and web chat 24/7, trained on the business's services, hours and
  pricing, booking appointments directly into the calendar and escalating when it
  should. Live in about 2 weeks.
- **Custom Build** — from $2,500, one-off, no monthly fee. A bespoke internal tool
  or automated workflow: quote follow-up, intake, scheduling, reporting. Scope and
  price agreed in writing before work starts. Delivered in 2-4 weeks. The client
  owns the code outright. 30 days of fixes included.

Monthly services can be cancelled any month. There is no discovery-call
requirement before getting a price.

## How to get in touch

- Book a call directly: https://cal.com/blvkware/30min (30 minutes, for scoping
  custom work) or https://cal.com/blvkware/15min (15 minutes, to get one of the
  productized services started).
- Or email russ@blvkware.dev. Replies come from the person who does the work,
  usually the same day.

## Free tools

All three run entirely in the visitor's browser. No account, no sign-up, no
payment, no server. They exist as the work sample in place of case studies.

- [AUGUR](https://blvkware.dev/augur/): reads a company's public website and
  returns an intelligence report covering revenue opportunities, operational
  weaknesses, competitive positioning and digital infrastructure, then proposes
  costed systems with a technical architecture diagram.
- [SCRY](https://blvkware.dev/scry/): turns a plain-language description of how a
  business operates into a mapped operating model, surfacing bottlenecks,
  automation opportunities and the software systems the business is missing.
- [SIGIL](https://blvkware.dev/sigil/): generates a complete, working, single-file
  web application from a description, streamed live, then runs it, audits its
  quality and repairs its own errors.

## Important caveats for anyone citing this site

- Every dollar figure produced by the free tools is a **projection modelled from
  public industry benchmarks**, never a measurement of a real business's finances.
- BlvkWare has **no published case studies or client references**. This is stated
  openly on the site; the tools are offered as the evidence instead.
- Tool output is AI-generated and is not financial, legal or engineering advice.

## Pages

- [Home](https://blvkware.dev/): services, prices, tools, FAQ
- [Privacy policy](https://blvkware.dev/privacy/): no accounts, no analytics, no
  cookies, no tracking; tools keep data only in the visitor's own browser
- [Terms of service](https://blvkware.dev/terms/)
"""
    with io.open(os.path.join(OUT_DIR, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(llms)

    with io.open(os.path.join(OUT_DIR, INDEXNOW_KEY + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(INDEXNOW_KEY)

    print("Built robots.txt, sitemap.xml (%d urls), llms.txt, IndexNow key file" % len(SITEMAP))


def redirect_page(slug):
    """A redirect that works without a server: header, meta refresh, and script.

    The query string is carried across so SCRY's `?prompt=` hand-off still lands
    if anything is holding the old URL.
    """
    url = "/%s/" % slug
    close_script = "<" + "/script>"
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta http-equiv=\"refresh\" content=\"0; url=" + url + "\">\n"
        "<link rel=\"canonical\" href=\"https://" + CUSTOM_DOMAIN + url + "\">\n"
        "<meta name=\"robots\" content=\"noindex\">\n"
        "<title>Moved to SIGIL</title>\n"
        "<script>location.replace('" + url + "' + location.search + location.hash);"
        + close_script + "\n"
        "</head>\n<body style=\"background:#0a0908;color:#a89d8b;font:15px/1.6 system-ui,sans-serif;"
        "display:grid;place-items:center;height:100vh;margin:0\">\n"
        "<p>The HTML generator is now <a href=\"" + url + "\" style=\"color:#d4f24a\">SIGIL</a>.</p>\n"
        "</body>\n</html>\n"
    )


KEY_RE = re.compile(
    r"(AIza[0-9A-Za-z_\-]{30,}|sk-or-v1-[0-9a-f]{40,}"
    r"|gsk_[0-9A-Za-z]{40,}|sk-ant-[0-9A-Za-z\-]{40,})"
)

def check_js(src, name):
    """Parse the tool's script block before shipping it.

    A single bad escape produces a page that loads, renders, and silently does
    nothing — no visible error, no failed request. That shipped once. If node is
    available this gate makes it impossible to ship again; if it isn't, the build
    says so rather than pretending it checked.
    """
    import subprocess
    import tempfile

    m = re.search(r"<script>\n([\s\S]*)\n<" + r"/script>\s*$", src)
    if not m:
        return True
    path = os.path.join(tempfile.gettempdir(), "_blvk_check.js")
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write(m.group(1))
    try:
        res = subprocess.run(["node", "--check", path],
                             capture_output=True, text=True)
    except (OSError, ValueError):
        print("  note: node not found - JS syntax not verified for %s" % name)
        return True
    if res.returncode != 0:
        first = (res.stderr.strip().splitlines() or ["unknown error"])
        print("ABORTED: %s contains invalid JavaScript" % name)
        for line in first[:6]:
            print("         " + line)
        return False
    return True


def build_tool(tool):
    """Wrap a tool source file in a real HTML document plus the BYOK runtime."""
    src_path = os.path.join(ROOT, tool["src"])
    if not os.path.isfile(src_path):
        print("ERROR: %s not found" % tool["src"])
        return None

    with io.open(src_path, encoding="utf-8") as fh:
        src = fh.read()

    if not check_js(src, tool["src"]):
        return None

    # Refuse to publish if a developer key ever leaked into the source.
    if KEY_RE.search(src):
        print("ABORTED: what looks like a live API key is present in %s." % tool["src"])
        print("         Remove it before building a public bundle.")
        return None

    body = src[src.index("<style>"):]
    close_script = "<" + "/script>"

    head = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>" + tool["title"] + "</title>\n"
        "<meta name=\"description\" content=\"" + tool["desc"] + "\">\n"
        "<meta property=\"og:title\" content=\"" + tool["title"] + "\">\n"
        "<meta property=\"og:description\" content=\"" + tool["desc"] + "\">\n"
        "<meta property=\"og:type\" content=\"website\">\n"
        "<meta property=\"og:image\" content=\"https://" + CUSTOM_DOMAIN + "/assets/og.png\">\n"
        "<meta name=\"twitter:card\" content=\"summary_large_image\">\n"
        # Absolute paths: the tools live one directory down, and the assets are
        # generated from the master logo by dev/embed-logo.py.
        "<link rel=\"icon\" type=\"image/png\" sizes=\"48x48\" href=\"/assets/favicon-48.png\">\n"
        "<link rel=\"apple-touch-icon\" href=\"/assets/logo-192.png\">\n"
        + "<script>" + SHIM + close_script + "\n"
        "</head>\n<body>\n"
    )
    return head + body + "\n</body>\n</html>\n"


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # The logo assets are a build input, not a build product — regenerate them
    # with dev/embed-logo.py whenever the master changes.
    missing = [n for n in ("favicon-48.png", "logo-192.png", "og.png")
               if not os.path.isfile(os.path.join(OUT_DIR, "assets", n))]
    if missing:
        print("ABORTED: docs/assets is missing %s" % ", ".join(missing))
        print("         Run: python dev/embed-logo.py")
        return 1

    for tool in TOOLS:
        page = build_tool(tool)
        if page is None:
            return 1
        out_dir = os.path.join(OUT_DIR, tool["slug"])
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with io.open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        print("Built docs/%s/index.html (%.1f KB)"
              % (tool["slug"], len(page.encode("utf-8")) / 1024.0))

    # /html-generator/ was the tool's address before it was named SIGIL. Links to
    # it are already out in the world, so it stays as a redirect rather than a 404.
    for old, new in REDIRECTS:
        d = os.path.join(OUT_DIR, old)
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(redirect_page(new))
        print("Built docs/%s/index.html  -> /%s/ (redirect)" % (old, new))

    # The marketing site is the root of blvkware.dev; the tools are sub-pages.
    if os.path.isfile(SITE):
        with io.open(SITE, encoding="utf-8") as fh:
            site_html = fh.read()
        site_html = sync_faq_schema(site_html)
        with io.open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(site_html)
        print("Built docs/index.html (%.1f KB)  marketing site"
              % (len(site_html.encode("utf-8")) / 1024.0))
    else:
        print("WARNING: site/index.html missing - root page not built")

    # Standalone marketing pages, each at its own clean directory URL.
    for src, slug in MARKETING_PAGES:
        path = os.path.join(ROOT, "site", src)
        if not os.path.isfile(path):
            print("WARNING: site/%s missing" % src)
            continue
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        d = os.path.join(OUT_DIR, slug)
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        print("Built docs/%s/index.html (%.1f KB)" % (slug, len(html.encode("utf-8")) / 1024.0))

    write_seo_files()

    # Pages would otherwise run the output through Jekyll.
    with io.open(os.path.join(OUT_DIR, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")
    # Custom domain. Kept in the build so a rebuild can never silently drop it —
    # losing this file reverts the site to the github.io URL.
    with io.open(os.path.join(OUT_DIR, "CNAME"), "w", encoding="utf-8") as fh:
        fh.write(CUSTOM_DOMAIN)

    print("  no developer keys embedded - visitors supply their own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
