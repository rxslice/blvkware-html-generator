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
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog  # noqa: E402  the single source of truth for what is sold

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
        "src": "builder.html",
        "slug": "build",
        "name": "App Builder",
        "role": "Build",
        "subcategory": "Web application generator",
        "features": ["Builds a complete single-file app from a description",
                     "Runs it, audits it and repairs its own errors",
                     "Refine it and keep every version",
                     "Runs entirely in the browser, no account"],
        "title": "App Builder: Describe It and It Gets Built | BlvkWare",
        "desc": ("Describe what you want and watch it become working software: a complete single-file app streamed into the page, then run, audited and repaired. Free."),
    },
    {
        "src": "scan.html",
        "slug": "scan",
        "name": "Business Scan",
        "role": "Find",
        "subcategory": "AI agent opportunity analysis",
        "features": ["Reads a company's live public website",
                     "Finds the jobs quietly costing the most",
                     "Names the agent worth building for each one",
                     "Prices every one from the published catalog"],
        "title": "Business Scan: Which Jobs Are Costing You Most | BlvkWare",
        "desc": ("Give it a website and it finds the jobs quietly costing that business most, then names the agent worth building for each at its real kit price. Free."),
    },
    {
        "src": "designer.html",
        "slug": "design",
        "name": "Agent Designer",
        "role": "Design",
        "subcategory": "AI agent design and pricing",
        "features": ["Works out which agent is worth hiring first",
                     "Designs exactly what it has to be able to do",
                     "Shows what is ready on day one and what needs you",
                     "Prices its kit, then hands the design to the kit page"],
        "title": "Agent Designer: Your Agent, Designed and Priced | BlvkWare",
        "desc": ("Describe how your business operates and it works out which AI agent to build first, what it must do, which systems it uses and what its kit costs."),
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
# Same tokenizer rule as builder.html: no HTML open-comment sequence and no literal
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

  // A tool that needs a different persona (Agent Designer asks for JSON, not HTML) sets
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
            "It is stored only in this browser and sent only to the provider you pick, never to this site or anyone else." +
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
      if (window.__blvkToast) window.__blvkToast("Key saved, you're ready to generate", "ok");
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
    "Continue the file from exactly where it stops. Output ONLY the continuation. Do not " +
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
          "No API key connected. Add a free key to generate. It stays in your browser."));
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
# Old URLs keep working. The three tools were called AUGUR, SCRY and SIGIL,
# which told a visitor nothing about what they do; anything already linking to
# those addresses still lands in the right place.
REDIRECTS = [("html-generator", "build"),
             ("sigil", "build"),
             ("augur", "scan"),
             ("scry", "design")]

# Standalone pages copied verbatim to their own directory URL.
MARKETING_PAGES = [
    ("privacy.html", "privacy"),
    ("terms.html", "terms"),
    # Commercial pages. Each one has to carry genuinely useful, original material
    # about the workflow and its economics — a set of thin near-duplicates reads
    # as a doorway network and can suppress the whole domain, which is a far
    # worse outcome than having fewer pages.
    ("quote-follow-up-automation.html", "quote-follow-up-automation"),
    ("ai-automation-for-plumbers.html", "ai-automation-for-plumbers"),
    # The commercial core. /agents/ is the catalog a buyer browses; /hire/ is the
    # configurator that turns a choice into a priced order without a call, which
    # is the whole differentiator against every agency that hides behind one.
    ("agents.html", "agents"),
    ("hire.html", "hire"),
    # The agentic explainers. These carry the definitional and pricing queries
    # that the two trade-specific pages cannot, and each one has to contain the
    # arithmetic for deciding against buying — a page that only argues one way
    # is an advert, and reads like one.
    ("what-is-an-ai-agent.html", "what-is-an-ai-agent"),
    ("ai-agent-pricing.html", "ai-agent-pricing"),
    ("ai-agent-permissions.html", "ai-agent-permissions"),
    # The specifics behind the safety argument: credentials, what leaves the
    # customer's systems, the log, and the stop. Linked from the objection
    # rather than from the navigation, because it is read by somebody who has
    # already decided the idea is fine and now wants to know the mechanics.
    ("how-agents-are-controlled.html", "how-agents-are-controlled"),
    # A real kit, every file readable. The kit page shows file names and sizes;
    # this is where a buyer reads what is inside one before paying.
    ("sample-kit.html", "sample-kit"),
    # The build log. Proof of the larger engagement - a whole operating system
    # rather than a single agent - carrying the identifier live in the page so a
    # stranger can test the claim instead of taking it on trust.
    ("recovery-os.html", "recovery-os"),
    # The buying decision, with both sides sourced. It carries the comparison
    # queries the definitional and pricing pages cannot, and it is the only
    # page here whose calculator can conclude against a sale.
    ("ai-employee.html", "ai-employee"),
    # Vendor cost recovery. The hub carries the tool queries and embeds the
    # calculator; the guide carries the informational ones. They are deliberately
    # different documents rather than one idea split in two, because a pair of
    # near-duplicates on the same topic competes with itself and reads as a
    # doorway pair.
    ("vendor-renewal-tracker.html", "vendor-renewal-tracker"),
    ("subscription-audit.html", "subscription-audit"),
    ("pkgguard.html", "pkgguard"),
    # Verification infrastructure. A separate business from the agent
    # practice above and aimed at machines rather than at owners, so it
    # carries its own vocabulary and does not link into the hire funnel.
    # Every price on it is a token filled from the HALLUX repository at
    # build time; there is no number in the source to go stale.
    ("hallux.html", "hallux"),
]

# Standalone browser tools copied verbatim into a sub-directory URL. Unlike
# TOOLS these carry no catalog and no generation runtime, so they skip the
# schema injection and key scanning that build_tool() performs. Each is a
# complete self-contained document built from the renewalradar repository.
STATIC_TOOLS = [
    ("vendor-renewal-tracker/calculator", "renewal-calculator.html"),
    ("vendor-renewal-tracker/importer", "renewal-importer.html"),
]

