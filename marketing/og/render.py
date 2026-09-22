#!/usr/bin/env python3
"""
Render a social card (og:image) for every page of blvkware.dev.

    python marketing/og/render.py          # after dev/build-static.py
    python dev/build-static.py             # again, to point pages at them

Writes docs/assets/og/<slug>.png at 1200x630. The build points each page's
og:image and twitter:image at its card when one exists, and at the generic
card otherwise, so a page never names an image that is not there.

Product pages get a designed card with a real panel: the file tree of a
real kit, HALLUX's live answer for a name models invent, pkgguard's actual
output for the same names. Every other page gets an article card built from
its own og:title and og:description, so a new page has a card the next time
this runs without anyone designing one.

Numbers come from where the site gets them: kit prices and the role count
from dev/catalog.py, HALLUX prices and coverage from the HALLUX bridge. A card
that quotes a price the page does not is the drift this build exists to stop.
"""
from __future__ import annotations

import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "assets" / "og"
sys.path.insert(0, str(ROOT / "dev"))

import catalog  # noqa: E402
import hallux_bridge  # noqa: E402

E = html.escape


def slug_for(page: Path) -> str:
    rel = page.parent.relative_to(DOCS).as_posix()
    return "home" if rel in ("", ".") else rel.replace("/", "-")


def money(n) -> str:
    return "${:,}".format(int(n))


# -- product cards ----------------------------------------------------------


def kit_tree() -> str:
    # The top of a real kit, as the kit service writes it.
    lines = [
        ('<span class="b">blvkware-agent-kit-follow-up/</span>', ""),
        ("├─ ", "README.md"), ("├─ ", "SETUP.md"), ("├─ ", "agent.json"),
        ("├─ ", '<span class="b">prompts/</span>'),
        ("│  ├─ ", "system.md"), ("│  └─ ", "capabilities/quote.followup.md"),
        ("├─ ", '<span class="b">workflows/</span>'),
        ("├─ ", '<span class="b">records/</span>'),
        ("├─ ", '<span class="b">tests/</span>'),
        ("└─ ", '<span class="b">tools/</span>'),
        ("   ├─ ", "openai.json"), ("   ├─ ", "anthropic.json"), ("   └─ ", "mcp.json"),
    ]
    return "\n".join(f'<span class="d">{a}</span><span class="i">{b}</span>' if a else a
                     for a, b in lines)


def hallux_terminal() -> str:
    api = hallux_bridge.API_BASE.rstrip("/") + "/hallux/v1"
    name = "requests-oauth2-helper"
    with urllib.request.urlopen(
        urllib.request.Request(f"{api}/check/pkg.pypi/{name}",
                               headers={"User-Agent": "blvkware-og-render/1.0"}), timeout=20
    ) as response:
        answer = json.load(response)
    stop = answer["verdict"] in ("absent", "phantom", "squat")
    verdict_class = "s" if stop else "c"
    host = api.replace("https://", "")
    nearest = answer["evidence"].get("nearestExisting", [])[:2]
    # Valid JSON on the card: a comma after every item but the last.
    nearest_lines = [f'    <span class="b">"{E(n)}"</span>' + ("," if i < len(nearest) - 1 else "")
                     for i, n in enumerate(nearest)]
    return "\n".join([
        f'<span class="c">$</span> <span class="i">curl</span> {E(host)}/',
        f'    check/pkg.pypi/{E(name)}',
        "",
        "{",
        f'  "verdict": <span class="{verdict_class}">"{E(answer["verdict"])}"</span>,',
        f'  "recommendation": <span class="{verdict_class}">"{E(answer.get("recommendation", ""))}"</span>,',
        f'  "successor": <span class="c">"{E(answer.get("successor") or "")}"</span>,',
        f'  "nearestExisting": [',
        *nearest_lines,
        "  ]",
        "}",
    ])


