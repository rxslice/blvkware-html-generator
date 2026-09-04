#!/usr/bin/env python3
"""Check that the web builder and agentcore still agree about capabilities.

The browser writes a configuration; agentcore consumes it. Those are two repos,
and the only thing keeping them in step has been somebody remembering. It did
not hold: five capabilities that agentcore already knew how to tailor had no
schema entry in the browser, so every order containing one arrived as operator
work for no reason.

This reports three kinds of drift:

  MISSING   agentcore can tailor it, the browser has no schema for it, so the
            buyer is told it needs a human when it does not.
  UNKNOWN   the browser writes config for a capability agentcore has no handler
            for, which is worse: it looks configured and nothing consumes it.
  KEYS      both sides know the capability but disagree about the field names,
            so the configuration is silently dropped at load.

Run it directly, or let build-static.py call it. Exits 1 on drift.
agentcore is a separate private repo; when it is not checked out this exits 0
with a note rather than failing a build that has nothing to do with it.
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
WEB = HERE.parent
# agentcore sits beside the site repo in the workspace.
CORE = WEB.parent / "blvkware-agentcore" / "agentcore"

# Fields the runtime reads for each template, from agentcore's blueprint.
# Kept here as the expectation; the check below verifies it against the source
# so this comment cannot quietly become a lie either.
TEMPLATE_KEYS = {
    "SequenceCap": {"subject", "steps"},
    "TriageCap": {"labels"},
    "RouteCap": {"rules", "default"},
    "ComposeCap": {"purpose", "template"},
    "RecordCap": {"required"},
    "DialogueCap": {"purpose", "needed"},
    "AnalyseCap": {"group_by", "measure"},
    "PortalCap": {"fields"},
}


def web_schema() -> dict[str, set[str]]:
    """Capability id -> the keys the browser is allowed to write for it."""
    src = (HERE / "forge.js").read_text(encoding="utf-8")
    block = src.split("var SCHEMA = {", 1)[1].split("\n    };", 1)[0]
    out: dict[str, set[str]] = {}
    for m in re.finditer(r'"([a-z0-9_.]+)"\s*:\s*\{(.*?)\n\s*(?="|\})', block, re.S):
        keys = re.search(r"keys:\s*\{(.*?)\}", m.group(2), re.S)
        out[m.group(1)] = set(re.findall(r"(\w+)\s*:", keys.group(1))) if keys else set()
    return out


def core_registry() -> dict[str, str]:
    """Capability id -> template class name, from agentcore's registry."""
    reg = (CORE / "capabilities" / "__init__.py").read_text(encoding="utf-8")
    return dict(re.findall(r'"([a-z0-9_.]+)":\s*\(([A-Za-z]+Cap)', reg))


def core_template_keys() -> dict[str, set[str]]:
    """Read the template field names straight out of blueprint.py."""
    bp = (CORE / "blueprint.py").read_text(encoding="utf-8")
    block = bp.split("TEMPLATE_FIELDS", 1)[1].split("\n# A few capabilities", 1)[0]
    out: dict[str, set[str]] = {}
    for m in re.finditer(r'"([A-Za-z]+Cap)":\s*\[(.*?)\n    \]', block, re.S):
        out[m.group(1)] = set(re.findall(r'F\(\s*"(\w+)"', m.group(2)))
    return out


def core_consumed_keys() -> set[str]:
    """Every config key agentcore reads, or supplies a default for, anywhere.

    A capability's tailorable fields are only part of its config: the rest comes
    from `defaults()` and from the registry tuple. Comparing the browser's keys
    against the tailorable set alone reports a capability as broken every time it
    writes a perfectly good default, which is how the first version of this check
    produced eight false alarms. The question worth asking is narrower and more
    useful: does anything in agentcore read this key at all?
    """
    keys: set[str] = set()
    for f in CORE.rglob("*.py"):
        t = f.read_text(encoding="utf-8", errors="replace")
        keys |= set(re.findall(r'config\["([a-z_]+)"\]', t))
        keys |= set(re.findall(r'config\.get\("([a-z_]+)"', t))
        for m in re.finditer(r"def defaults\(self\)[^{]*\{(.*?)\}", t, re.S):
            keys |= set(re.findall(r'"([a-z_]+)"\s*:', m.group(1)))
        for m in re.finditer(r"\([A-Za-z]+Cap,\s*\{(.*?)\}\)", t, re.S):
            keys |= set(re.findall(r'"([a-z_]+)"\s*:', m.group(1)))
    return keys


def main() -> int:
    if not CORE.exists():
        print("agentcore not checked out beside this repo; coverage check skipped.")
        return 0

    schema, registry = web_schema(), core_registry()
    declared = core_template_keys()

    problems = 0

    # The documented expectation must match agentcore's actual blueprint.
    for tpl, keys in TEMPLATE_KEYS.items():
        actual = declared.get(tpl)
        if actual and actual != keys:
            print(f"KEYS   template {tpl}: this script expects {sorted(keys)}, "
                  f"blueprint.py declares {sorted(actual)}")
            problems += 1

    missing = [c for c, tpl in sorted(registry.items())
               if tpl in TEMPLATE_KEYS and c not in schema]
    for c in missing:
        print(f"MISSING  {c:<22} agentcore tailors it as {registry[c]}, "
              f"the browser has no schema entry")
        problems += 1

    # Keys the browser consumes itself instead of passing through. knowledge.pack
    # is the only one: forge.js lifts `documents` out and puts it in the agent's
    # knowledge pack, because it is content rather than a capability setting, so
    # agentcore is right never to read it as config.
    HANDLED_IN_BROWSER = {"knowledge.pack": {"documents"}}

    consumed = core_consumed_keys()
    for cap, keys in sorted(schema.items()):
        stray = keys - consumed - HANDLED_IN_BROWSER.get(cap, set())
        if stray:
            print(f"KEYS     {cap:<22} writes {sorted(stray)}, which agentcore "
                  f"never reads; that config would be discarded at load")
            problems += 1

    covered = sum(1 for c in registry if c in schema)
    print(f"\n{len(schema)} schema entries; {covered}/{len(registry)} of agentcore's "
          f"registry covered.")
    if problems:
        print(f"{problems} drift problem(s).")
        return 1
    print("No drift.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
