#!/usr/bin/env python3
"""
Local dev server for the BlvkWare AI HTML Generator — backed by a real LLM API.

    python dev/serve.py

Serves app.html at http://localhost:8777 with the `$meta` platform header stripped
and a real `root.generateText` implementation injected. Generation streams from a
live provider. There is no mock anywhere in this file.

PROVIDERS — set whichever key you have; the server auto-detects it, preferring
free providers in DETECT_ORDER.

  GEMINI_API_KEY        Google AI Studio    free, no credit card   [recommended]
  OPENROUTER_API_KEY    OpenRouter          free models, no card
  GROQ_API_KEY          Groq                free, very fast
  CEREBRAS_API_KEY      Cerebras            free, high throughput
  MISTRAL_API_KEY       Mistral             large free tier (opts into training)
  ANTHROPIC_API_KEY     Anthropic           paid
  ANTHROPIC_AUTH_TOKEN  Anthropic OAuth     paid

  GitHub Models is retired (410 as of Aug 2026) and is never auto-selected.

Keys are read from the environment or a `.env` file next to app.html.
Override the provider, model, or output cap explicitly:

    python dev/serve.py --provider openrouter --model cohere/north-mini-code:free
    python dev/serve.py --list

Stdlib only — nothing to install.
"""

import argparse
import http.server
import io
import json
import os
import re
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.html")

DEFAULT_MAX_TOKENS = 32000
MAX_TOKENS = DEFAULT_MAX_TOKENS
CLI_MAX_TOKENS = None  # set only by --max-tokens

# ---------------------------------------------------------------------------
# provider registry
#
# `wire` selects the request/response shape:
#   "openai"    -> POST {base}/chat/completions, SSE with choices[].delta.content
#   "anthropic" -> POST /v1/messages, SSE with content_block_delta/text_delta
#
# Model IDs verified against provider docs in August 2026. If a provider retires
# one, pass --model to override without touching this file.
# ---------------------------------------------------------------------------
PROVIDERS = {
    "gemini": {
        "label": "Google AI Studio (Gemini)",
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "wire": "openai",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        # gemini-3.5-flash is documented as the most intelligent for agentic/coding work
        "model": "gemini-3.5-flash",
        "max_tokens": 32000,
        "free": True,
    },
    "openrouter": {
        "label": "OpenRouter",
        "env": ["OPENROUTER_API_KEY"],
        "wire": "openai",
        "base": "https://openrouter.ai/api/v1",
        "model": "nvidia/nemotron-3-super-120b-a12b:free",
        "max_tokens": 32000,
        "free": True,
        "extra_headers": {"X-Title": "BlvkWare HTML Generator"},
    },
    "groq": {
        "label": "Groq",
        "env": ["GROQ_API_KEY"],
        "wire": "openai",
        "base": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 8000,
        "free": True,
    },
    "cerebras": {
        "label": "Cerebras",
        "env": ["CEREBRAS_API_KEY"],
        "wire": "openai",
        "base": "https://api.cerebras.ai/v1",
        "model": "llama-3.3-70b",
        "max_tokens": 8000,
        "free": True,
    },
    # Retired: as of Aug 2026 this endpoint answers 410
    # github_models_retirement_brownout. Kept so an existing GITHUB_TOKEN in the
    # environment is never auto-selected, and only usable via --provider github.
    "github": {
        "label": "GitHub Models (retired)",
        "env": ["GITHUB_MODELS_TOKEN"],
        "wire": "openai",
        "base": "https://models.github.ai/inference",
        "model": "openai/gpt-4o",
        "free": False,
        "retired": True,
    },
    "mistral": {
        "label": "Mistral",
        "env": ["MISTRAL_API_KEY"],
        "wire": "openai",
        "base": "https://api.mistral.ai/v1",
        "model": "mistral-large-latest",
        "max_tokens": 32000,
        "free": True,
    },
    "anthropic": {
        "label": "Anthropic",
        "env": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"],
        "wire": "anthropic",
        "base": "https://api.anthropic.com",
        "model": "claude-opus-5",
        "max_tokens": 32000,
        "free": False,
    },
}

# Order matters: first provider with a key present wins. Free + strongest first.
# `github` is deliberately excluded — the service is retired.
DETECT_ORDER = ["gemini", "openrouter", "anthropic", "groq", "cerebras", "mistral"]

SYSTEM_PROMPT = (
    "You are a world-class front-end engineer and product designer. "
    "You output complete, self-contained, single-file HTML documents and nothing else."
)