def pkgguard_terminal() -> str:
    names = ["reqeusts", "requests-oauth2-helper", "requests"]
    pkgguard = ROOT.parent / "pkgguard-API"
    env = dict(os.environ, NO_COLOR="1")
    run = subprocess.run(
        [sys.executable, "-m", "pkgguard.cli", "--json", "check", "--ecosystem", "pypi", *names],
        cwd=pkgguard, env=env, capture_output=True, text=True, timeout=180,
    )
    results = json.loads(run.stdout)
    results = results.get("results", results) if isinstance(results, dict) else results
    by_name = {r["name"]: r for r in results}
    lines = [f'<span class="c">$</span> <span class="i">pkgguard</span> check --ecosystem pypi \\',
             f"    {' '.join(names)}", ""]
    blocked = 0
    for name in names:
        verdict = by_name[name]["verdict"]
        blocked += verdict == "BLOCK"
        cls = "s" if verdict == "BLOCK" else "c" if verdict == "ALLOW" else "b"
        lines.append(f'<span class="{cls}">{verdict:<6}</span> <span class="i">{E(name)}</span>')
        reason = {
            "reqeusts": "no such package on pypi",
            "requests-oauth2-helper": "blends 2 real packages",
            "requests": "established",
        }[name] if verdict != "REVIEW" else "needs a person"
        lines.append(f'       <span class="d">{E(reason)}</span>')
    lines += ["", f'<span class="i">{len(names)} checked</span> <span class="d">|</span> '
                  f'<span class="s">{blocked} blocked</span>']
    return "\n".join(lines)


def product_cards() -> dict:
    tokens = hallux_bridge.tokens() or {}
    t = lambda k: tokens.get("{{%s}}" % k, "")  # noqa: E731
    k1, k2 = catalog.KITS[1], catalog.KITS[2]
    roles = catalog.ROLES
    return {
        "home": {
            "eyebrow": "AI agent kits",
            "title": "Design an AI agent.<br>Download its <em>complete kit</em>.",
            "sub": "Instructions, tools, workflows, records, guardrails and tests, written "
                   "for your business. Every file shown before you pay.",
            "pills": [f"{money(k1['price'])} or {money(k2['price'])}", "one-off"],
            "terminal": kit_tree(),
            "url": "blvkware.dev",
        },
        "hire": {
            "eyebrow": "Kit configurator",
            "title": "Design your agent.<br><em>See every file</em> before you pay.",
            "sub": f"Pick the job, choose what it can do, name the systems it operates and set "
                   f"how much it may do alone.",
            "pills": [f"From {money(k1['price'])}", "one-off"],
            "terminal": kit_tree(),
            "url": "blvkware.dev/hire",
        },
        "agents": {
            "eyebrow": "The catalog",
            "title": f"{len(roles)} jobs you<br>already <em>pay for</em>.",
            "sub": "Pick the one costing you most, design its agent, and download the "
                   "complete kit for it.",
            "pills": [f"From {money(k1['price'])}", "one-off"],
            "rows": [{"name": r["name"], "value": r["family"]} for r in roles[:7]]
                    + [{"name": f"and {len(roles) - 7} more", "value": "", "more": True}],
            "url": "blvkware.dev/agents",
        },
        "hallux": {
            "eyebrow": "HALLUX · API + MCP",
            "title": "Does this package<br><em>actually exist?</em>",
            "sub": f"One call before an agent installs, imports or cites. "
                   f"{t('HALLUX_NAMESPACE_COUNT')} registries, no account, no key.",
            "pills": ["Free", f"{t('HALLUX_FREE_DAILY')} checks a day"],
            "terminal": hallux_terminal(),
            "url": "blvkware.dev/hallux",
        },
        "pkgguard": {
            "eyebrow": "pkgguard · open source",
            "title": "Stop the install<br><em>before it runs.</em>",
            "sub": "A pre-install gate for npm, PyPI and crates.io. As a CLI, a GitHub "
                   "Action or an MCP server.",
            "pills": ["Free", "Apache 2.0"],
            "terminal": pkgguard_terminal(),
            "url": "blvkware.dev/pkgguard",
        },
        "pricing": {
            "eyebrow": "HALLUX pricing",
            "title": "Billed on questions asked.<br><em>Never on answers.</em>",
            "sub": "The price of a check cannot depend on its verdict, so HALLUX never "
                   "gains by blocking you.",
            "pills": ["Open tier free", f"{t('HALLUX_FREE_DAILY')} a day"],
            "rows": [
                {"name": "Open", "value": "Free"},
                {"name": "Metered", "value": f"{t('HALLUX_PRICE_PER_IDENTIFIER')} / identifier"},
                {"name": "Team", "value": f"{t('HALLUX_TEAM_MONTH')} / month"},
                {"name": "Feed", "value": f"{t('HALLUX_FEED_MONTH')} / month"},
                {"name": "Embedded", "value": f"{t('HALLUX_EMBEDDED_FROM')} / month"},
            ],
            "url": "blvkware.dev/pricing",
        },
    }


