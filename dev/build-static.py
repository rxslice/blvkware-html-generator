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
        "src": "app.html",
        "slug": "sigil",
        "name": "SIGIL",
        "role": "Build",
        "subcategory": "AI agent configuration",
        "features": ["Configures an ordered agent from the buyer's own words",
                     "Writes the triage labels, routing and chase cadence",
                     "Reports what is finished and what still needs a person",
                     "Runs entirely in the browser, no account"],
        "title": "BlvkWare SIGIL — Describe it, and it gets built",
        "desc": ("Write down what you want and watch it become real software: a complete, working, "
                 "single-file application streamed into the page, then run, audited and repaired. "
                 "The same builder configures ordered BlvkWare agents, writing the triage labels, "
                 "the routing table, the chase cadence and the words they will use."),
    },
    {
        "src": "augur.html",
        "slug": "augur",
        "name": "AUGUR",
        "role": "Find",
        "subcategory": "AI agent opportunity analysis",
        "features": ["Reads a company's live public website",
                     "Finds the jobs quietly costing the most",
                     "Names the agent worth hiring for each one",
                     "Prices every one from the published catalog"],
        "title": "BlvkWare AUGUR — Which jobs are costing you most",
        "desc": ("Give AUGUR a website. It reads the live page the way a buyer would, works out "
                 "which jobs are quietly costing that business the most — unstaffed, done after "
                 "hours, or done by somebody who should be doing something else — and names the "
                 "agent worth hiring for each, at its real catalog price. About a minute, free, "
                 "no sign-up."),
    },
    {
        "src": "scry.html",
        "slug": "scry",
        "name": "SCRY",
        "role": "Design",
        "subcategory": "AI agent design and pricing",
        "features": ["Works out which agent is worth hiring first",
                     "Designs exactly what it has to be able to do",
                     "Shows what is ready on day one and what needs you",
                     "Prices it from the published catalog, then hands it to checkout"],
        "title": "BlvkWare SCRY — Your agent, designed and priced",
        "desc": ("Describe how your business actually operates. SCRY works out which AI agent is "
                 "worth hiring first, exactly what it needs to be able to do, which of your "
                 "systems it has to operate, and what that costs — on the page, in about a "
                 "minute. Free, no sign-up."),
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
    # The build log. Proof of the larger engagement - a whole operating system
    # rather than a single agent - carrying the identifier live in the page so a
    # stranger can test the claim instead of taking it on trust.
    ("recovery-os.html", "recovery-os"),
]