# Assistant prefill is unsupported on several current models (Claude Opus 5 returns a
# 400), so a continuation is never sent as a trailing assistant turn. The partial file
# goes back inside the user turn and the model is asked to continue from it.
CONTINUE_TEMPLATE = (
    "{instruction}\n\n"
    "You have already written the beginning of this file. Here it is, verbatim, "
    "between markers:\n\n"
    "<<<PARTIAL_FILE_START>>>\n{partial}\n<<<PARTIAL_FILE_END>>>\n\n"
    "Continue the file from exactly where it stops. Output ONLY the continuation — "
    "do not repeat any of the text above, do not restart the document, do not "
    "explain. Your first character must be the character that comes next."
)


# ---------------------------------------------------------------------------
# credentials / provider selection
# ---------------------------------------------------------------------------

def read_dotenv():
    path = os.path.join(ROOT, ".env")
    out = {}
    if not os.path.isfile(path):
        return out
    with io.open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


ENV = {}


def lookup(name):
    return os.environ.get(name) or ENV.get(name)


def detect_provider(forced, cli_key):
    """Return (provider_name, config, key) or (None, None, None)."""
    names = [forced] if forced else DETECT_ORDER
    for name in names:
        cfg = PROVIDERS.get(name)
        if not cfg:
            continue
        if forced and cli_key:
            return name, cfg, cli_key
        for var in cfg["env"]:
            key = lookup(var)
            if key:
                return name, cfg, key
    if forced and cli_key:
        return forced, PROVIDERS[forced], cli_key
    return None, None, None


PROVIDER = None
CFG = None
KEY = None
MODEL = None


# ---------------------------------------------------------------------------
# page assembly
# ---------------------------------------------------------------------------

# Same tokenizer rule as app.html applies to this shim: no HTML open-comment
# sequence and no literal script open/close tag inside this JS.
SHIM = r"""
(function () {
  window.root = {
    generateText: function (o) {
      var instruction = o.instruction || "";
      var startWith = o.startWith || "";
      var onChunk = o.onChunk;
      var ctrl = new AbortController();
      var generated = "";

      var sel = (window.__blvkProvider || {});
      var p = fetch("/api/generate", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          instruction: instruction, startWith: startWith,
          provider: sel.provider || "", model: sel.model || ""
        }),
        signal: ctrl.signal
      }).then(function (res) {
        if (!res.ok || !res.body) {
          return res.text().then(function (t) {
            throw new Error("Server error " + res.status + ": " + t.slice(0, 400));
          });
        }
        var reader = res.body.getReader();
        var dec = new TextDecoder();
        var buf = "";

        function pump() {
          return reader.read().then(function (r) {
            if (r.done) {
              if (buf.trim()) handleLine(buf);
              return { text: startWith + generated, generatedText: generated };
            }
            buf += dec.decode(r.value, { stream: true });
            var lines = buf.split("\n");
            buf = lines.pop();
            for (var i = 0; i < lines.length; i++) handleLine(lines[i]);
            return pump();
          });
        }

        function handleLine(line) {
          line = line.trim();
          if (!line) return;
          var msg;
          try { msg = JSON.parse(line); } catch (e) { return; }
          if (msg.error) throw new Error(msg.error);
          if (msg.meta || msg.note) {
            try {
              window.dispatchEvent(new CustomEvent("blvk:meta", { detail: msg }));
            } catch (e) {}
            return;
          }
          if (typeof msg.t === "string") {
            generated += msg.t;
            if (onChunk) {
              onChunk({ fullTextSoFar: startWith + generated, isFromStartWith: false });
            }
          }
        }

        return pump();
      });

      p.stop = function () { try { ctrl.abort(); } catch (e) {} };
      return p;
    }
  };
})();
"""


def favicon_from_mark(src):
    """Build a data-URI favicon from the brand symbol in app.html.

    Derived rather than duplicated, so the tab icon can never drift from the mark
    rendered in the rail.
    """
    m = re.search(r'<symbol id="i-blvkmark"[^>]*>([\s\S]*?)</symbol>', src)
    if not m:
        return ""
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
           '<rect width="64" height="64" rx="14" fill="#0b0806"/>'
           + m.group(1) + '</svg>')
    svg = " ".join(svg.split())
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


def build_page():
    with io.open(APP, encoding="utf-8") as fh:
        src = fh.read()
    idx = src.index("<style>")
    body = src[idx:]
    close_script = "<" + "/script>"
    icon = favicon_from_mark(src)
    head = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>BlvkWare AI HTML Generator</title>\n"
        + ('<link rel="icon" href="%s">\n' % icon if icon else "") +
        "<script>" + SHIM + close_script + "\n"
        "</head>\n<body>\n"
    )
    return (head + body + "\n</body>\n</html>\n").encode("utf-8")


