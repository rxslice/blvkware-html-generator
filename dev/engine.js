/* The agent pricing and specification engine.
 *
 * Injected verbatim into BOTH the buyer's configurator at /hire/ and the
 * internal fulfilment console. That is deliberate: the console recomputes the
 * price from the submitted specification and compares it against what the buyer
 * was actually charged. If those ever disagree, the order is held rather than
 * built — which is the only reliable defence against a configurator bug quietly
 * selling a Deputy's workload at Operator money.
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
     * bought at Operator money, and a buyer who genuinely needs less is not
     * upsold into a tier they will not use. */
    /* No single signal separates the tiers. Measured across the catalog, a
     * Tier I role loaded with everything it suggests reaches 18 weight and 5
     * capability groups, while a Tier II role's core alone sits at 11-14 weight
     * and 3-4 groups — the ranges overlap. So the thresholds sit above what a
     * fully-suggested Tier I configuration reaches, and the role's own declared
     * minimum carries the cases that breadth cannot see.
     *
     * Systems and channels escalate only past the tier's *maximum*, not past
     * what the base includes. The span between the two is sold at the published
     * per-connection price, so a fourth system costs $750 rather than $6,000. */
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

        /* Crossing into Tier II costs the difference between the two base
         * prices in a single click. That difference is real — it is 10 delivery
         * days against 25 — but a buyer who meets it without warning reads it as
         * a trap rather than a tier. So the engine reports when a configuration
         * is one step away, and the page says so before the click rather than
         * after it. */
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
            tier2Delta: C.tiers[2].build - C.tiers[1].build,
            oversized: weight > C.pricing.splitWeight
        };
    }

    /* ---- pricing --------------------------------------------------------- */
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
        var def = t.def;

        var coreSet = {};
        role.core.forEach(function (id) { coreSet[id] = true; });

        var lines = [];
        var addedBuild = 0, capOps = 0;
        var gates = {};

        resolved.ids.forEach(function (id) {
            var cap = capById(id);
            if (!cap) return;
            if (cap.gate) gates[cap.gate] = true;
            capOps += cap.ops || 0;
            if (!coreSet[id]) {
                addedBuild += cap.price;
                lines.push({ kind: "cap", id: id, name: cap.name, amount: cap.price, group: cap.group });
            }
        });
        lines.sort(function (a, b) { return a.group === b.group ? b.amount - a.amount : a.group < b.group ? -1 : 1; });

        var extraSystems = Math.max(0, t.systems - def.systems);
        var systemsCost = extraSystems * C.pricing.extraSystem;

        var subtotal = def.build + addedBuild + systemsCost;

        var rush = state.modifiers && state.modifiers.rush;
        var rushCost = rush ? Math.round(subtotal * C.pricing.rushPct) : 0;
        var build = subtotal + rushCost;

        var band = bandById(state.volumeId);
        var extraActions = Math.max(0, band.actions - def.actions);
        var volumeOps = Math.ceil(extraActions / 1000) * C.pricing.prebuyPer1000;

        var monthly = def.ops + capOps + volumeOps;
        var annual = monthly * C.pricing.annualMonths;
        var recurring = state.billing === "annual" ? annual : monthly;

        var trial = !!state.trial;
        var credit = trial ? C.pricing.trial : 0;
        var dueNow = trial ? C.pricing.trial : build + recurring;

        var days = def.buildDays;
        if (rush) days = Math.ceil(days / 2);

        return {
            role: role, tier: t, def: def,
            resolved: resolved, autoAdded: resolved.added,
            lines: lines,
            base: def.build, addedBuild: addedBuild,
            extraSystems: extraSystems, systemsCost: systemsCost,
            rush: !!rush, rushCost: rushCost,
            subtotal: subtotal, build: build,
            capOps: capOps, volumeOps: volumeOps, band: band,
            includedActions: band.actions > def.actions ? band.actions : def.actions,
            monthly: monthly, annual: annual, recurring: recurring,
            trial: trial, credit: credit, dueNow: dueNow,
            buildAfterCredit: build - credit,
            gates: Object.keys(gates),
            days: days,
            billing: state.billing === "annual" ? "annual" : "monthly"
        };
    }

    /* ---- the specification the operator actually builds from ------------- */
    function spec(state, q) {
        q = q || price(state);
        if (!q) return null;

        var caps = q.resolved.ids.map(function (id) {
            var c = capById(id);
            return { id: c.id, name: c.name, group: c.group, tpl: c.tpl, accept: c.accept, gate: c.gate };
        }).sort(function (a, b) { return a.group < b.group ? -1 : a.group > b.group ? 1 : 0; });

        /* Two different things end up on this list and the operator must be able
         * to tell them apart. A "declared" system is one the buyer ticked and
         * paid a connection fee for beyond the tier's allowance. An "implied"
         * one comes with a capability they bought — the voice capability already
         * covers wiring the phone system — so it is in scope and already paid
         * for, but it is not what the connection count was charged on. Merging
         * them silently is how a build ends up wiring more than was sold. */
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

        return {
            schema: "blvkware.agent-order/1",
            ref: state.ref || null,
            role: { id: q.role.id, name: q.role.name, family: q.role.family },
            tier: { key: q.tier.key, name: q.def.name, derivedBecause: q.tier.reasons, weight: q.tier.weight },
            autonomy: state.autonomy || "L1",
            channels: keysOf(state.channels).map(function (id) {
                var c = chanById(id);
                return { id: id, name: c ? c.name : id, gate: c ? c.gate : null };
            }),
            integrations: integrations,
            volume: { id: q.band.id, label: q.band.label, includedActions: q.includedActions },
            capabilities: caps,
            templates: caps.map(function (c) { return c.tpl; }),
            acceptance: caps.filter(function (c) { return c.accept; })
                            .map(function (c) { return { cap: c.id, name: c.name, test: c.accept }; }),
            gates: q.gates,
            delivery: { businessDays: q.days, rush: q.rush },
            commercial: {
                build: q.build, subtotal: q.subtotal, rushCost: q.rushCost,
                monthly: q.monthly, annual: q.annual, billing: q.billing,
                trial: q.trial, credit: q.credit, dueNow: q.dueNow
            },
            business: state.answers || {}
        };
    }

    /* Recompute a submitted spec from scratch and compare. Used by the
     * fulfilment console before any build work starts. */
    function verify(submitted) {
        if (!submitted || submitted.schema !== "blvkware.agent-order/1") {
            return { ok: false, fatal: "Not a BlvkWare agent order." };
        }
        var state = {
            roleId: submitted.role && submitted.role.id,
            caps: {}, systems: {}, channels: {},
            volumeId: submitted.volume && submitted.volume.id,
            autonomy: submitted.autonomy,
            billing: submitted.commercial && submitted.commercial.billing,
            trial: !!(submitted.commercial && submitted.commercial.trial),
            modifiers: { rush: !!(submitted.delivery && submitted.delivery.rush) }
        };
        (submitted.capabilities || []).forEach(function (c) { state.caps[c.id] = true; });
        (submitted.integrations || []).forEach(function (i) { state.systems[i.id] = true; });
        (submitted.channels || []).forEach(function (c) { state.channels[c.id] = true; });

        var q = price(state);
        if (!q) return { ok: false, fatal: "Unknown role: " + state.roleId };

        var was = submitted.commercial || {};
        var diffs = [];
        function cmp(label, got, expect) {
            if (Number(got) !== Number(expect)) {
                diffs.push({ label: label, charged: Number(got), recomputed: Number(expect) });
            }
        }
        cmp("Build", was.build, q.build);
        cmp("Monthly", was.monthly, q.monthly);
        cmp("Due at order", was.dueNow, q.dueNow);
        if (submitted.tier && Number(submitted.tier.key) !== q.tier.key) {
            diffs.push({ label: "Tier", charged: "Tier " + submitted.tier.key, recomputed: "Tier " + q.tier.key });
        }
        return { ok: diffs.length === 0, diffs: diffs, quote: q, spec: spec(state, q) };
    }

    function money(n) {
        return "$" + Number(n).toLocaleString("en-US");
    }

    global.BlvkEngine = {
        price: price, spec: spec, verify: verify, resolve: resolve,
        deriveTier: deriveTier, capById: capById, roleById: roleById,
        bandById: bandById, chanById: chanById, keysOf: keysOf, money: money,
        catalog: C
    };
})(window);
