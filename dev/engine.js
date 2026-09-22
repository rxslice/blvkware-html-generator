/* The agent kit engine: tier, price and the design a kit is generated from.
 *
 * Runs in three places, as this exact file: the configurator at /hire/, the
 * Lab tools that design agents, and the kit service that generates and
 * delivers the download (blvkware-agentcore/kits). The service re-derives the
 * tier from the buyer's answers with this code rather than trusting what the
 * page sent, so a configurator bug can never sell a Deputy-sized kit at the
 * Operator price, and a hand-edited request cannot either.
 *
 * Reads window.BLVK_CATALOG (compiled from dev/catalog.py at build time).
 * Exposes window.BlvkEngine.
 */
(function (global) {
    "use strict";

    var C = global.BLVK_CATALOG;

    function capById(id) { return C.capabilities.filter(function (c) { return c.id === id; })[0]; }
    function roleById(id) { return C.roles.filter(function (r) { return r.id === id; })[0]; }
    function bandById(id) { return C.volume.filter(function (v) { return v.id === id; })[0] || C.volume[0]; }
    function chanById(id) { return C.channels.filter(function (c) { return c.id === id; })[0]; }

    function keysOf(obj) {
        return Object.keys(obj || {}).filter(function (k) { return obj[k]; });
    }

    /* Expand a selection to include everything it depends on. A capability
     * whose dependency is missing does not half-work, it does not work — so the
     * engine adds the dependency and the buyer is told, rather than the build
     * failing inspection on day nine. */
    function resolve(ids) {
        var out = {}, added = [];
        var queue = ids.slice();
        while (queue.length) {
            var id = queue.shift();
            if (out[id]) continue;
            var cap = capById(id);
            if (!cap) continue;
            out[id] = true;
            cap.needs.forEach(function (n) {
                if (!out[n]) {
                    if (ids.indexOf(n) === -1 && added.indexOf(n) === -1) added.push(n);
                    queue.push(n);
                }
            });
        }
        return { ids: Object.keys(out), added: added };
    }

    /* Channels are priced through their capability, never as a separate line,
     * so that turning on the phone costs the voice capability and not the voice
     * capability plus a channel surcharge. */
    function channelCaps(channelIds) {
        var out = [];
        channelIds.forEach(function (cid) {
            var ch = chanById(cid);
            if (ch && ch.cap) out.push(ch.cap);
        });
        return out;
    }

    function autonomyNeeds(level) {
        var a = C.autonomy.filter(function (x) { return x.id === level; })[0];
        return a ? a.needs.slice() : [];
    }

    /* ---- tier derivation -------------------------------------------------
     * The buyer never picks the tier. A scope that is really a Deputy cannot be
     * bought at the Operator price, and a buyer who genuinely needs less is not
     * upsold into a tier they will not use. */
    /* No single signal separates the tiers. Measured across the catalog, a
     * Tier I role loaded with everything it suggests reaches 18 weight and 5
     * capability groups, while a Tier II role's core alone sits at 11-14 weight
     * and 3-4 groups — the ranges overlap. So the thresholds sit above what a
     * fully-suggested Tier I configuration reaches, and the role's own declared
     * minimum carries the cases that breadth cannot see.
     *
     * Systems and channels escalate only past the tier's *maximum*, so a
     * genuinely one-job agent that touches a fourth system stays one job. */
    function deriveTier(state, resolved) {
        var role = roleById(state.roleId);
        var systems = keysOf(state.systems).length;
        var channels = keysOf(state.channels).length;

        var weight = 0, groups = {};
        resolved.ids.forEach(function (id) {
            var cap = capById(id);
            if (!cap) return;
            weight += cap.weight;
            groups[cap.group] = true;
        });
        var groupCount = Object.keys(groups).length;
        var t1 = C.tiers[1];

        var reasons = [];
        if (role && role.minTier === 2) {
            reasons.push("the " + role.name + " owns a whole function rather than one job");
        }
        if (weight > C.pricing.tier2Weight) {
            reasons.push("you have scoped more work than one job's worth");
        }
        if (groupCount >= C.pricing.tier2Groups) {
            reasons.push("it now spans " + groupCount + " different areas of your business rather than one");
        }
        if (systems > t1.maxSystems) {
            reasons.push("it has to operate " + systems + " systems, which is past what a Tier I agent stretches to");
        }
        if (channels > t1.maxChannels) {
            reasons.push("it works across " + channels + " channels, which is past what a Tier I agent stretches to");
        }

        var tier = reasons.length ? 2 : 1;

        /* Crossing into Tier II changes the kit price in a single click. A
         * buyer who meets that without warning reads it as a trap rather than a
         * tier, so the engine reports when a configuration is one step away,
         * and the page says so before the click rather than after it. */
        var near = tier === 1 && (
            weight > C.pricing.tier2Weight - 4 ||
            groupCount >= C.pricing.tier2Groups - 1 ||
            systems >= t1.maxSystems ||
            channels >= t1.maxChannels
        );

        return {
            tier: tier, key: tier, def: C.tiers[tier],
            weight: weight, groups: groupCount, reasons: reasons,
            systems: systems, channels: channels,
            nearTier2: near,
            tier2Delta: C.kits[2].price - C.kits[1].price,
            oversized: weight > C.pricing.splitWeight
        };
    }

    /* ---- pricing --------------------------------------------------------- */
    /* A kit is priced by its tier and nothing else. Capabilities, systems and
     * channels change what is in the kit and can change the tier; they are
     * never charged one by one. */
    function price(state) {
        var role = roleById(state.roleId);
        if (!role) return null;

        var picked = keysOf(state.caps)
            .concat(role.core)
            .concat(channelCaps(keysOf(state.channels)))
            .concat(autonomyNeeds(state.autonomy || "L1"));

        // de-duplicate before resolving so `added` reports honestly
        var seen = {}, unique = [];
        picked.forEach(function (id) { if (!seen[id]) { seen[id] = 1; unique.push(id); } });

        var resolved = resolve(unique);
        var t = deriveTier(state, resolved);
        var kit = C.kits[t.tier];

        var gates = {};
        resolved.ids.forEach(function (id) {
            var cap = capById(id);
            if (cap && cap.gate) gates[cap.gate] = true;
        });

        return {
            role: role, tier: t, def: t.def,
            resolved: resolved, autoAdded: resolved.added,
            kit: kit, price: kit.price, currency: kit.currency,
            gates: Object.keys(gates)
        };
    }

    /* ---- the design a kit is generated from --------------------------------- */
    function spec(state, q) {
        q = q || price(state);
        if (!q) return null;

        var caps = q.resolved.ids.map(function (id) {
            var c = capById(id);
            return { id: c.id, name: c.name, group: c.group, tpl: c.tpl, accept: c.accept, gate: c.gate };
        }).sort(function (a, b) { return a.group < b.group ? -1 : a.group > b.group ? 1 : 0; });

        /* Two different things end up on this list and the kit tells them apart.
         * A "declared" system is one the buyer said the agent works with. An
         * "implied" one comes with a capability they chose (the voice
         * capability needs a phone system), and its integration notes say which
         * capability needs it, so nobody wires a system for no reason. */
        var integ = {};
        keysOf(state.systems).forEach(function (i) { integ[i] = "declared"; });
        q.resolved.ids.forEach(function (id) {
            var c = capById(id);
            if (!c) return;
            c.integ.forEach(function (i) { if (!integ[i]) integ[i] = "implied"; });
        });

        var integrations = Object.keys(integ).map(function (id) {
            var d = C.integrations.filter(function (x) { return x.id === id; })[0];
            var by = [];
            if (integ[id] === "implied") {
                q.resolved.ids.forEach(function (cid) {
                    var c = capById(cid);
                    if (c && c.integ.indexOf(id) !== -1) by.push(c.name);
                });
            }
            return {
                id: id, name: d ? d.name : id,
                source: integ[id],
                requiredBy: by,
                detail: (state.systemDetail && state.systemDetail[id]) || ""
            };
        });

        var config = {};
        Object.keys(state.config || {}).forEach(function (id) {
            if (q.resolved.ids.indexOf(id) !== -1 && state.config[id]) config[id] = state.config[id];
        });

        return {
            schema: "blvkware.agent-design/1",
            ref: state.ref || null,
            role: { id: q.role.id, name: q.role.name, family: q.role.family },
            tier: { key: q.tier.key, name: q.def.name, derivedBecause: q.tier.reasons, weight: q.tier.weight },
            kit: { name: q.kit.name, price: q.kit.price, currency: q.kit.currency },
            autonomy: state.autonomy || "L1",
            channels: keysOf(state.channels).map(function (id) {
                var c = chanById(id);
                return { id: id, name: c ? c.name : id, gate: c ? c.gate : null };
            }),
            integrations: integrations,
            capabilities: caps,
            acceptance: caps.filter(function (c) { return c.accept; })
                            .map(function (c) { return { cap: c.id, name: c.name, test: c.accept }; }),
            gates: q.gates,
            business: state.answers || {},
            config: config
        };
    }

    /* Recompute a submitted design from scratch and compare. The kit service
     * does this before it generates anything: the tier and the price are
     * always the ones these answers derive, never the ones a request claims. */
    function verify(submitted) {
        if (!submitted || submitted.schema !== "blvkware.agent-design/1") {
            return { ok: false, fatal: "Not a BlvkWare agent design." };
        }
        var state = stateOf(submitted);
        var q = price(state);
        if (!q) return { ok: false, fatal: "Unknown role: " + state.roleId };

        var diffs = [];
        if (submitted.tier && Number(submitted.tier.key) !== q.tier.key) {
            diffs.push({ label: "Tier", claimed: "Tier " + submitted.tier.key, recomputed: "Tier " + q.tier.key });
        }
        if (submitted.kit && Number(submitted.kit.price) !== q.price) {
            diffs.push({ label: "Kit price", claimed: Number(submitted.kit.price), recomputed: q.price });
        }
        return { ok: diffs.length === 0, diffs: diffs, quote: q, spec: spec(state, q) };
    }

    /* The configurator state a design came from. */
    function stateOf(design) {
        var state = {
            roleId: design.role && design.role.id,
            caps: {}, systems: {}, channels: {},
            autonomy: design.autonomy,
            answers: design.business || {},
            config: design.config || {}
        };
        (design.capabilities || []).forEach(function (c) { state.caps[c.id] = true; });
        (design.integrations || []).forEach(function (i) {
            if (i.source === "declared") state.systems[i.id] = true;
        });
        (design.channels || []).forEach(function (c) { state.channels[c.id] = true; });
        return state;
    }

    function money(n) {
        return "$" + Number(n).toLocaleString("en-US");
    }

    global.BlvkEngine = {
        price: price, spec: spec, verify: verify, stateOf: stateOf, resolve: resolve,
        deriveTier: deriveTier, capById: capById, roleById: roleById,
        bandById: bandById, chanById: chanById, keysOf: keysOf, money: money,
        catalog: C
    };
    // Also usable outside a browser. The kit service re-derives every tier
    // server-side from this exact file, because a price the client sends is a
    // price anyone can edit.
})(typeof window !== "undefined" ? window : globalThis);