# ---------------------------------------------------------------------------
# request builders
# ---------------------------------------------------------------------------

def user_content(instruction, start_with):
    if start_with:
        return CONTINUE_TEMPLATE.format(instruction=instruction, partial=start_with)
    return instruction


def build_request(instruction, start_with):
    """Return (urllib.Request, wire) for the active provider."""
    content = user_content(instruction, start_with)
    wire = CFG["wire"]

    if wire == "anthropic":
        url = CFG["base"] + "/v1/messages"
        payload = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "stream": True,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": content}],
        }
        headers = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if KEY.startswith("sk-ant-oat") or lookup("ANTHROPIC_AUTH_TOKEN") == KEY:
            headers["Authorization"] = "Bearer " + KEY
            headers["anthropic-beta"] = "oauth-2025-04-20"
        else:
            headers["x-api-key"] = KEY
    else:
        url = CFG["base"] + "/chat/completions"
        payload = {
            "model": MODEL,
            "max_tokens": MAX_TOKENS,
            "stream": True,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        }
        headers = {
            "content-type": "application/json",
            "Authorization": "Bearer " + KEY,
        }
        headers.update(CFG.get("extra_headers") or {})

    # Some providers sit behind a WAF that rejects urllib's default user-agent
    # outright (Groq answers Cloudflare 1010), so always send a real one.
    headers["User-Agent"] = "BlvkWare-HTMLGen/1.1"
    headers["Accept"] = "text/event-stream"

    return urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    ), wire


def extract_delta(wire, ev):
    """Pull the text delta out of one parsed SSE event, or None."""
    if wire == "anthropic":
        if ev.get("type") == "content_block_delta":
            d = ev.get("delta") or {}
            if d.get("type") == "text_delta":
                return d.get("text", "")
        return None

    choices = ev.get("choices") or []
    if not choices:
        return None
    delta = choices[0].get("delta") or {}
    txt = delta.get("content")
    # some providers stream a non-string content array
    if isinstance(txt, list):
        return "".join(
            p.get("text", "") for p in txt if isinstance(p, dict)
        )
    return txt if isinstance(txt, str) else None


RETRYABLE = (408, 409, 425, 429, 500, 502, 503, 504, 529)


def attempt_stream(cfg, key, model, instruction, start_with, write_line):
    """One provider attempt.

    Returns (ok, emitted_any, error_text, retryable). `emitted_any` matters: once
    bytes reach the client we can no longer silently switch providers, because the
    partial output is already on screen.
    """
    global CFG, KEY, MODEL
    CFG, KEY, MODEL = cfg, key, model
    emitted = False
    try:
        req, wire = build_request(instruction, start_with)
    except Exception as e:
        return False, False, "Could not build request: " + str(e), False

    try:
        resp = urllib.request.urlopen(req, timeout=900)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        return False, False, "%s %d: %s" % (cfg["label"], e.code, detail), e.code in RETRYABLE
    except Exception as e:
        return False, False, "%s unreachable: %s" % (cfg["label"], e), True

    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            try:
                ev = json.loads(data)
            except ValueError:
                continue

            if isinstance(ev, dict) and ev.get("error"):
                err = ev["error"]
                msg = err.get("message") if isinstance(err, dict) else str(err)
                return False, emitted, "%s: %s" % (cfg["label"], msg or "stream error"), False

            piece = extract_delta(wire, ev)
            if piece:
                if not emitted:
                    emitted = True
                    write_line({"meta": {"provider": cfg["label"], "model": model}})
                write_line({"t": piece})

    if not emitted:
        return False, False, "%s returned no text" % cfg["label"], False
    return True, True, None, False


def available_providers():
    """[(name, cfg, key)] for every non-retired provider with a key present."""
    out = []
    for name in DETECT_ORDER:
        cfg = PROVIDERS[name]
        for var in cfg["env"]:
            key = lookup(var)
            if key:
                out.append((name, cfg, key))
                break
    return out