# -- article cards ----------------------------------------------------------

EYEBROWS = [
    (r"^docs-|^legal-corpus", "HALLUX documentation"),
    (r"^legal-bsl", "HALLUX licence"),
    (r"^(scan|design|build)$", "The Blvk Lab · free tool"),
    (r"^recovery-os$", "Build log"),
    (r"^vendor-renewal-tracker|^subscription-audit", "Vendor cost recovery"),
    (r"^(ai-automation-for-plumbers|quote-follow-up-automation)$", "AI agents, by job"),
    (r"^(privacy|terms)$", "BlvkWare"),
]


def meta(text: str, prop: str) -> str:
    m = re.search(r'<meta (?:property|name)="%s" content="([^"]*)"' % re.escape(prop), text)
    return html.unescape(m.group(1)) if m else ""


def article_card(slug: str, page_html: str) -> dict | None:
    title = meta(page_html, "og:title") or re.search(r"<title>([^<]*)", page_html).group(1)
    title = html.unescape(title).replace(" | BlvkWare", "").strip()
    sub = meta(page_html, "og:description") or meta(page_html, "description")
    if len(sub) > 190:
        sub = sub[:190].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    eyebrow = next((e for pattern, e in EYEBROWS if re.search(pattern, slug)), "BlvkWare guide")
    path = "" if slug == "home" else "/" + slug.replace("-", "/", 1) if slug.startswith(("docs-", "legal-")) else "/" + slug
    return {"layout": "article", "eyebrow": eyebrow, "title": E(title), "sub": sub,
            "pills": [], "url": "blvkware.dev" + path.replace("vendor/renewal", "vendor-renewal")}


def pages():
    for page in sorted(DOCS.rglob("index.html")):
        text = page.read_text(encoding="utf-8")
        if 'name="robots" content="noindex"' in text or "http-equiv=\"refresh\"" in text:
            continue  # redirect stubs
        yield slug_for(page), text


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    template = (HERE / "template.html").read_text(encoding="utf-8")
    logo = (DOCS / "assets" / "logo-192.png").as_uri()
    products = product_cards()
    work = Path(tempfile.mkdtemp(prefix="og-cards-"))
    jobs = []
    for slug, text in pages():
        card = products.get(slug) or article_card(slug, text)
        card.setdefault("layout", "product")
        card["logo"] = logo
        page = work / f"{slug}.html"
        page.write_text(template.replace("/*DATA*/", "window.CARD = " + json.dumps(card) + ";"),
                        encoding="utf-8")
        jobs.append({"html": str(page), "out": str(OUT / f"{slug}.png")})
    (work / "jobs.json").write_text(json.dumps(jobs), encoding="utf-8")
    shot = subprocess.run(["node", str(HERE / "shoot.mjs"), str(work / "jobs.json")],
                          capture_output=True, text=True)
    print(shot.stdout.strip())
    if shot.returncode != 0:
        print(shot.stderr.strip()[-800:])
        print("SOME CARDS OVERFLOWED OR TIMED OUT - see above")
        return 1
    print(f"{len(jobs)} cards in {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