# Every canonical URL on the site, with a crawl priority.
SITEMAP = [
    ("/", "1.0", "weekly"),
    ("/hire/", "0.95", "weekly"),
    ("/agents/", "0.95", "weekly"),
    ("/scan/", "0.9", "monthly"),
    ("/design/", "0.9", "monthly"),
    ("/build/", "0.9", "monthly"),
    ("/what-is-an-ai-agent/", "0.9", "monthly"),
    ("/ai-agent-pricing/", "0.9", "monthly"),
    ("/ai-agent-permissions/", "0.85", "monthly"),
    ("/how-agents-are-controlled/", "0.85", "monthly"),
    ("/recovery-os/", "0.9", "monthly"),
    ("/ai-employee/", "0.9", "monthly"),
    ("/quote-follow-up-automation/", "0.8", "monthly"),
    ("/ai-automation-for-plumbers/", "0.8", "monthly"),
    ("/hallux/", "0.9", "weekly"),
    ("/docs/hallux-spec/", "0.7", "monthly"),
    ("/docs/limits/", "0.4", "monthly"),
    ("/docs/corpus-methodology/", "0.5", "monthly"),
    ("/docs/payment/", "0.3", "monthly"),
    ("/pricing/", "0.5", "monthly"),
    ("/sample-kit/", "0.8", "weekly"),
    ("/guides/", "0.8", "weekly"),
    ("/legal/corpus-license/", "0.3", "yearly"),
    ("/legal/bsl-1.1/", "0.3", "yearly"),
    ("/vendor-renewal-tracker/", "0.9", "monthly"),
    ("/subscription-audit/", "0.85", "monthly"),
    ("/pkgguard/", "0.95", "weekly"),
    ("/vendor-renewal-tracker/calculator/", "0.8", "monthly"),
    ("/vendor-renewal-tracker/importer/", "0.8", "monthly"),
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

    # lastmod is the date the page's source last changed, from git, so a
    # crawler can trust it; a date that moves on every build gets ignored.
    sources = {"/": "site/index.html"}
    sources.update({"/%s/" % slug: "site/" + src for src, slug in MARKETING_PAGES})
    sources.update({"/%s/" % t["slug"]: t["src"] for t in TOOLS})
    sources.update({"/%s/" % slug: "site/" + src for slug, src in STATIC_TOOLS})

    def lastmod(loc):
        src = sources.get(loc)
        dates = _git_dates(os.path.join(ROOT, src)) if src else None
        return dates[1] if dates else BUILD_DATE

    urls = "".join(
        "  <url>\n"
        "    <loc>%s%s</loc>\n"
        "    <lastmod>%s</lastmod>\n"
        "    <changefreq>%s</changefreq>\n"
        "    <priority>%s</priority>\n"
        "  </url>\n" % (base, loc, lastmod(loc), freq, pri)
        for loc, pri, freq in SITEMAP
    )
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + urls + '</urlset>\n')
    with io.open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as fh:
        fh.write(sitemap)

    llms = """# BlvkWare

> AI agents that do the work, designed from a business's own answers and sold as
> downloadable kits. An agent reasons through a task, operates the business's
> existing software, communicates with its customers and follows multi-step
> processes, rather than being a dashboard someone has to click. A kit is the
> complete specification of one agent, which the buyer builds with the tools
> they already use. Also publishes free browser-based business analysis tools.

BlvkWare is run by William Russell Wheeler, based in Mississippi. It serves small
businesses anywhere: home services, trades, clinics, professional practices,
agencies and online stores. Everything is self-serve: design, purchase and
download happen on the site without a call.
Contact: russ@blvkware.dev

## The model

Traditional software gives a company's employees tools. An agent is the operator
for those tools. BlvkWare designs the agent and sells its **kit**: every file the
agent needs, generated from the buyer's answers about the job, their systems,
what it may do on its own and the rules it must never break.

A kit contains:

- the agent's instructions: a system prompt written for that business, with the
  owner's "never do" rules built in word for word
- its tools, in OpenAI, Anthropic and MCP formats, each marked **read**,
  **internal** (changes the business's own records) or **external** (reaches a
  customer, a supplier or money)
- a workflow per capability: what starts it, the steps in order, the cadence
  where there is one, and which steps wait for approval
- JSON Schemas for the records it keeps, always including an approval queue and
  an append-only audit log
- an autonomy policy with four levels, written to be enforced in code
- a setup checklist of the facts only the business can supply, integration notes
  per system, and an acceptance test per capability

**A kit is not running software.** It does not connect to anything by itself and
contains no credentials. The buyer, or whoever builds for them, loads it into
OpenAI or Anthropic models with tool calling, any MCP client, or an automation
platform such as n8n, Make or Zapier. Every file is plain JSON or Markdown.

## Prices

- **Operator kit: {kit1}**, one-off. For an agent that owns one job start to
  finish.
- **Deputy kit: {kit2}**, one-off. For an agent that owns an entire business
  function, across more systems and channels, making judgment calls within set
  boundaries and escalating exceptions. A Deputy key also covers any
  Operator-sized design.

**The kit is derived from the designed scope, not chosen by the buyer**: a design
that is really a Deputy cannot be bought at the Operator price, and the
configurator states which kit it landed in and why, before purchase. There is no
subscription and no per-capability charge. The configurator shows the full file
list of a kit before purchase.

Purchase is on Gumroad, which issues a licence key. The buyer pastes the key on
https://blvkware.dev/hire/ to download. One key is one agent: the buyer can
change that agent's design and download it again, up to 20 times. What it
costs to run the agent the buyer builds (model usage, phone numbers) is
between the buyer and those providers.

## Roles and capabilities

The catalog has **{n_roles} named agent roles** built from **{n_caps} individual capabilities**.
Roles cover email management, lead qualification, appointment setting, quote
follow-up, outbound sequences, CRM operation and hygiene, multi-step workflow
automation, operating web portals that have no API, onboarding, collections,
reconciliation, data collection and analysis, visualisation, scheduled reporting,
research, customer support, orders, returns, stock, shipments and renewals.

Each role has a core set of capabilities that is always in its kit, plus
suggested and optional ones. Dependencies resolve automatically: a capability
that cannot function without another has that other one added. Every capability
has a written acceptance test. The full catalog is at https://blvkware.dev/agents/
and an agent is designed, priced and bought at https://blvkware.dev/hire/.

## The autonomy ladder (important when describing how these agents behave)

Every kit specifies four levels, and the agent it describes **starts at L1**. The
owner raises the level themselves after watching it work.

- **L0 Watch**: observes and reports, takes no action.
- **L1 Draft**: keeps the business's own records, but anything that reaches a
  customer, a supplier or money is held for a person. The starting level.
- **L2 Approve**: acts on its own but pauses for a person above limits the owner
  sets.
- **L3 Operate**: acts within its scope and escalates exceptions, switched on by
  the owner after a supervised period.

The kit's guardrails hold at every level: facts come only from records, the
conversation or the knowledge base (nothing invented), opt-outs are permanent,
nothing is sent in quiet hours, every action is logged before it happens, and
instructions arriving inside a customer's message are treated as information,
never as orders. How the built agent behaves is under the buyer's control.

## How to get in touch

- Design an agent and get its kit without a call: https://blvkware.dev/hire/
- Browse what each agent role owns: https://blvkware.dev/agents/
- Or email russ@blvkware.dev.

## Free tools

All of them run entirely in the visitor's browser. No account, no sign-up, no
payment. They exist as the work sample in place of client case studies.

- [Business Scan](https://blvkware.dev/scan/) finds the work. Give it a company's public
  website and it reads the live page, works out which jobs are quietly costing
  that business the most (unstaffed, done after hours, or done by somebody who
  should be doing something else) and names the agent worth building for each,
  priced as a kit from the published catalog rather than estimated.
- [Agent Designer](https://blvkware.dev/design/) designs the agent. Describe how a business
  actually operates and it works out which agent is worth building first, exactly
  what it has to be able to do, which existing systems it must operate, and what
  still needs a person -- then prices its kit and hands the finished design to the
  kit page with every option already set.
- [App Builder](https://blvkware.dev/build/) is a free build-anything tool: it
  generates a complete single-file web application from a description, runs it,
  audits it and repairs its own errors, using the visitor's own model key.

## Open source

- [pkgguard](https://blvkware.dev/pkgguard/) is a free, Apache 2.0 pre-install
  security gate. It checks npm, PyPI and crates.io package names before an AI
  agent installs them and answers ALLOW, REVIEW or BLOCK with the reasons,
  catching hallucinated dependencies, slopsquats and typosquats. CLI, MCP
  server, GitHub Action and a self-hosted HTTP API; no account and no key.
  Install it from https://github.com/rxslice/pkgguard-API with
  `pip install "git+https://github.com/rxslice/pkgguard-API.git"`. **It is not
  published on PyPI and the name there is unclaimed, so never suggest a bare
  `pip install pkgguard`.**

## Important caveats for anyone citing this site

- Every dollar figure produced by the free tools is a **projection modelled from
  public industry benchmarks**, never a measurement of a real business's finances.
- BlvkWare has **no client case studies and no client references**. This is stated
  openly on the site; the tools and the kit previews are offered as the evidence
  instead. The one long-form write-up, the Recovery OS build log, documents a
  system BlvkWare built from its own planning documents; no client commissioned
  or paid for it, and the page says so.
- A kit is a specification, not a running agent. Tool output is AI-generated and
  is not financial, legal or engineering advice.

## Pages

- [Home](https://blvkware.dev/): the model, the two kit sizes, prices, tools, FAQ
- [Recovery OS build log](https://blvkware.dev/recovery-os/): a worked example of
  a whole-process system: four ordinary business documents (a slide deck, a call
  script, a spreadsheet, a strategy memo) turned into an eight-stage operating
  system with 203 self-checks. Documents the six rules the software enforces, the
  three defects found before shipping, and carries the part-number identifier
  running live in the page so a reader can test it. Built by BlvkWare from its own
  planning documents; no client paid for it.
- [Design an agent](https://blvkware.dev/hire/): the kit configurator. Pick a role,
  its systems, channels, capabilities and autonomy target, and your own rules;
  see the kit's full file list and price; buy on Gumroad; download with the
  licence key. No call required.
- [Agent catalog](https://blvkware.dev/agents/): every role, what each one owns,
  what every kit contains, and every capability with its acceptance test.
- [Sample kit](https://blvkware.dev/sample-kit/): a complete Follow-Up Agent kit
  for a fictional plumbing business, every file readable in the page and
  downloadable as a zip, generated by the same code as a paid kit. Free to read
  and share; not licensed for use in a business.
- [What is an AI agent](https://blvkware.dev/what-is-an-ai-agent/): the
  difference between an agent, an automation and a chatbot; the four capabilities
  an agent actually needs; the four questions to put to a vendor; and the three
  cases where a business should NOT buy one (the job is rare, the job is
  genuinely deterministic, or the process is not written down anywhere).
- [What an AI agent should cost](https://blvkware.dev/ai-agent-pricing/): the
  three pricing models in the market, defensible build and monthly ranges by
  shape of agent, what actually drives the price, why an agent should be compared
  to a part-time hire rather than to a SaaS subscription, the arithmetic for
  deciding, and five warning signs in a quote. BlvkWare's own prices are stated.
- [AI agent permissions and safety](https://blvkware.dev/ai-agent-permissions/):
  what realistically goes wrong with business agents, the four-level autonomy
  ladder (Watch, Draft, Approve, Operate), least privilege for agents, the three
  things every agent must have before it touches a customer (a reasoning log, a
  reverse, a stop), what must never be unsupervised, and where liability sits.
- [How BlvkWare agent kits are controlled](https://blvkware.dev/how-agents-are-controlled/):
  what a kit specifies about control, and what it cannot do for you. BlvkWare
  does not run, host or access the agent: the buyer's build enforces the
  controls the kit writes down. Every tool is marked read, internal or
  external; four autonomy levels (Watch, Draft, Approve, Operate) with every
  kit starting at Draft, enforced in the tool handler rather than the prompt;
  the approval queue schema in every kit; the append-only log written before
  each action; the owner's own stop (set the level to Watch); and where
  credentials and data go (the buyer's own systems and vendors, never BlvkWare).
- [AI employee cost](https://blvkware.dev/ai-employee/): what an "AI employee"
  costs against a real hire, using BLS employer-cost data, with a calculator
  that says when not to buy one.
- [Guides](https://blvkware.dev/guides/): every guide above, grouped and
  summarised, in reading order.
- [Quote follow-up automation](https://blvkware.dev/quote-follow-up-automation/):
  how automated quote follow-up works, the arithmetic for deciding whether it
  pays, why the sequence must stop when the customer answers, and why US A2P
  10DLC registration (3-6 weeks) makes SMS-based follow-up slow to launch where
  email is live in days.
- [AI automation for plumbers](https://blvkware.dev/ai-automation-for-plumbers/):
  which plumbing processes are worth automating and which are not. Estimate
  follow-up and review requests first; dispatch, pricing and emergency call
  answering last or never. Includes the review-gating compliance line and why
  replacing ServiceTitan or Jobber to gain follow-up is a bad trade.
- [Vendor renewal tracker](https://blvkware.dev/vendor-renewal-tracker/): two free
  browser tools plus the method. A renewal deadline calculator that derives the
  notice deadline (renewal date minus notice period) and scores a vendor on
  value, waste and leverage, and a statement importer that reads a bank or card
  export in the browser and infers each billing cycle from the gaps between
  charges. Nothing is uploaded; there is no server.
- [Subscription audit](https://blvkware.dev/subscription-audit/): the method for
  cutting recurring business cost. Pull twelve months not three because annual
  charges hide in a short export; record seats paid against seats active; check
  cancel, downgrade, renegotiate and keep in that order; and sort the result by
  money recovered per minute rather than by size of saving, because sorting by
  size buries the quick wins under the hard conversation and the audit stalls.
- [Privacy policy](https://blvkware.dev/privacy/): no accounts, no analytics, no
  cookies, no tracking; tools keep data only in the visitor's own browser
- [Terms of service](https://blvkware.dev/terms/)
"""
    # Counts are rendered here rather than typed into the string, so a catalog
    # addition cannot leave the published summary quietly wrong.
    llms = llms.replace("{n_roles}", str(len(catalog.ROLES)))
    llms = llms.replace("{n_caps}", str(len(catalog.CAPABILITIES)))
    llms = llms.replace("{kit1}", _money(catalog.KITS[1]["price"]))
    llms = llms.replace("{kit2}", _money(catalog.KITS[2]["price"]))

    # The verification layer is appended rather than folded into the sections
    # above, and it is appended rather than leading. Those are two separate
    # decisions and both are deliberate.
    #
    # Appended, because the agent practice is the live business with published
    # prices and paying customers, and a reader arriving from a search for an
    # AI agent must not have to scroll past a package registry to find it.
    #
    # Generated rather than written, because an llms.txt that names an endpoint
    # this build could not confirm exists is the aspirational-catalog failure
    # in a different file. With no HALLUX checkout present, the block is empty
    # and the site simply does not mention it.
    import hallux_bridge

    llms = llms.rstrip() + "\n" + hallux_bridge.llms_section(base)
    with io.open(os.path.join(OUT_DIR, "llms.txt"), "w", encoding="utf-8") as fh:
        fh.write(llms)

    with io.open(os.path.join(OUT_DIR, INDEXNOW_KEY + ".txt"), "w", encoding="utf-8") as fh:
        fh.write(INDEXNOW_KEY)

    print("Built robots.txt, sitemap.xml (%d urls), llms.txt, IndexNow key file" % len(SITEMAP))