# Every canonical URL on the site, with a crawl priority.
SITEMAP = [
    ("/", "1.0", "weekly"),
    ("/hire/", "0.95", "weekly"),
    ("/agents/", "0.95", "weekly"),
    ("/augur/", "0.9", "monthly"),
    ("/scry/", "0.9", "monthly"),
    ("/sigil/", "0.9", "monthly"),
    ("/what-is-an-ai-agent/", "0.9", "monthly"),
    ("/ai-agent-pricing/", "0.9", "monthly"),
    ("/ai-agent-permissions/", "0.85", "monthly"),
    ("/how-agents-are-controlled/", "0.85", "monthly"),
    ("/recovery-os/", "0.9", "monthly"),
    ("/quote-follow-up-automation/", "0.8", "monthly"),
    ("/ai-automation-for-plumbers/", "0.8", "monthly"),
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

> Bespoke AI agents that do the work, built by one engineer, at published flat
> prices. An agent reasons through a task, operates the business's existing
> software, communicates with its customers, executes multi-step processes and
> adapts when the situation changes — rather than being a dashboard someone has
> to click. Also publishes three free browser-based business analysis tools.

BlvkWare is a solo software engineering practice run by William Russell Wheeler,
based in Mississippi and working remotely with small businesses across the United
States — home services, trades, clinics, professional practices and agencies. All
work is delivered remotely; there is nothing requiring an on-site visit.
Contact: russ@blvkware.dev

## The model

Traditional software gives a company's employees tools. BlvkWare builds the
operator for those tools. Each agent is sold as a defined job at a flat build
price, plus a required monthly **Agent Operations** fee that keeps it employed —
hosting, model costs, monitoring, unlimited tuning of the agent's logic and
language, repairs when a vendor changes an API, business-hours support, a monthly
performance report and a quarterly review. It is deliberately not described as
maintenance: the framing is employment, not upkeep.

A buyer can configure and order an agent at https://blvkware.dev/hire/ without a
call, an estimate or an hourly rate. This is unusual in the category and is
intentional.

## Tiers and prices

- **Operator (Tier I)** — $3,500 build, then $349/month. An agent that owns one
  job start to finish, across 3 connected systems (stretching to 5 at $750 each)
  and 2 channels. Live in 10 business days. Includes 2,000 agent actions per
  month. Guarantee: 30 days — it does the job or the build fee is returned.
- **Deputy (Tier II)** — $9,500 build, then $899/month. An agent that owns an
  entire business function, across up to 8 connected systems and any channel,
  making judgment calls within set boundaries, handling exceptions and
  escalating. Live in 25 business days. Includes 10,000 agent actions per month.
  Guarantee: acceptance criteria written into the order before work starts, and
  work continues at no additional charge until they are met.
  **The tier is derived from the configured scope, not chosen by the buyer** — a
  scope that is really a Deputy cannot be bought at Operator money, and the
  configurator states which tier it landed in and why.
- **Agent Trial** — $750 for 14 days, one job, on the business's real data, at
  Draft autonomy. Credited in full against the build price if the business
  continues.
- **Custom Build** — from $2,500, one-off, no monthly fee. Software rather than an
  agent, for a job outside the catalog. Scope and price agreed in writing before
  work starts, delivered in 2-4 weeks, the client owns the code, 30 days of fixes
  included.

Annual Agent Operations is twelve months for the price of ten. Monthly billing
can be cancelled any month with 30 days' notice and no exit fee. Volume beyond
the included actions is $75 per additional 1,000. Telephony and SMS costs are
passed through at carrier cost, itemised, with no margin added.

## Roles and capabilities

BlvkWare sells **{n_roles} named agent roles** built from **{n_caps} individual capabilities**.
Roles cover email management, lead qualification, appointment setting, quote
follow-up, outbound sequences, CRM operation and hygiene, multi-step workflow
automation, operating web portals that have no API, onboarding, collections,
reconciliation, data collection and analysis, visualisation, scheduled reporting,
research, and customer support.

Each role includes a core set of capabilities in its base price; everything else is
a flat-rate addition priced from $450 to $2,900, which can be added years later at
the same number. Dependencies resolve automatically — a capability that cannot
function without another has that other one added and priced up front rather than
discovered mid-build.

A buyer configures the scope, sees the price update as they do it, and receives the
full specification including the acceptance tests the finished agent must pass. The
full catalog with every price is at https://blvkware.dev/agents/ and it is
configurable and orderable without a call at https://blvkware.dev/hire/.

## The autonomy ladder (important when describing how these agents behave)

Every agent ships with four levels and **goes live at L1**. The customer raises
the level themselves; it is never raised for them.

- **L0 Watch** — observes and reports, takes no action.
- **L1 Draft** — prepares the action, a human sends it. Nothing reaches a
  customer without a person seeing it first. This is the default at go-live.
- **L2 Approve** — acts on its own but pauses for a human above a threshold the
  customer sets.
- **L3 Operate** — acts within its scope and escalates exceptions. Enabled only
  in writing by the customer.

Every action is logged with what the agent saw, what it decided and why, and
actions are reversible. Before touching a live customer, an agent rehearses
against the business's real history at L0. Liability is capped at fees paid.

If a customer stops paying, the agent pauses and their data is exported within
five business days. The source is available for purchase at 12x the monthly
operations fee.

## How to get in touch

- Configure and order an agent without a call: https://blvkware.dev/hire/
- Browse what each agent role owns: https://blvkware.dev/agents/
- Book a call: https://cal.com/blvkware/30min (30 minutes, for a Deputy or custom
  work) or https://cal.com/blvkware/15min (15 minutes, for a question about an
  Operator).
- Or email russ@blvkware.dev. Replies come from the person who does the work,
  usually the same day.

## Free tools

All three run entirely in the visitor's browser. No account, no sign-up, no
payment, no server. They exist as the work sample in place of client case studies.