def stream_completion(instruction, start_with, write_line, prefer=None, model_override=None):
    global MAX_TOKENS
    """Stream with bounded retry, then fail over to another provider.

    Free tiers rate-limit aggressively, so a single 429 should not surface as a
    dead end when another key is sitting right there.
    """
    chain = available_providers()
    if prefer:
        chain.sort(key=lambda t: 0 if t[0] == prefer else 1)
    if not chain:
        write_line({"error": "No API key found. Put GEMINI_API_KEY=... in a .env "
                             "file next to app.html (free: aistudio.google.com/apikey)."})
        return

    last = None
    for idx, (name, cfg, key) in enumerate(chain):
        # A model override only applies to the provider it was meant for; after a
        # failover we use that provider's own default.
        model = model_override if (model_override and (not prefer or name == prefer)) \
            else cfg["model"]
        # An explicit --max-tokens always wins; otherwise take the provider's cap
        # fresh each time (never carry the previous provider's smaller limit over).
        MAX_TOKENS = CLI_MAX_TOKENS or cfg.get("max_tokens", DEFAULT_MAX_TOKENS)

        for attempt in range(3):
            ok, emitted, err, retryable = attempt_stream(
                cfg, key, model, instruction, start_with, write_line)
            if ok:
                return
            last = err
            if emitted:
                # Output already on the wire — the client keeps the partial and the
                # app's continuation pass takes over. Never restart underneath it.
                write_line({"error": err or "stream ended early"})
                return
            if not retryable:
                break
            time.sleep(1.5 * (2 ** attempt))

        if idx + 1 < len(chain):
            write_line({"note": "%s unavailable — trying %s" % (
                cfg["label"], chain[idx + 1][1]["label"])})

    write_line({"error": last or "All providers failed."})


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "BlvkWareDev/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s\n" % (fmt % args))

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html", "/app.html"):
            try:
                page = build_page()
            except Exception as e:
                self.send_error(500, "Could not build page: %s" % e)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(page)
        elif path in ("/api/status", "/api/providers"):
            avail = available_providers()
            info = json.dumps({
                "provider": PROVIDER, "model": MODEL, "ready": bool(avail),
                "providers": [
                    {"id": n, "label": c["label"], "model": c["model"], "free": c["free"]}
                    for n, c, _ in avail
                ],
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(info)))
            self.end_headers()
            self.wfile.write(info)
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/generate":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            self.send_error(400, "Bad JSON")
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        lock = threading.Lock()

        def write_line(obj):
            data = (json.dumps(obj) + "\n").encode("utf-8")
            with lock:
                self.wfile.write(("%X\r\n" % len(data)).encode("ascii"))
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()

        if True:
            try:
                stream_completion(
                    body.get("instruction", ""), body.get("startWith", ""), write_line,
                    prefer=body.get("provider") or None,
                    model_override=body.get("model") or None,
                )
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as e:
                try:
                    write_line({"error": "Proxy error: " + str(e)})
                except Exception:
                    return

        try:
            with lock:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
        except Exception:
            pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    global ENV, PROVIDER, CFG, KEY, MODEL, MAX_TOKENS, CLI_MAX_TOKENS

    ap = argparse.ArgumentParser(description="Run the generator against a real LLM API.")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--key", help="API key (use with --provider)")
    ap.add_argument("--provider", choices=sorted(PROVIDERS), help="force a provider")
    ap.add_argument("--model", help="override the model id")
    ap.add_argument("--max-tokens", type=int, dest="max_tokens", help="override max output tokens")
    ap.add_argument("--list", action="store_true", help="list providers and exit")
    args = ap.parse_args()

    if args.list:
        print("\n  provider     free  default model                 env var")
        print("  " + "-" * 68)
        for n in DETECT_ORDER:
            c = PROVIDERS[n]
            print("  %-12s %-5s %-29s %s" % (
                n, "yes" if c["free"] else "no", c["model"], c["env"][0]))
        print("")
        return 0

    ENV = read_dotenv()
    PROVIDER, CFG, KEY = detect_provider(args.provider, args.key)
    MODEL = args.model or (CFG["model"] if CFG else None)
    CLI_MAX_TOKENS = args.max_tokens
    if CFG:
        MAX_TOKENS = CLI_MAX_TOKENS or CFG.get("max_tokens", DEFAULT_MAX_TOKENS)

    if not os.path.isfile(APP):
        print("ERROR: app.html not found at " + APP)
        return 1

    print("")
    print("  BlvkWare AI HTML Generator - local dev server")
    print("  http://localhost:%d/" % args.port)
    if KEY:
        print("  provider: %s" % CFG["label"])
        print("  model:    %s" % MODEL)
        print("  max out:  %d tokens" % MAX_TOKENS)
    else:
        print("  provider: NONE - no API key found.")
        print("")
        print("  Free options (no credit card):")
        print("    Google AI Studio  https://aistudio.google.com/apikey   -> GEMINI_API_KEY")
        print("    OpenRouter        https://openrouter.ai/keys           -> OPENROUTER_API_KEY")
        print("    Groq              https://console.groq.com/keys        -> GROQ_API_KEY")
        print("")
        print("  Put one in a .env file next to app.html, then restart.")
        print("  `python dev/serve.py --list` shows every supported provider.")
    print("  Ctrl-C to stop.")
    print("")

    try:
        Server(("127.0.0.1", args.port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