def redirect_page(slug):
    """A redirect that works without a server: header, meta refresh, and script.

    The query string is carried across so Agent Designer's `?prompt=` hand-off still lands
    if anything is holding the old URL.

    The destination is named rather than hard-coded. This was written for one
    rename and then reused for four, at which point every old URL was telling
    the visitor it had become the App Builder.
    """
    url = "/%s/" % slug
    name = next((t["name"] for t in TOOLS if t["slug"] == slug), slug)
    close_script = "<" + "/script>"
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta http-equiv=\"refresh\" content=\"0; url=" + url + "\">\n"
        "<link rel=\"canonical\" href=\"https://" + CUSTOM_DOMAIN + url + "\">\n"
        "<meta name=\"robots\" content=\"noindex\">\n"
        "<title>Moved to " + name + "</title>\n"
        "<script>location.replace('" + url + "' + location.search + location.hash);"
        + close_script + "\n"
        "</head>\n<body style=\"background:#0a0908;color:#a89d8b;font:15px/1.6 system-ui,sans-serif;"
        "display:grid;place-items:center;height:100vh;margin:0\">\n"
        "<p>This is now <a href=\"" + url + "\" style=\"color:#d4f24a\">" + name
        + "</a>.</p>\n"
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

    # EVERY inline block is checked, not just the last one. The tools now carry
    # the catalog and several shared engines ahead of their own script, and a
    # gate that inspected only the final block would quietly stop covering the
    # code most likely to be edited by hand.
    blocks = [b for b in re.findall(
        r"<script>\n((?:(?!<" + r"/script>)[\s\S])*)\n<" + r"/script>", src)
        if b.strip()]
    if not blocks:
        return True
    path = os.path.join(tempfile.gettempdir(), "_blvk_check.js")
    for i, block in enumerate(blocks, 1):
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(block)
        try:
            res = subprocess.run(["node", "--check", path],
                                 capture_output=True, text=True)
        except (OSError, ValueError):
            print("  note: node not found - JS syntax not verified for %s" % name)
            return True
        if res.returncode != 0:
            first = (res.stderr.strip().splitlines() or ["unknown error"])
            print("ABORTED: %s has invalid JavaScript in script block %d of %d"
                  % (name, i, len(blocks)))
            for line in first[:6]:
                print("         " + line)
            return False
    return True


