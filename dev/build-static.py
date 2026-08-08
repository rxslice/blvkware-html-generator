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

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.html")
OUT_DIR = os.path.join(ROOT, "docs")
OUT = os.path.join(OUT_DIR, "index.html")

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
            { role: "system", content: SYSTEM },
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

  /* a way back into the key dialog once a key is set */
  document.addEventListener("DOMContentLoaded", function () {
    var foot = document.querySelector(".rail-foot");
    if (!foot) return;
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


def main():
    if not os.path.isfile(APP):
        print("ERROR: app.html not found")
        return 1

    with io.open(APP, encoding="utf-8") as fh:
        src = fh.read()

    # Refuse to publish if a developer key ever leaked into the source.
    leak = re.search(r"(AIza[0-9A-Za-z_\-]{30,}|sk-or-v1-[0-9a-f]{40,}|gsk_[0-9A-Za-z]{40,}|sk-ant-[0-9A-Za-z\-]{40,})", src)
    if leak:
        print("ABORTED: what looks like a live API key is present in app.html.")
        print("         Remove it before building a public bundle.")
        return 1

    idx = src.index("<style>")
    body = src[idx:]

    m = re.search(r'<symbol id="i-blvkmark"[^>]*>([\s\S]*?)</symbol>', src)
    icon = ""
    if m:
        import urllib.parse
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
               '<rect width="64" height="64" rx="14" fill="#0b0806"/>' + m.group(1) + "</svg>")
        icon = "data:image/svg+xml," + urllib.parse.quote(" ".join(svg.split()), safe="")

    close_script = "<" + "/script>"
    desc = ("Describe a website, game, tool or app in plain language and get a complete, "
            "working, single-file HTML page back — streamed live, with a runtime console "
            "and a quality audit.")

    head = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>BlvkWare AI HTML Generator</title>\n"
        "<meta name=\"description\" content=\"" + desc + "\">\n"
        "<meta property=\"og:title\" content=\"BlvkWare AI HTML Generator\">\n"
        "<meta property=\"og:description\" content=\"" + desc + "\">\n"
        "<meta property=\"og:type\" content=\"website\">\n"
        "<meta name=\"twitter:card\" content=\"summary\">\n"
        + ('<link rel="icon" href="%s">\n' % icon if icon else "")
        + "<script>" + SHIM + close_script + "\n"
        "</head>\n<body>\n"
    )

    page = head + body + "\n</body>\n</html>\n"

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(page)
    # Pages would otherwise run the output through Jekyll.
    with io.open(os.path.join(OUT_DIR, ".nojekyll"), "w", encoding="utf-8") as fh:
        fh.write("")

    print("Built %s  (%.1f KB)" % (os.path.relpath(OUT, ROOT), len(page.encode("utf-8")) / 1024.0))
    print("  no developer keys embedded - visitors supply their own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
