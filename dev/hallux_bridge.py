"""
The HALLUX bridge.

Named `hallux_bridge` rather than `hallux` on purpose: `dev/` is on
`sys.path` when the build runs, so a module called `hallux.py` in here
shadows the HALLUX package and this file ends up importing from itself.

HALLUX is a separate repository with its own price list, its own namespace
coverage and its own machine-readable surface. This module is the only place
the site knows about any of it, and it exists to enforce one rule the deploy
notes are explicit about:

    Every price in the agent catalog and on the human pricing page must match,
    byte for byte, or an agent quotes one number and gets billed another.

The mechanism is the same one the agent catalog already uses. The HALLUX page
contains no prices. It contains tokens, and this fills them from HALLUX's
`payment.py`. A stale price is then not something to notice in review: it is
impossible, because there is no number in the page to go stale.

`check_published_prices` covers the other direction: it asserts that the
rendered page and the generated agent catalog carry exactly the figures in
`payment.py`. It reads rendered output rather than source, because that is
where the last drift hunt found most of them.

It also builds the specification page, because the HALLUX page, llms.txt and
the catalog all link to it, and publishing a link without publishing the page
is the same failure as an aspirational catalog entry.

HALLUX is optional. A checkout of this repository without it must still be
able to publish the site, so everything here degrades to a warning.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

#: Where to look for the HALLUX checkout, in order. Beside this repo first,
#: which is how the workspace is laid out.
_CANDIDATES = (
    os.environ.get("HALLUX_PATH", ""),
    os.path.join(os.path.dirname(ROOT), "hallux"),
    os.path.join(ROOT, "..", "hallux"),
    os.path.join(ROOT, "vendor", "hallux"),
)


def locate():
    """Absolute path to a usable HALLUX checkout, or None."""
    for candidate in _CANDIDATES:
        if not candidate:
            continue
        path = os.path.abspath(candidate)
        if os.path.isfile(os.path.join(path, "hallux", "payment.py")):
            return path
    return None


def _load(path):
    """Import HALLUX's own modules rather than reimplementing anything.

    Importing across repositories is deliberate. The alternative is a copy of
    the price list in this repo, which is the exact failure this module
    exists to prevent.
    """
    if path not in sys.path:
        sys.path.insert(0, path)
    from hallux import authorities, payment  # noqa: E402

    return payment, authorities


def _money(value):
    """Render a price the way the rest of the site renders one."""
    text = str(value).strip()
    prefix = ""
    if text.lower().startswith("from "):
        prefix, text = "from ", text[5:].strip()
    try:
        return "%s$%s" % (prefix, "{:,}".format(int(text)))
    except ValueError:
        return "%s$%s" % (prefix, text)


#: The one place the site names HALLUX's endpoint. The page probe, the agent
#: catalog and llms.txt all read this, because three independently configured
#: URLs can reach three different conclusions about whether the service is
#: live, and the catalog would then say one thing while the page said another.
#:
#: This is the Hugging Face Space. `api.blvkware.dev` needs a custom domain,
#: which Hugging Face only offers on PRO; when that exists, change this one
#: value. The Space keeps answering at its own address afterwards, so anything
#: that cached this URL keeps working.
API_BASE = os.environ.get("HALLUX_API_BASE", "https://aimoneybags-hallux.hf.space")

#: Cached so the build does not probe the endpoint once per page.
_LIVE = {}


def endpoint_live(api_base=None):
    """Whether anything is actually answering. Returns (bool, detail).

    Delegates to HALLUX's own probe so the site and the catalog cannot reach
    different conclusions about the same endpoint. Without this, the page
    prints a curl command that fails, which is the aspirational-catalog
    failure wearing prose.
    """
    api_base = api_base or API_BASE
    if api_base in _LIVE:
        return _LIVE[api_base]
    path = locate()
    if path is None:
        _LIVE[api_base] = (False, "hallux checkout not found")
        return _LIVE[api_base]
    if path not in sys.path:
        sys.path.insert(0, path)
    sys.path.insert(0, os.path.join(path, "dev"))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hallux_build_surface", os.path.join(path, "dev", "build-surface.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LIVE[api_base] = module.endpoint_answers(api_base)
    except Exception as error:
        _LIVE[api_base] = (False, "probe failed: %s" % error)
    return _LIVE[api_base]


#: Shown on the page while nothing is serving the API. Deliberately loud and
#: deliberately above the curl command it replaces.
_NOT_DEPLOYED = (
    '<div class="notice"><strong>The public endpoint is not open yet.</strong> '
    "The service is built and tested, and everything below describes what it "
    "does. Until an endpoint is answering it is listed under "
    "<code>roadmap</code> in the agent catalog rather than as a capability, "
    "so an agent reading that catalog will not try to call it.</div>"
    # An earlier version ended "Run it yourself from the source in the
    # meantime." The source is not published anywhere, so that sentence was a
    # promise with nothing behind it: the same failure as a catalog entry that
    # 404s, in prose.
)

_DEPLOYED_INTRO = "<p>No account, no key, no signup. One command:</p>"


def _try_response(deployed):
    """The response shown under "Try it now", as the endpoint really gives it.

    Fetched from the live endpoint at build time rather than written into the
    page. The first version showed the specification's illustrative answer --
    a phantom with 412 attestations from three model families -- under a
    heading telling the reader to try the command. Anyone who did got
    `absent`, because the production ledger is new. Evidence a reader cannot
    reproduce is fabricated evidence, whatever the intent. Rendering what the
    endpoint actually returns makes the example true by construction, and it
    updates itself the day the ledger records this name for real.

    Volatile fields (timestamps) are dropped so a rebuild does not churn the
    page for no reason.
    """
    import html
    import json
    import urllib.request

    if not deployed:
        return (
            "<p>The public endpoint will answer this once it is open.</p>"
        )
    url = API_BASE.rstrip("/") + "/hallux/v1/check/pkg.pypi/requests-oauth2-helper"
    request = urllib.request.Request(url, headers={"User-Agent": "blvkware-site-build"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    body.pop("checkedAt", None)
    (body.get("evidence") or {}).pop("registryCheckedAt", None)
    text = html.escape(json.dumps(body, indent=2))
    # The same two highlights the illustration uses: the verdict, and the
    # name to use instead.
    verdict = html.escape(json.dumps(body.get("verdict")))
    text = text.replace(
        "&quot;verdict&quot;: " + verdict,
        '&quot;verdict&quot;: <span class="s">' + verdict + "</span>", 1)
    if body.get("successor"):
        successor = html.escape(json.dumps(body["successor"]))
        text = text.replace(
            "&quot;successor&quot;: " + successor,
            '&quot;successor&quot;: <span class="c">' + successor + "</span>", 1)
    return "<pre><code>%s</code></pre>" % text


def tokens():
    """The `{{HALLUX_*}}` substitutions, or None when HALLUX is absent.

    Every value here is read from HALLUX at build time. Nothing in this
    function may be a literal price.
    """
    path = locate()
    if path is None:
        return None
    payment, authorities = _load(path)
    # Named apart from `namespaces` on purpose: an earlier version called both
    # of these `live`, the namespace list overwrote the probe result, and the
    # not-deployed notice silently never rendered because a non-empty list is
    # truthy. A shadowed name that happens to be truthy fails quietly.
    deployed, _detail = endpoint_live()

    by_id = payment.TIERS_BY_ID
    namespaces = list(authorities.supported())
    pricing = payment.catalog_pricing()

    return {
        "{{HALLUX_FREE_DAILY}}": "{:,}".format(payment.FREE_DAILY_IDENTIFIERS),
        "{{HALLUX_PRICE_PER_IDENTIFIER}}": "$%s" % payment.PRICE_PER_IDENTIFIER_USD,
        "{{HALLUX_WATCH_MONTH}}": "$%s" % payment.PRICE_PER_WATCH_MONTH_USD,
        "{{HALLUX_TEAM_MONTH}}": _money(by_id[payment.TIER_TEAM].monthly_usd),
        "{{HALLUX_TEAM_YEAR}}": _money(by_id[payment.TIER_TEAM].annual_usd),
        "{{HALLUX_FEED_MONTH}}": _money(by_id[payment.TIER_FEED].monthly_usd),
        "{{HALLUX_FEED_YEAR}}": _money(by_id[payment.TIER_FEED].annual_usd),
        "{{HALLUX_EMBEDDED_FROM}}": _money(by_id[payment.TIER_EMBEDDED].monthly_usd),
        "{{HALLUX_CAP_IDENTIFIERS}}": "{:,}".format(
            pricing["cap"]["identifiersPerMonth"]
        ),
        "{{HALLUX_TEAM_WATCHES}}": str(by_id[payment.TIER_TEAM].included_watches),
        "{{HALLUX_NAMESPACES}}": ", ".join(namespaces),
        "{{HALLUX_NAMESPACE_COUNT}}": str(len(namespaces)),
        "{{HALLUX_NEUTRALITY}}": payment.PRICE_NOTES["neutrality"],
        # The example command on the page. It was hard-coded to
        # api.blvkware.dev, which is not the host serving it, so the moment
        # the not-deployed notice came down the page would have shown a
        # "Try it now" command that fails. One base URL, everywhere.
        "{{HALLUX_API_BASE}}": API_BASE.rstrip("/") + "/hallux/v1",
        "{{HALLUX_TRY_RESPONSE}}": _try_response(deployed),
        "{{HALLUX_STATUS_NOTICE}}": "" if deployed else _NOT_DEPLOYED,
        # The heading was the most prominent untruth on the page: a section
        # called "Try it now" above a command that cannot work.
        "{{HALLUX_TRY_HEADING}}": "Try it now" if deployed else "What it answers",
        "{{HALLUX_TRY_INTRO}}": _DEPLOYED_INTRO if deployed else (
            "<p>Once deployed, checking a name is one command. "
            "Today this is what it will answer, not what it does answer:</p>"
        ),
    }


def check_published_prices(pages, out_dir=None):
    """Assert the published HALLUX prices are the ones HALLUX charges.

    Returns `(problems, notes)`. A problem stops the build; a note is
    something the operator should read but which is not wrong. They are
    separate return values rather than a prefix on a string, because a caller
    deciding whether to abort by looking for the word "note:" is a caller one
    rewording away from shipping a broken catalog.

    This is a positive assertion, and that is the whole design. The obvious
    check is the negative one: scan every page for a hand-typed HALLUX price.
    It was written that way first and it does not work, because BlvkWare sells
    two things. Agent Operations is a monthly fee too, agent components are
    priced in the same range, and a numeric scan cannot tell a stale HALLUX
    figure from a perfectly correct agent one. It produced seven false
    positives on the first run and would have been switched off within a week.

    What actually has to be true is narrower and checkable: the rendered
    HALLUX page and the generated agent catalog both carry exactly the numbers
    in `hallux/payment.py`. A positive assertion about a page we control
    cannot false-positive on a page we do not.

    Checked against rendered output rather than source, because the last time
    prices drifted on this site most of them were not in the HTML at all.
    """
    path = locate()
    if path is None:
        return [], []
    payment, _ = _load(path)

    problems = []
    notes = []
    page = pages.get("hallux")
    if page is None:
        # Not an error on its own: a partial build may not have reached it.
        return [], []

    text = re.sub(r"<[^>]+>", " ", page)
    text = re.sub(r"\s+", " ", text)

    required = {
        "per identifier": "$" + payment.PRICE_PER_IDENTIFIER_USD,
        "per watch": "$" + payment.PRICE_PER_WATCH_MONTH_USD,
        "Team monthly": _money(payment.TIERS_BY_ID[payment.TIER_TEAM].monthly_usd),
        "Team annual": _money(payment.TIERS_BY_ID[payment.TIER_TEAM].annual_usd),
        "Feed monthly": _money(payment.TIERS_BY_ID[payment.TIER_FEED].monthly_usd),
        "Feed annual": _money(payment.TIERS_BY_ID[payment.TIER_FEED].annual_usd),
    }
    for label, value in required.items():
        if value not in text:
            problems.append(
                "the HALLUX page does not show the %s price %s. "
                "Add the matching {{HALLUX_*}} token." % (label, value)
            )

    # The other half of the rule: the machine surface has to agree with the
    # page a human reads, because an agent quoting one and being billed the
    # other is the failure this exists to prevent.
    if out_dir:
        catalog_path = os.path.join(out_dir, ".well-known", "ai-catalog.json")
        if os.path.isfile(catalog_path):
            import json

            with io.open(catalog_path, encoding="utf-8") as fh:
                catalog = json.load(fh)
            hallux_entries = [
                e for e in catalog.get("entries", []) if e.get("id") == "hallux"
            ]
            if not hallux_entries:
                # Not a failure: HALLUX is on the roadmap because nothing is
                # serving it, and a roadmap entry carries no prices to check.
                # Worth saying out loud, because a check that silently stops
                # checking is worse than one that fails.
                notes.append(
                    "the catalog has no live HALLUX entry to price-check; it "
                    "is on the roadmap until the endpoint answers. The page "
                    "was still checked."
                )
            for entry in hallux_entries:
                amount = str(entry.get("pricing", {}).get("amount", ""))
                if amount != payment.PRICE_PER_IDENTIFIER_USD:
                    problems.append(
                        "the agent catalog quotes $%s per identifier but "
                        "HALLUX charges $%s" % (amount, payment.PRICE_PER_IDENTIFIER_USD)
                    )
                cap = entry.get("pricing", {}).get("cap", {})
                if str(cap.get("thenMonthlyUsd", "")) != payment.PRICE_TEAM_MONTH_USD:
                    problems.append(
                        "the agent catalog quotes a cap price of $%s but the "
                        "Team price is $%s"
                        % (cap.get("thenMonthlyUsd"), payment.PRICE_TEAM_MONTH_USD)
                    )
    return problems, notes


def fill(html, name=""):
    """Replace every `{{HALLUX_*}}` token. Raises if one is left unresolved."""
    values = tokens()
    if values is None:
        # Leave the tokens in place so the unresolved-token check downstream
        # reports them rather than publishing a page that silently says
        # nothing about price.
        return html
    for token, value in values.items():
        html = html.replace(token, value)
    leftover = re.findall(r"\{\{HALLUX_[A-Z_]+\}\}", html)
    if leftover:
        raise ValueError(
            "%s has unresolved HALLUX tokens: %s"
            % (name or "page", ", ".join(sorted(set(leftover))))
        )
    return html


def publish_attestation_key(out_dir, api=None):
    """Publish the receipt verification key, but only if it is the right one.

    The key is copied to /.well-known/blvkware-attestation.pub, the URL the
    specification and the catalog name. Before copying, when the endpoint is
    live, its own reported key is compared with the file. Publishing a key
    that does not match the one signing live receipts would make every
    receipt fail verification for anyone who checked -- an audit artefact
    that proves the opposite of what it claims -- so a mismatch stops the
    build rather than publishing.

    Returns True when the key was published. The catalog's attestation-key
    entry is gated on this, so it can never name a key file that is absent.
    """
    import base64
    import json
    import shutil
    import urllib.request

    path = locate()
    if path is None:
        return False
    source = os.path.join(path, "deploy", "attestation.pub")
    if not os.path.isfile(source):
        return False

    deployed, _detail = endpoint_live(api)
    if deployed:
        base = (api or API_BASE).rstrip("/")
        request = urllib.request.Request(
            base + "/hallux/v1/health",
            headers={"User-Agent": "blvkware-site-build"},
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            health = json.load(response)
        live_key = (health.get("receipts") or {}).get("publicKey")
        if not live_key:
            raise RuntimeError(
                "the endpoint is live but reports no receipt key; refusing to "
                "publish a verification key for receipts it does not issue"
            )
        if path not in sys.path:
            sys.path.insert(0, path)
        from cryptography.hazmat.primitives import serialization

        with io.open(source, encoding="ascii") as fh:
            file_key = serialization.load_pem_public_key(
                fh.read().encode("ascii")
            ).public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        if base64.b64decode(live_key) != file_key:
            raise RuntimeError(
                "deploy/attestation.pub does not match the key the live "
                "endpoint signs with. Publishing it would make every receipt "
                "fail verification. Redeploy, or regenerate the .pub from the "
                "key the Space actually holds."
            )

    target_dir = os.path.join(out_dir, ".well-known")
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    shutil.copyfile(source, os.path.join(target_dir, "blvkware-attestation.pub"))
    return True


def build_surface(out_dir, site="https://blvkware.dev", api=None):
    """Publish HALLUX's agent catalog into the site.

    Runs HALLUX's own generator rather than reimplementing it, so the catalog
    the site publishes is the catalog HALLUX's tests check.

    The generator writes into a **scratch directory**, and exactly one file is
    copied out of it: `.well-known/ai-catalog.json`. That is deliberate, and
    it fixes a real defect. This used to point the generator straight at the
    site's `docs/`, and the generator also writes its own `llms.txt`,
    `pricing.md` and `openapi.json`. HALLUX's standalone `llms.txt` leads with
    verification and lists the agent practice under Optional; it was being
    written over the site's, and the site's only won because
    `write_seo_files()` happened to run afterwards. Reordering two lines in
    the build would have demoted the live revenue business on the production
    domain, silently. The other two files do not belong at the site root
    either: the OpenAPI document is served by the API itself.

    `--corpus-live` and `--key-published` are deliberately not passed. Their
    targets are files that have to actually be served first, and nothing in
    this catalog is aspirational.
    """
    import shutil
    import tempfile

    path = locate()
    if path is None:
        return None
    script = os.path.join(path, "dev", "build-surface.py")
    if not os.path.isfile(script):
        return None

    key_published = publish_attestation_key(out_dir, api)

    with tempfile.TemporaryDirectory(prefix="hallux-surface-") as scratch:
        command = [sys.executable, script, "--out", scratch, "--site", site,
                   "--api", api or API_BASE]
        if key_published:
            command.append("--key-published")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=path,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "hallux surface generation failed:\n%s"
                % (result.stderr or result.stdout)
            )
        source = os.path.join(scratch, ".well-known", "ai-catalog.json")
        target_dir = os.path.join(out_dir, ".well-known")
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)
        shutil.copyfile(source, os.path.join(target_dir, "ai-catalog.json"))
    return result.stdout.strip()


def llms_section(base="https://blvkware.dev"):
    """The HALLUX block for llms.txt, generated from live coverage.

    Returns an empty string when HALLUX is absent, so the site's llms.txt
    never advertises an endpoint this build could not confirm exists.
    """
    path = locate()
    if path is None:
        return ""
    payment, authorities = _load(path)
    live = ", ".join(authorities.supported())
    deployed, _detail = endpoint_live()
    # Named `deployment_note`, not `status`: this module already has a
    # module-level `status()` function, and a local called `status` that fails
    # to be assigned falls back to it silently. The first version of this
    # interpolated the function object into llms.txt.
    deployment_note = (
        ""
        if deployed
        else (
            "  **Not deployed yet.** Built and tested, but no endpoint is\n"
            "  answering. It is under `roadmap` in the agent catalog rather\n"
            "  than listed as a capability. Do not call it.\n"
        )
    )
    return (
        "\n## Verification infrastructure\n\n"
        "Separate from the agent practice above, and aimed at machines rather\n"
        "than at businesses.\n\n"
        "- [HALLUX](%s/hallux/): does this identifier actually exist? Package\n"
        "  names, module paths and DOIs, checked against their authoritative\n"
        "  registry before an agent installs, imports or cites. Returns\n"
        "  exists / deprecated / absent / phantom / squat / unknown.\n"
        "  A phantom is a name no registry has and models repeatedly invent.\n"
        "  A squat is a phantom somebody has since registered, which is a\n"
        "  supply-chain attack caught before the first install.\n"
        "  Live namespaces: %s.\n"
        "  Free tier: %s identifiers a day, no account, no key.\n"
        "%s"
        "- [Agent catalog](%s/.well-known/ai-catalog.json): machine-readable\n"
        "  index of every capability that answers, with prices and payment\n"
        "  rails. Capabilities listed under `roadmap` are not built.\n"
        "- [HALLUX specification](%s/docs/hallux-spec): verdict semantics,\n"
        "  namespaces, receipt format and corpus methodology.\n"
        % (
            base,
            live,
            "{:,}".format(payment.FREE_DAILY_IDENTIFIERS),
            deployment_note,
            base,
            base,
        )
    )


def status():
    """One line for the build log."""
    path = locate()
    if path is None:
        return "hallux: not found, surface and price check skipped"
    payment, authorities = _load(path)
    return "hallux: %s, %d live namespaces, %s per identifier" % (
        path,
        len(authorities.supported()),
        "$" + payment.PRICE_PER_IDENTIFIER_USD,
    )


def main():
    """Standalone check, for CI and for a quick look."""
    path = locate()
    if path is None:
        print("hallux checkout not found. Set HALLUX_PATH or place it beside "
              "this repository.")
        return 0
    print(status())
    values = tokens()
    width = max(len(k) for k in values)
    for token, value in sorted(values.items()):
        shown = value if len(value) < 60 else value[:57] + "..."
        print("  %-*s %s" % (width, token, shown))
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# the specification page
# ---------------------------------------------------------------------------

#: The page shell. Matches site/hallux.html so the spec does not read as a
#: different site, and carries no price of its own.
_SPEC_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HALLUX specification | BlvkWare</title>
<meta name="description" content="The HALLUX specification: verdict semantics, namespaces, the API, receipt format and the corpus methodology behind the phantom ledger.">
<link rel="canonical" href="https://blvkware.dev/docs/hallux-spec">
<meta name="robots" content="index, follow">
<meta property="og:title" content="HALLUX specification | BlvkWare">
<meta property="og:description" content="Verdict semantics, namespaces, receipt format and corpus methodology.">
<meta property="og:type" content="article">
<meta property="og:url" content="https://blvkware.dev/docs/hallux-spec">
<meta property="og:image" content="https://blvkware.dev/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" sizes="48x48" href="/assets/favicon-48.png">
<meta name="theme-color" content="#0A0908">
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&family=Fira+Code:wght@500&display=swap');
:root { --bg:#0A0908; --surface:#17140F; --accent:#D4F24A; --brass:#D9B65C;
  --ink:#F5F0E6; --ink-2:#A89D8B; --line:rgba(245,240,230,0.1);
  --font:'Manrope',system-ui,-apple-system,sans-serif; --mono:'Fira Code',ui-monospace,monospace; }
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--ink); font-family:var(--font); line-height:1.7; -webkit-font-smoothing:antialiased; }
.wrap { max-width:860px; margin:0 auto; padding:3rem 1.5rem 6rem; }
.top { display:flex; align-items:center; gap:0.8rem; margin-bottom:2.5rem; text-decoration:none; color:inherit; }
.mark { width:52px; height:52px; border-radius:14px; background:#060504; overflow:hidden; flex:none; }
.mark img { width:100%; height:100%; display:block; }
.wordmark { font-size:1.3rem; font-weight:800; letter-spacing:-0.01em; }
.wordmark span { color:var(--accent); }
.back { font-family:var(--mono); font-size:0.78rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--brass); display:inline-block; margin-bottom:2rem; text-decoration:none; }
.back:hover { text-decoration:underline; }
h1 { font-size:clamp(1.9rem,5vw,2.6rem); font-weight:800; letter-spacing:-0.02em; margin-bottom:0.8rem; line-height:1.2; }
h2 { font-size:1.35rem; font-weight:700; margin:3rem 0 1rem; letter-spacing:-0.01em; padding-top:1.5rem; border-top:1px solid var(--line); }
h3 { font-size:1.05rem; font-weight:700; margin:2rem 0 0.6rem; color:var(--brass); }
p { color:var(--ink-2); margin-bottom:1.1rem; }
ul, ol { margin:0 0 1.1rem 1.2rem; color:var(--ink-2); }
li { margin-bottom:0.5rem; }
strong { color:var(--ink); font-weight:700; }
a { color:var(--accent); text-decoration:none; }
a:hover { text-decoration:underline; }
code { font-family:var(--mono); font-size:0.87em; background:var(--surface); padding:0.15rem 0.4rem; border-radius:4px; color:var(--brass); }
pre { font-family:var(--mono); font-size:0.8rem; background:var(--surface); border:1px solid var(--line); border-radius:12px; padding:1.25rem; overflow-x:auto; margin:1.5rem 0; line-height:1.6; color:var(--ink-2); }
pre code { background:none; padding:0; color:inherit; font-size:inherit; }
hr { border:0; border-top:1px solid var(--line); margin:2.5rem 0; }
.tw { overflow-x:auto; margin:1.5rem 0; -webkit-overflow-scrolling:touch; }
table { border-collapse:collapse; width:100%; font-size:0.9rem; min-width:480px; }
th, td { text-align:left; padding:0.65rem 0.85rem; border-bottom:1px solid var(--line); vertical-align:top; }
th { font-family:var(--mono); font-size:0.7rem; letter-spacing:0.08em; text-transform:uppercase; color:var(--brass); font-weight:500; }
td { color:var(--ink-2); }
.foot { margin-top:4rem; padding-top:2rem; border-top:1px solid var(--line); font-size:0.9rem; color:var(--ink-2); }
.foot-links { display:flex; flex-wrap:wrap; gap:0.5rem 1.25rem; }
</style>
</head>
<body>
<div class="wrap">
<a class="top" href="/">
  <span class="mark"><img src="/assets/logo-192.png" alt="BlvkWare" width="192" height="192"></span>
  <span class="wordmark">BlvkWare<span>.</span></span>
</a>
<a class="back" href="/hallux/">&larr; HALLUX</a>
__BODY__
<div class="foot">
  <div class="foot-links">
    <a href="/">BlvkWare</a>
    <a href="/hallux/">HALLUX</a>
    <a href="/.well-known/ai-catalog.json">Agent catalog</a>
    <a href="/privacy/">Privacy</a>
    <a href="/terms/">Terms</a>
  </div>
</div>
</div>
</body>
</html>
"""


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text):
    """Inline markdown.

    Code spans are lifted out first so nothing inside one is treated as
    markup. Without that, a regex character class written in a code span
    becomes a link, which is exactly the trap the copy rules warn about.
    """
    spans = []

    def stash(match):
        spans.append(match.group(1))
        return "\x00%d\x00" % (len(spans) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = _escape(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    for index, span in enumerate(spans):
        text = text.replace("\x00%d\x00" % index, "<code>%s</code>" % _escape(span))
    return text


def markdown_to_html(source):
    """Render the subset of markdown the specification uses.

    Deliberately not a markdown library. The specification is one document in
    this repository's control and uses six constructs; adding a dependency to
    the site build so one page can render is a worse trade than a hundred
    lines that only have to handle what is actually written.
    """
    out = []
    lines = source.split("\n")
    index = 0
    total = len(lines)

    while index < total:
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            index += 1
            continue

        if stripped.startswith("```"):
            index += 1
            block = []
            while index < total and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            out.append("<pre><code>%s</code></pre>" % _escape("\n".join(block)))
            continue

        if re.match(r"^-{3,}$", stripped):
            out.append("<hr>")
            index += 1
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading:
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, _inline(heading.group(2)), level))
            index += 1
            continue

        # A table is a header row, a separator row, then body rows.
        if stripped.startswith("|") and index + 1 < total and re.match(
            r"^\|[\s:|-]+\|$", lines[index + 1].strip()
        ):
            header = [c.strip() for c in stripped.strip("|").split("|")]
            index += 2
            rows = []
            while index < total and lines[index].strip().startswith("|"):
                cells = lines[index].strip().strip("|").split("|")
                rows.append([c.strip() for c in cells])
                index += 1
            html = ['<div class="tw"><table><thead><tr>']
            html += ["<th>%s</th>" % _inline(c) for c in header]
            html.append("</tr></thead><tbody>")
            for row in rows:
                cells = "".join("<td>%s</td>" % _inline(c) for c in row)
                html.append("<tr>%s</tr>" % cells)
            html.append("</tbody></table></div>")
            out.append("".join(html))
            continue

        if re.match(r"^(\d+\.|[-*])\s+", stripped):
            ordered = bool(re.match(r"^\d+\.", stripped))
            tag = "ol" if ordered else "ul"
            items = []
            while index < total and re.match(r"^(\d+\.|[-*])\s+", lines[index].strip()):
                item = re.sub(r"^(\d+\.|[-*])\s+", "", lines[index].strip())
                index += 1
                # An indented continuation belongs to the item above it, not
                # to a new paragraph.
                while (
                    index < total
                    and lines[index].startswith("   ")
                    and lines[index].strip()
                    and not re.match(r"^(\d+\.|[-*])\s+", lines[index].strip())
                ):
                    item += " " + lines[index].strip()
                    index += 1
                items.append("<li>%s</li>" % _inline(item))
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag))
            continue

        paragraph = [stripped]
        index += 1
        while index < total and lines[index].strip() and not re.match(
            r"^(#{1,4}\s|```|\||-{3,}$|\d+\.\s|[-*]\s)", lines[index].strip()
        ):
            paragraph.append(lines[index].strip())
            index += 1
        out.append("<p>%s</p>" % _inline(" ".join(paragraph)))

    return "\n".join(out)