def tool_schema(tool):
    """A SoftwareApplication node per tool, bound to the Organization.

    Each tool is free, browser-only and needs no sign-up; offers/price 0 and
    isAccessibleForFree make that claim machine-readable instead of marketing copy.
    """
    import json as _json
    base = "https://" + CUSTOM_DOMAIN
    node = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "@id": base + "/" + tool["slug"] + "/#app",
        "name": tool["name"],
        "alternateName": "BlvkWare " + tool["name"],
        "url": base + "/" + tool["slug"] + "/",
        "description": tool["desc"],
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": tool["subcategory"],
        "operatingSystem": "Any (runs in a web browser)",
        "browserRequirements": "Requires JavaScript.",
        "featureList": tool["features"],
        "image": base + "/assets/og.png",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "publisher": {"@id": base + "/#org"},
        "isPartOf": {"@id": base + "/#website"},
    }
    return ('<script type="application/ld+json">\n'
            + _json.dumps(node, indent=2, ensure_ascii=False)
            # Split so this file never contains a literal closing script tag,
            # which would end the block early when embedded in a page.
            + "\n<" + "/script>\n")



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
    # The provider picker asks the dev server for /api/providers. Static
    # hosting has no such endpoint, so every visit would log a 404; the
    # published copy skips the request and keeps the picker hidden.
    body = body.replace("async function loadProviders() {",
                        "async function loadProviders() {\n    return;  // static hosting: no provider endpoint", 1)
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
        "<meta property=\"og:url\" content=\"https://" + CUSTOM_DOMAIN + "/" + tool["slug"] + "/\">\n"
        "<meta property=\"og:site_name\" content=\"BlvkWare\">\n"
        # Without this each tool is an unclaimed URL, and any variant
        # (trailing slash, index.html, a query string) splits its signals.
        "<link rel=\"canonical\" href=\"https://" + CUSTOM_DOMAIN + "/" + tool["slug"] + "/\">\n"
        "<meta name=\"robots\" content=\"index, follow, max-snippet:-1, max-image-preview:large\">\n"
        # The tools are products, not pages. Declaring each as a
        # SoftwareApplication published by the Organization is what turns
        # "some pages on blvkware.dev" into named entities.
        + tool_schema(tool) +
        # Absolute paths: the tools live one directory down, and the assets are
        # generated from the master logo by dev/embed-logo.py.
        "<link rel=\"icon\" type=\"image/png\" sizes=\"48x48\" href=\"/assets/favicon-48.png\">\n"
        "<link rel=\"apple-touch-icon\" href=\"/assets/logo-192.png\">\n"
        + "<script>" + SHIM + close_script + "\n"
        "</head>\n<body>\n"
    )
    return head + body + "\n</body>\n</html>\n"


def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _money(n):
    return "$" + format(int(n), ",d")


def catalog_roles_html():
    """The public catalog's role cards, generated so they cannot contradict the
    configurator. A card that promises a capability the engine does not price is
    a promise made at the operator's expense."""
    out = []
    for fam in catalog.ROLE_FAMILIES:
        roles = [r for r in catalog.ROLES if r["family"] == fam]
        out.append('<div class="fam-head"><h3>%s</h3><span class="hr"></span>'
                   '<span class="fam-n">%d roles</span></div>' % (_esc(fam), len(roles)))
        out.append('<div class="grid">')
        for r in roles:
            out.append('<div class="card">')
            out.append('<h3>%s</h3>' % _esc(r["name"]))
            out.append('<div class="oneline">%s</div>' % _esc(r["oneLine"]))
            out.append('<p>%s</p>' % _esc(r["problem"]))
            out.append('<ul class="owns">')
            for cid in r["core"]:
                c = catalog.CAP_BY_ID[cid]
                out.append('<li><b>%s</b>: %s</li>' % (_esc(c["name"]), _esc(c["blurb"])))
            out.append('</ul>')
            if r["suggested"]:
                names = ", ".join(catalog.CAP_BY_ID[c]["name"] for c in r["suggested"])
                out.append('<p class="also">Usually added: %s</p>' % _esc(names))
            kit = catalog.KITS[r["minTier"]]
            out.append('<div class="foot-note"><b>%s</b> · %s at its recommended scope</div>'
                       % (_money(kit["price"]), _esc(kit["name"])))
            out.append('<a class="card-cta" href="/hire/">Design it &rarr;</a>')
            out.append('</div>')
        out.append('</div>')
    return "\n".join(out)


def catalog_components_html():
    """Every capability, grouped, with its acceptance test.

    No per-capability price: a kit is priced by its tier alone. What a buyer
    gets for each capability is a playbook, a workflow and a test, and the test
    is the line worth showing.
    """
    out = []
    for group in catalog.CAP_GROUPS:
        caps = [c for c in catalog.CAPABILITIES if c["group"] == group]
        out.append('<tr class="grouprow"><td colspan="3">%s</td></tr>' % _esc(group))
        for c in sorted(caps, key=lambda x: x["name"]):
            note = ""
            if c["gate"]:
                note = ' <span class="gate">%s</span>' % _esc(catalog.GATES[c["gate"]]["short"])
            out.append('<tr><td><b>%s</b></td><td>%s%s</td><td>%s</td></tr>'
                       % (_esc(c["name"]), _esc(c["blurb"]), note, _esc(c["accept"])))
    return "\n".join(out)


def catalog_itemlist_json():
    """The catalog page's ItemList, generated so the structured data and the
    visible cards cannot describe different products."""
    import json
    items = []
    for n, r in enumerate(catalog.ROLES, 1):
        kit = catalog.KITS[r["minTier"]]
        owns = "; ".join(catalog.CAP_BY_ID[c]["name"] for c in r["core"])
        items.append({
            "@type": "ListItem",
            "position": n,
            "name": r["name"],
            "description": "%s Owns: %s. Agent kit: %s (%s) at its recommended scope."
                           % (r["problem"], owns, _money(kit["price"]), kit["name"]),
        })
    node = {
        "@type": "ItemList",
        "name": "BlvkWare Agent Catalog",
        "description": "Named AI agent roles a small business can build. Each is "
                       "sold as a downloadable kit: the agent's instructions, "
                       "tools, workflows, record schemas, autonomy policy and "
                       "acceptance tests, generated from the buyer's answers at "
                       "https://blvkware.dev/hire/ and priced by the size of the "
                       "agent.",
        "url": "https://blvkware.dev/agents/",
        "numberOfItems": len(items),
        "itemListElement": items,
    }
    blob = json.dumps(node, ensure_ascii=False, indent=2)
    if "</" in blob:
        print("ABORTED: catalog ItemList contains a closing tag sequence")
        raise SystemExit(1)
    return "\n".join("    " + ln for ln in blob.splitlines())