- [AUGUR](https://blvkware.dev/augur/) finds the work. Give it a company's public
  website and it reads the live page, works out which jobs are quietly costing
  that business the most -- unstaffed, done after hours, or done by somebody who
  should be doing something else -- and names the agent worth hiring for each,
  priced from the published catalog rather than estimated.
- [SCRY](https://blvkware.dev/scry/) designs the agent. Describe how a business
  actually operates and it works out which agent is worth hiring first, exactly
  what it has to be able to do, which existing systems it must operate, what is
  ready on day one and what still needs a person -- then prices it and hands the
  finished design to checkout with every option already set.
- [SIGIL](https://blvkware.dev/sigil/) builds it. Given a paid order it writes
  the configuration that turns shared, tested machinery into one specific agent:
  the triage labels, the routing table, the chase cadence and the words it will
  use, followed by an honest account of what it finished and what was handed to a
  human. Opened without an order it is a free build-anything tool that generates
  a complete single-file web application from a description, runs it, audits it
  and repairs its own errors.

## Important caveats for anyone citing this site

- Every dollar figure produced by the free tools is a **projection modelled from
  public industry benchmarks**, never a measurement of a real business's finances.
- BlvkWare has **no client case studies and no client references**. This is stated
  openly on the site; the tools are offered as the evidence instead. The one
  long-form write-up, the Recovery OS build log, documents a system BlvkWare
  built from its own planning documents -- no client commissioned or paid for it,
  and the page says so.
- Tool output is AI-generated and is not financial, legal or engineering advice.

## Pages

- [Home](https://blvkware.dev/): the model, the two agent tiers, prices, tools, FAQ
- [Recovery OS build log](https://blvkware.dev/recovery-os/): a worked example of
  the larger engagement -- four ordinary business documents (a slide deck, a call
  script, a spreadsheet, a strategy memo) turned into an eight-stage operating
  system with 203 self-checks. Documents the six rules the software enforces, the
  three defects found before shipping, and carries the part-number identifier
  running live in the page so a reader can test it. Built by BlvkWare from its own
  planning documents; no client paid for it.
- [Hire an agent](https://blvkware.dev/hire/): the configurator. Pick a role, add
  components, choose monthly or annual, and the total is calculated on the page.
  Produces a written order that becomes the scope of record. No call required.
- [Agent catalog](https://blvkware.dev/agents/): every role, what each one owns,
  what comes with an agent regardless of tier, and the full capability price list.
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
- [How BlvkWare agents are controlled](https://blvkware.dev/how-agents-are-controlled/):
  the mechanics rather than the argument. Where credentials live (a permissioned
  file on the agent's own machine, never in the codebase, not separately
  encrypted at rest and stated as such), the two destinations data goes to (the
  customer's own vendors, and the model provider for reasoning only), that the
  agent runs with no model at all on a deterministic path and what that costs in
  escalations, the append-only log written before each side effect, what can and
  cannot be undone, the customer's own one-press stop, export on exit, and an
  explicit list of what the page does NOT claim (no SOC 2, no encryption at
  rest, and that the agent can be wrong).
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
- [Privacy policy](https://blvkware.dev/privacy/): no accounts, no analytics, no
  cookies, no tracking; tools keep data only in the visitor's own browser
- [Terms of service](https://blvkware.dev/terms/)
"""
    # Counts are rendered here rather than typed into the string, so a catalog
    # addition cannot leave the published summary quietly wrong.
    llms = llms.replace("{n_roles}", str(len(catalog.ROLES)))
    llms = llms.replace("{n_caps}", str(len(catalog.CAPABILITIES)))
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
            tier = catalog.TIERS[r["minTier"]]
            out.append('<div class="card">')
            out.append('<h3>%s</h3>' % _esc(r["name"]))
            out.append('<div class="oneline">%s</div>' % _esc(r["oneLine"]))
            out.append('<p>%s</p>' % _esc(r["problem"]))
            out.append('<ul class="owns">')
            for cid in r["core"]:
                c = catalog.CAP_BY_ID[cid]
                out.append('<li><b>%s</b> — %s</li>' % (_esc(c["name"]), _esc(c["blurb"])))
            out.append('</ul>')
            if r["suggested"]:
                names = ", ".join(catalog.CAP_BY_ID[c]["name"] for c in r["suggested"])
                out.append('<p class="also">Usually added: %s</p>' % _esc(names))
            out.append('<div class="foot-note">From <b>%s</b> build · <b>%s</b>/month · live in %s</div>'
                       % (_money(tier["build"]), _money(tier["ops"]), _esc(tier["days"])))
            out.append('<a class="card-cta" href="/hire/">See the price &rarr;</a>')
            out.append('</div>')
        out.append('</div>')
    return "\n".join(out)


def catalog_components_html():
    """Every capability, grouped, with the price the configurator will charge."""
    out = []
    for group in catalog.CAP_GROUPS:
        caps = [c for c in catalog.CAPABILITIES if c["group"] == group]
        out.append('<tr class="grouprow"><td colspan="3">%s</td></tr>' % _esc(group))
        for c in sorted(caps, key=lambda x: -x["price"]):
            note = ""
            if c["gate"]:
                note = ' <span class="gate">%s</span>' % _esc(catalog.GATES[c["gate"]]["short"])
            ops = ""
            if c["ops"]:
                ops = '<br><span class="ops">+%s/mo</span>' % _money(c["ops"])
            out.append('<tr><td><b>%s</b></td><td>%s%s</td><td class="num">%s%s</td></tr>'
                       % (_esc(c["name"]), _esc(c["blurb"]), note, _money(c["price"]), ops))
    return "\n".join(out)


def catalog_itemlist_json():
    """The catalog page's ItemList, generated so the structured data and the
    visible cards cannot describe different products."""
    import json
    items = []
    for n, r in enumerate(catalog.ROLES, 1):
        tier = catalog.TIERS[r["minTier"]]
        owns = "; ".join(catalog.CAP_BY_ID[c]["name"] for c in r["core"])
        items.append({
            "@type": "ListItem",
            "position": n,
            "name": r["name"],
            "description": "%s. Owns: %s. From %s build plus %s/month, live in %s."
                           % (r["problem"], owns, _money(tier["build"]),
                              _money(tier["ops"]), tier["days"]),
        })
    node = {
        "@type": "ItemList",
        "name": "BlvkWare Agent Catalog",
        "description": "Named agent roles a small business can hire. Each has a "
                       "fixed scope, a flat build price and a required monthly "
                       "Agent Operations fee. Scope and price are configured at "
                       "https://blvkware.dev/hire/ without a sales call.",
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
                        ("/*FORGE_JS*/", "forge.js")):
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
        chips.append('<a class="role-chip more" href="/hire/"><b>Pick one and see the price &rarr;</b>'
                     '<span>%d capabilities to pick from</span></a>' % len(catalog.CAPABILITIES))
        html = html.replace("<!--CATALOG_STRIP-->", "\n                    ".join(chips))
    if "<!--CATALOG_ITEMLIST-->" in html:
        html = html.replace("<!--CATALOG_ITEMLIST-->", catalog_itemlist_json())
    if "<!--CATALOG_ROLES-->" in html:
        html = html.replace("<!--CATALOG_ROLES-->", catalog_roles_html())
    if "<!--CATALOG_COMPONENTS-->" in html:
        html = html.replace("<!--CATALOG_COMPONENTS-->", catalog_components_html())

    for token, value in (
        ("{{TIER1_BUILD}}", _money(catalog.TIERS[1]["build"])),
        ("{{TIER1_OPS}}", _money(catalog.TIERS[1]["ops"])),
        ("{{TIER2_BUILD}}", _money(catalog.TIERS[2]["build"])),
        ("{{TIER2_OPS}}", _money(catalog.TIERS[2]["ops"])),
        ("{{TRIAL}}", _money(catalog.TRIAL)),
        ("{{N_ROLES}}", str(len(catalog.ROLES))),
        ("{{N_CAPS}}", str(len(catalog.CAPABILITIES))),
    ):
        html = html.replace(token, value)

    leftover = re.findall(r"\{\{[A-Z0-9_]+\}\}", html)
    if leftover:
        print("ABORTED: %s has unresolved tokens: %s" % (name, ", ".join(sorted(set(leftover)))))
        raise SystemExit(1)
    return html


def main():
    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)

    # A catalog edit that silently reprices every Tier I role as a Tier II is a
    # business bug that looks like nothing in a diff. It blocks the build.
    import thresholds
    if thresholds.main() != 0:
        print("ABORTED: tier thresholds are wrong - see above")
        return 1

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
        site_html = compile_catalog(site_html, "site/index.html")
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
        html = compile_catalog(html, "site/" + src)
        d = os.path.join(OUT_DIR, slug)
        if not os.path.isdir(d):
            os.makedirs(d)
        with io.open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        print("Built docs/%s/index.html (%.1f KB)" % (slug, len(html.encode("utf-8")) / 1024.0))

    # The fulfilment console is built OUTSIDE docs/ on purpose. It carries the
    # template library, the tier-derivation reasoning and the run-cost lines —
    # none of which belong on a public static host with no authentication.
    ops_src = os.path.join(ROOT, "ops", "console.html")
    if os.path.isfile(ops_src):
        with io.open(ops_src, encoding="utf-8") as fh:
            ops_html = fh.read()
        ops_html = compile_catalog(ops_html, "ops/console.html")
        ops_out = os.path.join(ROOT, "ops", "console.built.html")
        with io.open(ops_out, "w", encoding="utf-8") as fh:
            fh.write(ops_html)
        print("Built ops/console.built.html (%.1f KB)  internal - not published"
              % (len(ops_html.encode("utf-8")) / 1024.0))

    # The checkout function prices server-side from the same catalog and the
    # same engine as the page. Emitting them here rather than letting api/ keep
    # its own copies is what stops the amount a buyer is charged from drifting
    # away from the amount they were shown.
    api_dir = os.path.join(ROOT, "api")
    if os.path.isdir(api_dir):
        with io.open(os.path.join(api_dir, "_catalog.json"), "w",
                     encoding="utf-8") as fh:
            fh.write(catalog.as_json())
        with io.open(os.path.join(ROOT, "dev", "engine.js"), encoding="utf-8") as fh:
            engine = fh.read()
        with io.open(os.path.join(api_dir, "_engine.js"), "w",
                     encoding="utf-8") as fh:
            fh.write("/* GENERATED from dev/engine.js by dev/build-static.py.\n"
                     "   Do not edit: rebuild instead. */\n" + engine)
        print("Built api/_catalog.json and api/_engine.js  for the checkout function")

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
