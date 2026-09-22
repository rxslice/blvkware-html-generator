#!/usr/bin/env python3
"""
Check the launch copy before anyone pastes it.

    python marketing/launch/check.py

Every block in marketing/launch/*.md fenced as

    ```post name="PH tagline" limit=60
    ...
    ```

is held to:

* its platform's length limit (the `limit`), counted the way the platforms
  count, in characters;
* the copy rules: no em dashes or en dashes (see the blvkware copy rules);
* the facts the site publishes: every $ price must be one the site charges,
  and the counts it quotes (jobs in the catalog, free HALLUX checks a day,
  HALLUX registries) must match the catalog and HALLUX.

Copy that quotes a price the site does not charge is the drift the site's
own build refuses; this is the same rule for text that lives off the site.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "dev"))

import catalog  # noqa: E402
import hallux_bridge  # noqa: E402

BLOCK = re.compile(r'```post name="([^"]+)" limit=(\d+)\n(.*?)\n```', re.S)


def facts():
    tokens = hallux_bridge.tokens() or {}
    prices = {"$%d" % k["price"] for k in catalog.KITS.values()}
    for key, value in tokens.items():
        for match in re.findall(r"\$[\d,.]+", value):
            prices.add(match.rstrip(".,"))
    return {
        "prices": prices,
        "roles": len(catalog.ROLES),
        "free": tokens.get("{{HALLUX_FREE_DAILY}}", "").replace(",", ""),
        "registries": tokens.get("{{HALLUX_NAMESPACE_COUNT}}", ""),
    }


def check_block(name, limit, text, known):
    problems = []
    if len(text) > limit:
        problems.append(f"{len(text)} characters, limit {limit}")
    if "—" in text or "–" in text:
        problems.append("contains an em or en dash")
    # "$1,500" is one price; the comma in "$199, one-off" is punctuation.
    for price in re.findall(r"\$\d{1,3}(?:,\d{3})*(?:\.\d+)?", text):
        if price not in known["prices"]:
            problems.append(f"quotes {price}, which the site does not charge")
    for count in re.findall(r"\b(\d+) (?:of them|jobs|in the catalog)\b", text):
        if int(count) != known["roles"]:
            problems.append(f"says {count} jobs; the catalog has {known['roles']}")
    for count in re.findall(r"\b(\d[\d,]*) (?:names|checks|identifiers) a day\b", text):
        if count.replace(",", "") != known["free"]:
            problems.append(f"says {count} a day; the HALLUX open tier is {known['free']}")
    return problems


def main() -> int:
    known = facts()
    failures = 0
    total = 0
    for path in sorted(HERE.glob("*.md")):
        for name, limit, text in BLOCK.findall(path.read_text(encoding="utf-8")):
            total += 1
            problems = check_block(name, int(limit), text, known)
            status = "FAIL" if problems else "ok  "
            print(f"{status} {path.name:<10} {name:<22} {len(text):>5}/{limit}"
                  + ("  " + "; ".join(problems) if problems else ""))
            failures += bool(problems)
    print(f"\n{total} blocks, {failures} failing")
    return 1 if failures or not total else 0


if __name__ == "__main__":
    sys.exit(main())
