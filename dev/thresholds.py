#!/usr/bin/env python3
"""Guard the tier-derivation thresholds against catalog drift.

    python dev/thresholds.py

The configurator derives a buyer's tier from the scope they configure. If a
capability's weight changes, or a role gains a suggestion, a Tier I role can
silently start pricing as a Tier II — which triples the entry price and makes
the tier look arbitrary to anyone clicking around. That is a business bug, not
a styling one, so it gets a test.

The rule this enforces: **a Tier I role configured at its own recommended scope
must stay Tier I.** A buyer who goes further than the role suggests may escalate;
a buyer who simply accepts the defaults may not.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import catalog as C


def resolve(ids):
    """Expand a capability selection to include its dependencies."""
    seen, queue = set(), list(ids)
    while queue:
        cid = queue.pop()
        if cid in seen:
            continue
        seen.add(cid)
        queue.extend(C.CAP_BY_ID[cid]["needs"])
    return seen


def measure(ids):
    caps = [C.CAP_BY_ID[i] for i in resolve(ids)]
    return sum(c["weight"] for c in caps), len(set(c["group"] for c in caps))


def main():
    failures = []
    t1_weight = t1_groups = 0
    t2_core_weight = []
    t2_core_groups = []

    rows = []
    for r in C.ROLES:
        core_w, core_g = measure(r["core"])
        full_w, full_g = measure(list(r["core"]) + list(r["suggested"]))
        rows.append((r["name"], r["minTier"], core_w, core_g, full_w, full_g))

        if r["minTier"] == 1:
            t1_weight = max(t1_weight, full_w)
            t1_groups = max(t1_groups, full_g)
            if full_w > C.TIER2_WEIGHT:
                failures.append(
                    "%s is a Tier I role but its recommended scope weighs %d, "
                    "over the Tier II threshold of %d"
                    % (r["name"], full_w, C.TIER2_WEIGHT))
            if full_g >= C.TIER2_GROUPS:
                failures.append(
                    "%s is a Tier I role but its recommended scope spans %d "
                    "capability groups, at or over the Tier II threshold of %d"
                    % (r["name"], full_g, C.TIER2_GROUPS))
        else:
            t2_core_weight.append(core_w)
            t2_core_groups.append(core_g)

    width = max(len(x[0]) for x in rows)
    print("%-*s  tier  core_w  core_g  full_w  full_g" % (width, "role"))
    for name, tier, cw, cg, fw, fg in rows:
        print("%-*s  %4d  %6d  %6d  %6d  %6d" % (width, name, tier, cw, cg, fw, fg))

    print()
    print("Tier I ceiling at recommended scope : weight %d, groups %d"
          % (t1_weight, t1_groups))
    print("Tier II core range                  : weight %d-%d, groups %d-%d"
          % (min(t2_core_weight), max(t2_core_weight),
             min(t2_core_groups), max(t2_core_groups)))
    print("Thresholds                          : weight > %d, groups >= %d"
          % (C.TIER2_WEIGHT, C.TIER2_GROUPS))
    print("Headroom                            : weight %d, groups %d"
          % (C.TIER2_WEIGHT - t1_weight, C.TIER2_GROUPS - t1_groups))

    # A threshold that only just clears the ceiling will break on the next
    # capability added to a role, so require real headroom rather than none.
    if C.TIER2_WEIGHT - t1_weight < 2:
        failures.append(
            "weight threshold (%d) leaves under 2 points of headroom above the "
            "Tier I ceiling (%d) — the next capability added to any Tier I role "
            "will silently reprice it" % (C.TIER2_WEIGHT, t1_weight))
    if C.TIER2_GROUPS - t1_groups < 1:
        failures.append(
            "group threshold (%d) leaves no headroom above the Tier I ceiling "
            "(%d)" % (C.TIER2_GROUPS, t1_groups))

    print()
    if failures:
        for f in failures:
            print("FAIL: %s" % f)
        return 1
    print("OK: every Tier I role stays Tier I at its recommended scope.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