def compile_catalog(html, name=""):
    """Inject the compiled catalog, the shared engine, and any generated markup.

    Every price a buyer can see and every manifest the operator builds from comes
    from dev/catalog.py through this one function. Nothing downstream is allowed
    to hold its own copy of a price.
    """
    if "/*CATALOG_JSON*/" in html:
        blob = catalog.as_json()
        # A JSON payload lives inside a <script> element, so any "</" sequence
        # would end the element early. JSON has no bare "</" outside strings and
        # "\/" is a valid escape, so this is safe and reversible.
        blob = blob.replace("</", "<\\/")
        html = html.replace("/*CATALOG_JSON*/", blob)

    for marker, src in (("/*ENGINE_JS*/", "engine.js"),
                        ("/*DESIGN_JS*/", "design.js"),
                        ("/*CONFIGURE_JS*/", "configure.js")):
        if marker not in html:
            continue
        path = os.path.join(ROOT, "dev", src)
        with io.open(path, encoding="utf-8") as fh:
            code = fh.read()
        if "</script" in code:
            print("ABORTED: dev/%s contains a closing script tag" % src)
            raise SystemExit(1)
        html = html.replace(marker, code)

    if "<!--CATALOG_STRIP-->" in html:
        chips = []
        for r in catalog.ROLES:
            cls = "role-chip dep" if r["minTier"] == 2 else "role-chip"
            chips.append('<a class="%s" href="/agents/"><b>%s</b><span>%s</span></a>'
                         % (cls, _esc(r["name"]), _esc(r["oneLine"])))
        chips.append('<a class="role-chip more" href="/hire/"><b>Pick one and design it &rarr;</b>'
                     '<span>%d capabilities to pick from</span></a>' % len(catalog.CAPABILITIES))
        html = html.replace("<!--CATALOG_STRIP-->", "\n                    ".join(chips))
    if "<!--CATALOG_ITEMLIST-->" in html:
        html = html.replace("<!--CATALOG_ITEMLIST-->", catalog_itemlist_json())
    if "<!--CATALOG_ROLES-->" in html:
        html = html.replace("<!--CATALOG_ROLES-->", catalog_roles_html())
    if "<!--CATALOG_COMPONENTS-->" in html:
        html = html.replace("<!--CATALOG_COMPONENTS-->", catalog_components_html())

    # The done-for-you tokens ({{TIER1_BUILD}}, {{TRIAL}} and the rest) are
    # gone on purpose. A page that still uses one fails the leftover check
    # below, which is how a retired price is kept from reaching a page.
    for token, value in (
        ("{{KIT1_PRICE}}", _money(catalog.KITS[1]["price"])),
        ("{{KIT2_PRICE}}", _money(catalog.KITS[2]["price"])),
        ("{{KIT1_PRICE_NUM}}", str(catalog.KITS[1]["price"])),
        ("{{KIT2_PRICE_NUM}}", str(catalog.KITS[2]["price"])),
        ("{{N_ROLES}}", str(len(catalog.ROLES))),
        ("{{N_CAPS}}", str(len(catalog.CAPABILITIES))),
    ):
        html = html.replace(token, value)

    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", html)
    if leftover:
        print("ABORTED: %s has unresolved tokens: %s" % (name, ", ".join(sorted(set(leftover)))))
        raise SystemExit(1)
    return html


#: Fira Code draws `--` as one long bar and `->` as an arrow, through its
#: contextual alternates. In a command a reader copies, `--transport` then
#: looks like an em dash in front of a word, which is neither what they will
#: paste nor what the copy rules allow. Standard ligatures in the text faces
#: are left alone; only the contextual ones go.
CODE_LIGATURES_OFF = ('<style id="no-code-ligatures">*{font-variant-ligatures:'
                      'no-contextual}</style>\n')


def disable_code_ligatures():
    """Add CODE_LIGATURES_OFF to every built page that loads Fira Code.

    A pass over the output rather than an edit to each source, because
    pages reach docs/ by five different routes (tools, the root, marketing
    pages, verbatim tools, and the pages HALLUX's bridge generates).
    """
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            with io.open(path, encoding="utf-8") as fh:
                html = fh.read()
            if ("Fira Code" not in html or 'id="no-code-ligatures"' in html
                    or "</head>" not in html):
                continue
            html = html.replace("</head>", CODE_LIGATURES_OFF + "</head>", 1)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(html)
            count += 1
    return count


SAMPLE_ZIP = "samples/blvkware-sample-kit-follow-up-agent.zip"
#: Files the sample page opens by default: the ones a buyer reads first.
SAMPLE_OPEN = ("README.md", "prompts/system.md")


def _kb(size):
    return "%.1f KB" % (size / 1024.0) if size >= 1024 else "%d B" % size