def build_spec_page(out_dir):
    """Publish HALLUX-SPEC.md at /docs/hallux-spec/.

    That URL is linked from the HALLUX page, from llms.txt and from the agent
    catalog. Publishing those links without publishing this page is the
    catalog-full-of-404s failure wearing a different hat.
    """
    path = locate()
    if path is None:
        return None
    source_path = os.path.join(path, "HALLUX-SPEC.md")
    if not os.path.isfile(source_path):
        return None
    with io.open(source_path, encoding="utf-8") as fh:
        source = fh.read()

    html = _SPEC_SHELL.replace("__BODY__", markdown_to_html(source))
    target_dir = os.path.join(out_dir, "docs", "hallux-spec")
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    target = os.path.join(target_dir, "index.html")
    with io.open(target, "w", encoding="utf-8") as fh:
        fh.write(html)
    return target


# ---------------------------------------------------------------------------
# the two pages the catalog points at
# ---------------------------------------------------------------------------


def _plain_page(title, description, canonical, heading, body, back="/hallux/",
                back_label="HALLUX"):
    """A minimal page in the site's type, for documents rather than marketing."""
    shell = _SPEC_SHELL
    shell = shell.replace(
        "<title>HALLUX specification | BlvkWare</title>",
        "<title>%s | BlvkWare</title>" % title,
    )
    shell = shell.replace(
        'content="The HALLUX specification: verdict semantics, namespaces, '
        'the API, receipt format and the corpus methodology behind the '
        'phantom ledger."',
        'content="%s"' % description,
    )
    shell = shell.replace(
        'content="HALLUX specification | BlvkWare"',
        'content="%s | BlvkWare"' % title,
    )
    shell = shell.replace(
        'content="Verdict semantics, namespaces, receipt format and corpus '
        'methodology."',
        'content="%s"' % description,
    )
    shell = shell.replace(
        'href="https://blvkware.dev/docs/hallux-spec"',
        'href="%s"' % canonical,
    )
    shell = shell.replace(
        'content="https://blvkware.dev/docs/hallux-spec"',
        'content="%s"' % canonical,
    )
    shell = shell.replace(
        '<a class="back" href="/hallux/">&larr; HALLUX</a>',
        '<a class="back" href="%s">&larr; %s</a>' % (back, back_label),
    )
    return shell.replace("__BODY__", "<h1>%s</h1>\n%s" % (heading, body))