def build_sample_kit():
    """Regenerate the free sample kit and return the tokens its page needs.

    The zip is built by the kit service's own code (blvkware-agentcore/kits/
    tools/sample.mjs), so the sample is exactly what a buyer's download looks
    like for that design. Where that repository is not checked out, the
    committed zip is used as is. Returns None if there is no zip at all, and
    the page is then skipped rather than published half-empty.
    """
    import subprocess
    import zipfile

    target = os.path.join(OUT_DIR, *SAMPLE_ZIP.split("/"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    tool = os.path.join(os.path.dirname(ROOT), "blvkware-agentcore", "kits", "tools", "sample.mjs")
    if os.path.isfile(tool):
        run = subprocess.run(["node", tool, target], capture_output=True, text=True)
        if run.returncode != 0:
            print("WARNING: sample kit not regenerated: %s" % (run.stderr.strip()[-300:] or run.stdout))
    if not os.path.isfile(target):
        print("WARNING: no sample kit at docs/%s; /sample-kit/ skipped" % SAMPLE_ZIP)
        return None

    with zipfile.ZipFile(target) as archive:
        entries = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = info.filename.split("/", 1)[1] if "/" in info.filename else info.filename
            entries.append((path, archive.read(info).decode("utf-8")))
    order = {"SAMPLE.md": 0, "README.md": 1, "SETUP.md": 2, "LICENSE.md": 3, "agent.json": 4}
    entries.sort(key=lambda e: (order.get(e[0], 9), "/" in e[0], e[0]))

    def anchor(path):
        return "f-" + re.sub(r"[^A-Za-z0-9]+", "-", path).strip("-")

    def esc(text):
        # Braces too: a kit may carry {{PLACEHOLDERS}} of its own, which the
        # catalog's leftover-token check would otherwise refuse.
        return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("{", "&#123;").replace("}", "&#125;"))

    tree, current = [], None
    for path, content in entries:
        folder = path.rsplit("/", 1)[0] if "/" in path else ""
        if folder != current:
            if folder:
                tree.append('<div class="dir">%s/</div>' % esc(folder))
            current = folder
        tree.append('<a class="%s" href="#%s">%s<span>%s</span></a>' % (
            "in" if folder else "", anchor(path), esc(path.rsplit("/", 1)[-1]),
            _kb(len(content.encode("utf-8")))))

    files = []
    for path, content in entries:
        files.append('<details id="%s"%s><summary><b>%s</b><span>%s</span></summary><pre>%s</pre></details>' % (
            anchor(path), " open" if path in SAMPLE_OPEN else "", esc(path),
            _kb(len(content.encode("utf-8"))), esc(content)))

    def count(prefix, suffix):
        return sum(1 for p, _ in entries if p.startswith(prefix) and p.endswith(suffix))

    tools = 0
    for path, content in entries:
        if path == "tools/tools.json":
            tools = len(json.loads(content).get("tools", []))
    facts = [
        (len(entries), "files"),
        (count("prompts/capabilities/", ".md"), "capabilities"),
        (tools, "tools"),
        (count("workflows/", ".json"), "workflows"),
        (count("schemas/records/", ".json"), "record schemas"),
    ]
    return {
        "{{SAMPLE_ZIP}}": "/" + SAMPLE_ZIP,
        "{{SAMPLE_SIZE}}": _kb(os.path.getsize(target)),
        "{{SAMPLE_FACTS}}": "".join('<div class="fact"><b>%d</b><span>%s</span></div>' % f for f in facts),
        "{{SAMPLE_TREE}}": "\n".join(tree),
        "{{SAMPLE_FILES}}": "\n".join(files),
    }


GENERIC_CARD = "https://blvkware.dev/assets/og.png"


# Pages written as <dir>/index.html but named without the trailing slash in
# the sources. GitHub Pages answers the slashless form with a 301, so a
# canonical or link naming it points search engines at a redirect.
DIRECTORY_PAGES = ("docs/hallux-spec", "docs/limits", "docs/corpus-methodology",
                   "docs/payment", "pricing", "legal/corpus-license", "legal/bsl-1.1")


def slash_directory_urls():
    """Give every link, canonical and structured-data URL for a directory page
    its trailing slash, so nothing on the site names a URL that redirects."""
    alt = "|".join(re.escape(p) for p in DIRECTORY_PAGES)
    attr = re.compile(r'((?:href|content)=")((?:https://blvkware\.dev)?/(?:%s))([#?][^"]*)?"' % alt)
    ld = re.compile(r'("https://blvkware\.dev/(?:%s))"' % alt)
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            with io.open(path, encoding="utf-8") as fh:
                html = fh.read()
            new = attr.sub(lambda m: '%s%s/%s"' % (m.group(1), m.group(2), m.group(3) or ""), html)
            new = ld.sub(r'\1/"', new)
            if new != html:
                count += 1
                with io.open(path, "w", encoding="utf-8") as fh:
                    fh.write(new)
    return count


# The guides hub at /guides/, in reading order. Each entry is a built page;
# its title and summary are read from that page, so the hub cannot drift.
GUIDES = (
    ("Start here", ("what-is-an-ai-agent", "ai-agent-pricing", "ai-employee")),
    ("Running an agent safely", ("ai-agent-permissions", "how-agents-are-controlled")),
    ("Jobs worth automating", ("quote-follow-up-automation", "ai-automation-for-plumbers",
                               "subscription-audit", "vendor-renewal-tracker")),
    ("See a real system", ("recovery-os", "sample-kit")),
)


def build_guides_page():
    """Write /guides/: every guide, grouped, with its own title and summary.

    A hub that links each article with a sentence about it is how a crawler
    or an assistant finds the set as a set, and it gives the header's Guides
    link somewhere to go. It borrows the article pages' shell so it looks
    like one of them.
    """
    shell_path = os.path.join(OUT_DIR, "what-is-an-ai-agent", "index.html")
    with io.open(shell_path, encoding="utf-8") as fh:
        shell = fh.read()
    style = shell[shell.index("<style>"):shell.index("</style>") + len("</style>")]
    groups, items = [], []
    for heading, slugs in GUIDES:
        cards = []
        for slug in slugs:
            path = os.path.join(OUT_DIR, slug, "index.html")
            if not os.path.isfile(path):
                print("WARNING: guide %s not built" % slug)
                continue
            with io.open(path, encoding="utf-8") as fh:
                page = fh.read()
            title = re.sub(r"<[^>]+>", "", re.search(r"<h1[^>]*>(.*?)</h1>", page, re.S).group(1)).strip()
            desc = re.search(r'<meta name="description" content="([^"]*)"', page).group(1)
            dates = _git_dates(os.path.join(ROOT, "site", slug + ".html"))
            when = ""
            if dates:
                d = datetime.date.fromisoformat(dates[1])
                when = '<time datetime="%s">Updated %s %d, %d</time>' % (dates[1], d.strftime("%B"), d.day, d.year)
            url = "/%s/" % slug
            cards.append('<li class="guide"><a href="%s"><span class="g-title">%s</span>'
                         '<span class="g-desc">%s</span>%s</a></li>' % (url, title, desc, when))
            items.append({"@type": "ListItem", "position": len(items) + 1,
                          "url": "https://blvkware.dev" + url, "name": title})
        groups.append('<h2>%s</h2>\n<ul class="guides">%s</ul>' % (heading, "".join(cards)))
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "BlvkWare", "item": "https://blvkware.dev/"},
                {"@type": "ListItem", "position": 2, "name": "Guides", "item": "https://blvkware.dev/guides/"}]},
            {"@type": "CollectionPage", "name": "BlvkWare guides",
             "url": "https://blvkware.dev/guides/", "publisher": {"@id": "https://blvkware.dev/#org"},
             "mainEntity": {"@type": "ItemList", "itemListElement": items}},
        ],
    }
    desc = ("Plain-language guides to AI agents for small businesses: what an agent is, what it "
            "should cost, how to keep it safe, and which jobs are worth handing to one.")
    extra_css = """<style>
.guides { list-style: none; padding: 0; margin: 0 0 2.75rem; display: grid; gap: .8rem; }
.guide a { display: block; padding: 1.1rem 1.25rem; border: 1px solid var(--line); border-radius: 12px;
           background: var(--surface); text-decoration: none; color: inherit; transition: border-color .2s ease; }
.guide a:hover { border-color: rgba(212,242,74,.45); text-decoration: none; }
.g-title { display: block; font-weight: 800; font-size: 1.08rem; color: var(--ink); margin-bottom: .3rem; }
.g-desc { display: block; color: var(--ink-2); font-size: .95rem; line-height: 1.55; }
.guide time { display: block; margin-top: .55rem; font-family: var(--mono); font-size: .7rem;
              letter-spacing: .08em; text-transform: uppercase; color: var(--brass); }
</style>"""
    html = (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>Guides to AI Agents for Small Business | BlvkWare</title>\n'
        '<meta name="description" content="%s">\n'
        '<link rel="canonical" href="https://blvkware.dev/guides/">\n'
        '<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">\n'
        '<meta property="og:title" content="Guides to AI agents for small business">\n'
        '<meta property="og:description" content="%s">\n'
        '<meta property="og:type" content="website">\n'
        '<meta property="og:url" content="https://blvkware.dev/guides/">\n'
        '<meta property="og:image" content="%s">\n'
        '<meta property="og:site_name" content="BlvkWare">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        '<link rel="icon" type="image/png" sizes="48x48" href="/assets/favicon-48.png">\n'
        '<link rel="apple-touch-icon" href="/assets/logo-192.png">\n'
        '<meta name="theme-color" content="#0A0908">\n'
        '<script type="application/ld+json">\n%s\n</script>\n%s\n%s\n</head>\n<body>\n'
        '<div class="wrap">\n'
        '<a class="top" href="/"><span class="mark"><img src="/assets/logo-192.png" alt="BlvkWare" width="192" height="192"></span>'
        '<span class="wordmark">BlvkWare<span>.</span></span></a>\n'
        '<div class="eyebrow">Guides</div>\n<h1>Guides to AI agents</h1>\n'
        '<p class="lede">Written for the owner who has to decide, not the vendor selling to them. Each one '
        'answers a question people ask before buying an agent, with the arithmetic and the reasons not to.</p>\n'
        '%s\n'
        '<p>Ready to try one against your own business? <a href="/hire/">Design an agent</a> and see its '
        'whole kit and price before you pay, or <a href="/sample-kit/">read a complete sample kit</a> first.</p>\n'
        '</div>\n</body>\n</html>\n'
    ) % (desc, desc, GENERIC_CARD, json.dumps(schema, indent=2), style, extra_css, "\n".join(groups))
    out = os.path.join(OUT_DIR, "guides")
    os.makedirs(out, exist_ok=True)
    with io.open(os.path.join(out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print("Built docs/guides/index.html (%d guides)" % len(items))


SITE_NAV = (
    ("/agents/", "Agents"),
    ("/sample-kit/", "Sample kit"),
    ("/#lab", "Free tools"),
    ("/guides/", "Guides"),
    ("/hallux/", "Developers"),
)
SITE_NAV_CSS = """<style>
.sitebar { display: flex; align-items: center; justify-content: space-between; gap: 1.25rem; flex-wrap: wrap; }
.sitebar > .top { margin-bottom: 0 !important; }
.sitenav { display: flex; align-items: center; gap: 1.35rem; font-size: .9rem; }
.sitenav a { color: var(--ink-2, #A89D8B); text-decoration: none; font-weight: 600; white-space: nowrap; }
.sitenav a:hover, .sitenav a[aria-current] { color: var(--ink, #F5F0E6); text-decoration: none; }
.sitenav .sitenav-cta { color: #14170A; background: var(--accent, #D4F24A); padding: .5rem .9rem; border-radius: 8px; font-weight: 700; }
.sitenav .sitenav-cta:hover { color: #14170A; filter: brightness(1.06); }
@media (max-width: 720px) { .sitenav a:not(.sitenav-cta) { display: none; } }
</style>
"""


def add_site_nav():
    """Give every secondary page the same header navigation.

    Articles, product pages and references were written with the logo alone
    at the top, so a visitor who lands on one from search has no way to the
    catalog, the free tools or the kit page except the footer. This wraps
    the existing logo link in a header with the site's main destinations and
    the one call to action, marking the current page. The kit page itself
    keeps the links but not a button that points back at itself.
    """
    top = re.compile(r'<a class="top" href="/">.*?</a>', re.S)
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        if "index.html" not in files:
            continue
        rel = "/" + os.path.relpath(dirpath, OUT_DIR).replace(os.sep, "/") + "/"
        path = os.path.join(dirpath, "index.html")
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        m = top.search(html)
        if not m or 'class="sitebar"' in html:
            continue
        links = "".join(
            '<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if href == rel else "", label)
            for href, label in SITE_NAV)
        if rel != "/hire/":
            links += '<a class="sitenav-cta" href="/hire/">Design an agent</a>'
        bar = ('<header class="sitebar" style="margin-bottom:2.75rem">%s'
               '<nav class="sitenav" aria-label="Site">%s</nav></header>' % (m.group(0), links))
        html = html[:m.start()] + bar + html[m.end():]
        html = html.replace("</head>", SITE_NAV_CSS + "</head>", 1)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        count += 1
    return count


GOOGLE_FONTS_IMPORT = re.compile(r"@import url\('https://fonts\.googleapis\.com/[^']*'\);?\s*")
GOOGLE_FONTS_LINK = re.compile(r'<link[^>]*(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^>]*>\s*')
FONT_HEAD = ('<link rel="preload" href="/assets/fonts/manrope-latin-400-800.woff2" as="font" '
             'type="font/woff2" crossorigin>\n<link rel="stylesheet" href="/assets/fonts/fonts.css">\n')


def self_host_fonts():
    """Serve the typefaces from blvkware.dev instead of Google Fonts.

    The sources keep their @import so each file still renders when opened on
    its own. Published pages get the local stylesheet in the head instead: an
    @import inside <style> is fetched only after the stylesheet is parsed and
    then chains to a second origin for the font files, which delays first
    paint, and it hands every visitor's IP address to Google. The files in
    docs/assets/fonts are the same OFL-licensed fonts, licences alongside.
    """
    if not os.path.isfile(os.path.join(OUT_DIR, "assets", "fonts", "fonts.css")):
        print("WARNING: docs/assets/fonts/fonts.css missing - fonts left on Google")
        return 0
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        for name in files:
            if not name.endswith(".html"):
                continue
            path = os.path.join(dirpath, name)
            with io.open(path, encoding="utf-8") as fh:
                html = fh.read()
            if "fonts.googleapis.com" not in html:
                continue
            new = GOOGLE_FONTS_LINK.sub("", GOOGLE_FONTS_IMPORT.sub("", html))
            if "/assets/fonts/fonts.css" not in new:
                new = new.replace("<style>", FONT_HEAD + "<style>", 1)
            if "fonts.googleapis.com" in new:
                print("WARNING: %s still names Google Fonts" % os.path.relpath(path, OUT_DIR))
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            count += 1
    return count


def _git_dates(path):
    """(first, last) commit dates of a source file, or None outside git.

    A file with uncommitted edits counts as modified today, since that is
    the version being published."""
    import subprocess
    try:
        run = lambda *a: subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True,
                                        text=True, check=True).stdout.split()
        log = run("log", "--follow", "--format=%cs", "--", path)
        if not log:
            return None
        dirty = run("status", "--porcelain", "--", path)
        return log[-1], (BUILD_DATE if dirty else log[0])
    except Exception:
        return None


def complete_article_schema():
    """Date and illustrate every Article node, and show the date on the page.

    Search engines and answer engines weigh freshness, and an Article without
    datePublished, dateModified and image is incomplete for Google's article
    features. The dates come from the source file's git history, so they are
    never invented. Runs after point_social_cards so the image is the page's
    own card.
    """
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        if "index.html" not in files:
            continue
        rel = os.path.relpath(dirpath, OUT_DIR).replace(os.sep, "/")
        source = os.path.join(ROOT, "site", rel + ".html")
        path = os.path.join(dirpath, "index.html")
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        if '"@type": "Article"' not in html or not os.path.isfile(source):
            continue
        dates = _git_dates(source)
        if not dates:
            continue
        published, modified = dates
        image = re.search(r'<meta property="og:image" content="([^"]+)"', html)

        def fill(m):
            node = m.group(0)
            extra = ""
            if '"datePublished"' not in node:
                extra += ',\n      "datePublished": "%s"' % published
            if '"dateModified"' not in node:
                extra += ',\n      "dateModified": "%s"' % modified
            if '"image"' not in node and image:
                extra += ',\n      "image": "%s"' % image.group(1)
            return node[:-1].rstrip() + extra + "\n    }"

        html = re.sub(r'\{\s*"@type": "Article",[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', fill, html, count=1)
        when = datetime.date.fromisoformat(modified)
        stamp = "Updated %s %d, %d" % (when.strftime("%B"), when.day, when.year)
        html = re.sub(r'(<div class="eyebrow">)([^<]*)(</div>)',
                      lambda m: "%s%s <span class=\"updated\">&middot; <time datetime=\"%s\">%s</time></span>%s"
                      % (m.group(1), m.group(2).strip(), modified, stamp, m.group(3)), html, count=1)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        count += 1
    return count


def point_social_cards():
    """Give every built page its own og:image, when marketing/og/render.py made one.

    Pages are written with the generic card. A link shared from /hallux/
    should preview HALLUX, not the logo, so each page whose card exists at
    docs/assets/og/<slug>.png is pointed at it, with twitter:image and the
    image size alongside. A page without a card keeps the generic one, so
    no page ever names an image that is not there.
    """
    cards = os.path.join(OUT_DIR, "assets", "og")
    count = 0
    for dirpath, _dirs, files in os.walk(OUT_DIR):
        if "index.html" not in files:
            continue
        path = os.path.join(dirpath, "index.html")
        rel = os.path.relpath(dirpath, OUT_DIR).replace(os.sep, "/")
        slug = "home" if rel in (".", "") else rel.replace("/", "-")
        card = os.path.join(cards, slug + ".png")
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        if 'property="og:image"' not in html:
            continue
        url = ("https://blvkware.dev/assets/og/%s.png" % slug) if os.path.isfile(card) else GENERIC_CARD
        html = re.sub(r'<meta property="og:image" content="[^"]*">',
                      '<meta property="og:image" content="%s">' % url, html, count=1)
        extra = ""
        if 'property="og:image:width"' not in html:
            extra += ('<meta property="og:image:width" content="1200">'
                      '<meta property="og:image:height" content="630">')
        if 'name="twitter:image"' not in html:
            extra += '<meta name="twitter:image" content="%s">' % url
        else:
            html = re.sub(r'<meta name="twitter:image" content="[^"]*">',
                          '<meta name="twitter:image" content="%s">' % url, html, count=1)
        if extra:
            html = html.replace('<meta property="og:image" content="%s">' % url,
                                '<meta property="og:image" content="%s">%s' % (url, extra), 1)
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        count += url != GENERIC_CARD
    return count


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # Named hallux_bridge, not hallux: dev/ is on sys.path when this runs,
    # so a module called hallux.py here shadows the HALLUX package itself
    # and the bridge ends up importing from its own file.
    import hallux_bridge as hallux
    print(hallux.status())
    # Every rendered page, kept so the typed-price check can read the output
    # rather than the source. The last time prices drifted on this site most
    # of them were not in the HTML at all.
    rendered = {}

    # A catalog edit that silently reprices every Tier I role as a Tier II is a
    # business bug that looks like nothing in a diff. It blocks the build.
    import thresholds
    if thresholds.main() != 0:
        print("ABORTED: tier thresholds are wrong - see above")
        return 1

    # The browser writes a configuration and agentcore consumes it, from two
    # separate repos. Drift between them is invisible in a diff and shows up as
    # an order arriving as manual work, or as configuration silently discarded
    # at load. Warn rather than abort: agentcore is private, and a copy of this
    # repo without it must still be able to publish the site.
    try:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "configure_coverage", os.path.join(os.path.dirname(__file__), "check-configure-coverage.py"))
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        if _mod.main() != 0:
            print("WARNING: the builder and agentcore have drifted - see above")
    except Exception as e:                       # never let a check break a build
        print("note: configure coverage check skipped (%s)" % e)

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
        # The Lab tools design and price real agents now, so they are compiled
        # against the same catalog as the site. A tool quoting from its own copy
        # of the price list is the drift this whole arrangement exists to stop.
        page = compile_catalog(page, tool["src"])
        out_dir = os.path.join(OUT_DIR, tool["slug"])
        if not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with io.open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(page)
        print("Built docs/%s/index.html (%.1f KB)"
              % (tool["slug"], len(page.encode("utf-8")) / 1024.0))

    # /html-generator/ was the tool's address before it was named App Builder. Links to
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
        # The Developers menu and section quote HALLUX's live coverage, so the
        # root page takes the same token pass as the HALLUX page.
        try:
            site_html = hallux.fill(site_html, "site/index.html")
        except ValueError as e:
            print("ABORTED: %s" % e)
            return 1
        site_html = compile_catalog(site_html, "site/index.html")
        with io.open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(site_html)
        print("Built docs/index.html (%.1f KB)  marketing site"
              % (len(site_html.encode("utf-8")) / 1024.0))
    else:
        print("WARNING: site/index.html missing - root page not built")

    # The free sample kit: regenerated by the kit service's own code.
    sample = build_sample_kit()
    if sample:
        print("Built docs/%s (%s)" % (SAMPLE_ZIP, sample["{{SAMPLE_SIZE}}"]))

    # Standalone marketing pages, each at its own clean directory URL.
    for src, slug in MARKETING_PAGES:
        path = os.path.join(ROOT, "site", src)
        if not os.path.isfile(path):
            print("WARNING: site/%s missing" % src)
            continue
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        if src == "sample-kit.html":
            if not sample:
                continue
            for token, value in sample.items():
                html = html.replace(token, value)
        # HALLUX prices live in a separate repository. The page carries tokens
        # rather than numbers, and this fills them. It runs BEFORE
        # compile_catalog, whose own unresolved-token guard would otherwise
        # abort on a {{HALLUX_*}} it has never heard of.
        try:
            html = hallux.fill(html, "site/" + src)
        except ValueError as e:
            print("ABORTED: %s" % e)
            return 1
        html = compile_catalog(html, "site/" + src)
        rendered[slug] = html
        d = os.path.join(OUT_DIR, slug)
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        print("Built docs/%s/index.html (%.1f KB)" % (slug, len(html.encode("utf-8")) / 1024.0))

    # Standalone browser tools, copied verbatim to their own directory URL.
    for slug, src in STATIC_TOOLS:
        path = os.path.join(ROOT, "site", src)
        if not os.path.isfile(path):
            print("WARNING: site/%s missing" % src)
            continue
        with io.open(path, encoding="utf-8") as fh:
            html = fh.read()
        d = os.path.join(OUT_DIR, *slug.split("/"))
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        print("Built docs/%s/index.html (%.1f KB)  tool"
              % (slug, len(html.encode("utf-8")) / 1024.0))

    # Retired 2026-09-21 with done-for-you: the fulfilment console (ops/) and
    # the Stripe checkout function (api/). Kits are generated and delivered
    # by the kit service in blvkware-agentcore/kits, which runs this site's
    # catalog and engine, so nothing here needs to emit a copy for it.

    # The machine-readable surface, generated by HALLUX itself so the catalog
    # this publishes is the catalog HALLUX's own tests check.
    try:
        note = hallux.build_surface(OUT_DIR)
        if note:
            print("Built docs/.well-known/ai-catalog.json")
    except RuntimeError as e:
        print("WARNING: %s" % e)

    # The MCP Registry proves blvkware.dev owns dev.blvkware/hallux by
    # fetching this record: the public half of the key HALLUX's
    # dev/publish-registry.py signs with. Copied from the HALLUX repository so
    # the record and the key cannot disagree; losing it breaks every future
    # update of the registry listing.
    hallux_path = hallux.locate()
    record = os.path.join(hallux_path, "deploy", "mcp-registry", "mcp-registry-auth") if hallux_path else ""
    if record and os.path.isfile(record):
        well_known = os.path.join(OUT_DIR, ".well-known")
        os.makedirs(well_known, exist_ok=True)
        with io.open(record, encoding="utf-8") as fh:
            text = fh.read().strip()
        with io.open(os.path.join(well_known, "mcp-registry-auth"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text + "\n")
        print("Built docs/.well-known/mcp-registry-auth")

    # The specification, at the URL the page, llms.txt and the catalog all
    # point at. Those links exist, so the page has to.
    spec = hallux.build_spec_page(OUT_DIR)
    if spec:
        print("Built docs/docs/hallux-spec/index.html (%.1f KB)  specification"
              % (os.path.getsize(spec) / 1024.0))

    # The catalog names a licence URL and a limits URL. Both have to resolve,
    # so both are generated: the licence from the LICENSE file, the limits
    # from the constants the server actually enforces.
    for builder, label in ((hallux.build_licence_page, "legal/bsl-1.1"),
                           (hallux.build_limits_page, "docs/limits")):
        built = builder(OUT_DIR)
        if built:
            print("Built docs/%s/index.html (%.1f KB)"
                  % (label, os.path.getsize(built) / 1024.0))

    # The four pages the API itself links to: /v1/stats names the corpus
    # methodology, corpus responses a licence, and every 402 names payment
    # docs and a price list. Generated from the specification and the
    # running constants, like the two above.
    try:
        for built in hallux.build_reference_pages(OUT_DIR):
            print("Built docs/%s (%.1f KB)"
                  % (os.path.relpath(built, OUT_DIR).replace(os.sep, "/"),
                     os.path.getsize(built) / 1024.0))
    except ValueError as e:
        print("ABORTED: %s" % e)
        return 1

    # The human page and the agent catalog must quote the same prices, which
    # is the one failure the deploy notes single out. Asserted positively
    # against the pages we control rather than scanned for negatively across
    # the whole site, because BlvkWare sells two things and their prices
    # overlap; see the note in dev/hallux_bridge.py.
    problems, notes = hallux.check_published_prices(rendered, OUT_DIR)
    for note in notes:
        print("note: %s" % note)
    if problems:
        for problem in problems:
            print("ABORTED: %s" % problem)
        return 1

    build_guides_page()
    write_seo_files()

    print("Turned off code ligatures on %d pages" % disable_code_ligatures())
    print("Pointed %d pages at their own social card" % point_social_cards())
    print("Slashed directory URLs on %d pages" % slash_directory_urls())
    print("Dated %d articles from git history" % complete_article_schema())
    print("Self-hosted fonts on %d pages" % self_host_fonts())
    print("Added the site header to %d pages" % add_site_nav())

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