def build_licence_page(out_dir):
    """Publish the Business Source Licence at /legal/bsl-1.1.

    The catalog names this URL as the licence for the HALLUX entry, so it has
    to resolve. Rendered from the LICENSE file in the HALLUX repository rather
    than retyped, because a licence that differs between the repository and
    the website is worse than one that is only in the repository.
    """
    path = locate()
    if path is None:
        return None
    source_path = os.path.join(path, "LICENSE")
    if not os.path.isfile(source_path):
        return None
    with io.open(source_path, encoding="utf-8") as fh:
        text = fh.read()

    body = (
        "<p>This is the licence referenced by the HALLUX entry in the "
        '<a href="/.well-known/ai-catalog.json">agent catalog</a>. It is '
        "reproduced verbatim from the LICENSE file in the source repository; "
        "that file is the operative copy.</p>"
        "<pre><code>%s</code></pre>" % _escape(text)
    )
    return _write_page(
        out_dir,
        ("legal", "bsl-1.1"),
        _plain_page(
            "HALLUX licence",
            "The Business Source License 1.1 under which HALLUX is published, "
            "converting to Apache 2.0 on 2030-01-01.",
            "https://blvkware.dev/legal/bsl-1.1",
            "HALLUX licence",
            body,
        ),
    )


def build_limits_page(out_dir):
    """Publish the rate limits at /docs/limits.

    Generated from HALLUX's own constants. A limits page that says something
    different from what the server enforces is worse than no limits page: an
    agent reads this to decide how to pace itself.
    """
    path = locate()
    if path is None:
        return None
    payment, authorities = _load(path)
    sys.path.insert(0, path) if path not in sys.path else None
    from hallux.engine import MAX_BATCH  # noqa: E402

    rows = [
        ("Identifiers per day, open tier", "{:,}".format(payment.FREE_DAILY_IDENTIFIERS)),
        ("Identifiers per batch request", str(MAX_BATCH)),
        ("Identifiers per month before the metered cap",
         "{:,}".format(payment.METERED_CAP_IDENTIFIERS)),
        ("Watched identifiers per request", str(MAX_BATCH)),
        ("Authentication on the open tier", "none"),
    ]
    table = ['<div class="tw"><table><thead><tr><th>Limit</th><th>Value</th>'
             "</tr></thead><tbody>"]
    for label, value in rows:
        table.append("<tr><td>%s</td><td><code>%s</code></td></tr>"
                     % (_escape(label), _escape(value)))
    table.append("</tbody></table></div>")

    body = (
        "<p>These are the limits the service enforces. They are generated "
        "from the same constants the server runs on, so this page cannot "
        "describe a limit that is not the real one.</p>"
        + "".join(table)
        + "<h2>How limits are reported</h2>"
        "<p>Every response carries <code>RateLimit-Limit</code>, "
        "<code>RateLimit-Remaining</code> and <code>RateLimit-Reset</code>. "
        "When the open allowance is spent the response is "
        "<code>402 Payment Required</code>, and its body names the price, the "
        "settlement rails and the flat tier that would remove the meter.</p>"
        "<h2>Batching</h2>"
        "<p>A batch is charged and served whole. Partially serving a batch and "
        "charging for the part served would make an agent's behaviour depend "
        "on where in its dependency list it ran out, which is a worse failure "
        "than a clean refusal.</p>"
        "<h2>Abuse</h2>"
        "<p>The open tier is generous on purpose and is expected to be "
        "abused. It is rate limited by client at the edge and some loss is "
        "accepted; the free tier is the advertisement. Clients are identified "
        "by a salted hash of their address, never by the address itself.</p>"
        '<p>Prices and tiers are at <a href="/hallux/">/hallux/</a>, and in '
        "machine-readable form in the "
        '<a href="/.well-known/ai-catalog.json">agent catalog</a>.</p>'
    )
    return _write_page(
        out_dir,
        ("docs", "limits"),
        _plain_page(
            "HALLUX rate limits",
            "The rate limits HALLUX enforces, generated from the constants "
            "the server runs on.",
            "https://blvkware.dev/docs/limits",
            "Rate limits",
            body,
        ),
    )


def _write_page(out_dir, parts, html):
    target_dir = os.path.join(out_dir, *parts)
    if not os.path.isdir(target_dir):
        os.makedirs(target_dir)
    target = os.path.join(target_dir, "index.html")
    with io.open(target, "w", encoding="utf-8") as fh:
        fh.write(html)
    return target
