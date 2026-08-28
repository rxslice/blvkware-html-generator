/* The design engine: business signals in, a costed agent design out.
 *
 * Shared by AUGUR (find the need), SCRY (design the agent) and SIGIL (forge it),
 * so all three propose the same thing for the same business.
 *
 * The rule that governs this whole file: **the model interprets, the catalog
 * decides.** A language model is good at reading a business and saying "these
 * people are drowning in quotes nobody chases". It is not allowed to say what
 * that costs, or to invent a capability. So every model output is filtered
 * through `adopt()`, which discards anything that is not a real catalog id, and
 * pricing only ever happens in BlvkEngine.
 *
 * The failure this prevents is specific and expensive: a hallucinated quote is
 * a number a buyer will hold us to.
 *
 * Reads window.BLVK_CATALOG and window.BlvkEngine. Exposes window.BlvkDesign.
 */
(function (global) {
    "use strict";

    var C = global.BLVK_CATALOG;
    var E = global.BlvkEngine;

    /* ---------------------------------------------------------------
     * Signals — the observable facts that imply an agent is worth having.
     *
     * Each is something a person can confirm about their own business in one
     * sentence, because a diagnostic the buyer cannot check is just an opinion.
     * `roles` maps the signal onto catalog roles with a weight: how strongly
     * this signal argues for that role.
     * ------------------------------------------------------------- */
    var SIGNALS = [
        { id: "quotes_unchased", ask: "You send quotes or estimates and nobody reliably chases them",
          evidence: "quotes, estimates, proposals sent by email",
          roles: { "follow-up": 5, "revenue-deputy": 3, "crm-operator": 1 } },

        { id: "slow_reply", ask: "New enquiries can wait hours — or overnight — for a first reply",
          evidence: "contact form, no live chat, no stated response time",
          roles: { "lead-qualifier": 4, "front-desk": 4, "email-manager": 2 } },

        { id: "missed_calls", ask: "Calls go unanswered when you're on a job",
          evidence: "a phone number as the primary call to action",
          roles: { "front-desk": 5, "appointment-setter": 2 } },

        { id: "inbox_swamp", ask: "A shared inbox is where things go to die",
          evidence: "info@ or admin@ as the published address",
          roles: { "email-manager": 5, "support-agent": 2 } },

        { id: "manual_booking", ask: "Booking and rescheduling is done by hand, by a person",
          evidence: "no online booking; 'call us to arrange'",
          roles: { "appointment-setter": 5, "front-desk": 3 } },

        { id: "unpaid_invoices", ask: "You are owed money you haven't chased",
          evidence: "invoicing mentioned; payment terms published",
          roles: { "collections": 5, "back-office": 3 } },

        { id: "crm_rot", ask: "Your CRM is only as good as whoever last remembered to update it",
          evidence: "a CRM in the stack with no automation around it",
          roles: { "crm-operator": 5, "revenue-deputy": 2 } },

        { id: "portal_by_hand", ask: "Somebody logs into a supplier or insurer portal and copies things out",
          evidence: "supplier, insurer, council or trade portal referenced",
          roles: { "browser-operator": 6 } },

        { id: "no_reporting", ask: "Getting a straight answer out of your own numbers takes a day",
          evidence: "several systems, no dashboard, spreadsheet reporting",
          roles: { "data-analyst": 5, "reporting": 4 } },

        { id: "repeat_questions", ask: "The same customer questions get answered over and over",
          evidence: "an FAQ page, published policies, a help centre",
          roles: { "support-agent": 5, "email-manager": 2 } },

        { id: "onboarding_adhoc", ask: "Onboarding a new client or hire is different every time",
          evidence: "a documented process, a welcome pack, a checklist",
          roles: { "onboarding": 5 } },

        { id: "no_outreach", ask: "Prospecting is the first thing to fall off when work gets busy",
          evidence: "a sales motion with no visible sequencing",
          roles: { "outreach": 4, "research": 2 } },

        { id: "no_reviews", ask: "You do good work and have far fewer reviews than you deserve",
          evidence: "few or no public reviews against visible volume",
          roles: { "follow-up": 2, "support-agent": 2 } },

        { id: "multi_system", ask: "A job crosses four systems and only one person knows the whole path",
          evidence: "several disconnected tools in the stack",
          roles: { "workflow-operator": 6, "back-office": 3 } },

        { id: "post_sale_drop", ask: "After the sale, customers hear nothing until they chase",
          evidence: "no status updates, no service portal",
          roles: { "support-agent": 4, "front-desk": 2 } }
    ];

    var SIGNAL_BY_ID = {};
    SIGNALS.forEach(function (s) { SIGNAL_BY_ID[s.id] = s; });

    /* Integration categories a role usually implies, so a design arrives with a
     * sensible stack rather than an empty one the buyer has to guess at. */
    var ROLE_SYSTEMS = {
        "email-manager": ["email"],
        "front-desk": ["email", "calendar", "crm", "telephony"],
        "support-agent": ["email", "helpdesk"],
        "lead-qualifier": ["email", "crm"],
        "appointment-setter": ["calendar", "crm"],
        "follow-up": ["email", "crm"],
        "outreach": ["email", "crm"],
        "revenue-deputy": ["email", "crm", "calendar"],
        "crm-operator": ["crm"],
        "workflow-operator": ["crm", "pm", "storage"],
        "browser-operator": ["portal", "sheets"],
        "onboarding": ["email", "pm", "storage"],
        "collections": ["accounting", "payments", "email"],
        "back-office": ["accounting", "payments", "crm"],
        "data-analyst": ["sheets", "db"],
        "reporting": ["sheets", "db"],
        "research": ["crm"]
    };

    function roleById(id) { return E.roleById(id); }
    function capById(id) { return E.capById(id); }

    /* ---------------------------------------------------------------
     * Ranking: which agent should this business hire first?
     * ------------------------------------------------------------- */
    function rank(signalIds, opts) {
        opts = opts || {};
        var scores = {}, why = {};

        /* Signals decay by the order they were reported. What a business leads
         * with is what actually hurts; without this, three mild secondary
         * mentions outrank the one thing they opened with — which is how a firm
         * complaining that nobody chases its quotes gets recommended a CRM
         * tidier instead of a Follow-Up Agent. */
        (signalIds || []).forEach(function (sid, i) {
            var sig = SIGNAL_BY_ID[sid];
            if (!sig) return;
            var decay = Math.pow(0.82, i);
            Object.keys(sig.roles).forEach(function (roleId) {
                if (!roleById(roleId)) return;
                scores[roleId] = (scores[roleId] || 0) + sig.roles[roleId] * decay;
                (why[roleId] = why[roleId] || []).push(sig.ask);
            });
        });

        /* A role named after reading the whole description is evidence, not a
         * footnote. Weighted below a lead signal but well above a passing one. */
        (opts.nominated || []).forEach(function (rid, i) {
            if (!roleById(rid)) return;
            scores[rid] = (scores[rid] || 0) + Math.max(4 - i * 1.5, 1);
            (why[rid] = why[rid] || []).unshift("named directly from how you described the business");
        });

        var out = Object.keys(scores).map(function (roleId) {
            var role = roleById(roleId);
            return {
                roleId: roleId, role: role, score: scores[roleId],
                reasons: why[roleId].slice(0, 3),
                tier: role.minTier
            };
        });

        // Strongest signal first; on a tie prefer the cheaper tier, because a
        // first hire that costs less is a first hire that actually happens.
        out.sort(function (a, b) {
            return b.score - a.score || a.tier - b.tier ||
                   (a.role.name < b.role.name ? -1 : 1);
        });
        return opts.limit ? out.slice(0, opts.limit) : out;
    }

    /* ---------------------------------------------------------------
     * Designing one agent.
     * ------------------------------------------------------------- */

    /* Which of a role's suggested capabilities this business actually needs.
     * Everything a buyer does not need is money they should not spend, and a
     * design that ticks every box is a design nobody trusts. */
    function relevantSuggestions(role, signalIds, systems) {
        var sigs = {}; (signalIds || []).forEach(function (s) { sigs[s] = true; });
        var sys = {}; (systems || []).forEach(function (s) { sys[s] = true; });

        return role.suggested.filter(function (cid) {
            var cap = capById(cid);
            if (!cap) return false;
            // A capability whose integration the business does not have is
            // noise; do not sell a CRM writer to somebody with no CRM.
            if (cap.integ.length && !cap.integ.some(function (i) { return sys[i]; })) {
                // telephony and portal are opt-in, never assumed
                if (cap.integ.indexOf("telephony") !== -1 ||
                    cap.integ.indexOf("portal") !== -1) return false;
            }
            // Anything with a registration gate stays out of a default design.
            if (cap.gate) return false;
            return true;
        });
    }

    function design(roleId, opts) {
        opts = opts || {};
        var role = roleById(roleId);
        if (!role) return null;

        var systems = (opts.systems && opts.systems.length)
            ? opts.systems.slice() : (ROLE_SYSTEMS[roleId] || ["email"]).slice();
        var channels = (opts.channels && opts.channels.length)
            ? opts.channels.slice() : ["email"];

        var chosen = {};
        role.core.forEach(function (c) { chosen[c] = true; });
        var suggested = opts.capabilities
            ? opts.capabilities.filter(function (c) { return capById(c); })
            : relevantSuggestions(role, opts.signals, systems);
        suggested.forEach(function (c) { chosen[c] = true; });

        var state = {
            roleId: roleId,
            caps: chosen,
            systems: systems.reduce(function (a, s) { a[s] = true; return a; }, {}),
            systemDetail: opts.systemDetail || {},
            channels: channels.reduce(function (a, c) { a[c] = true; return a; }, {}),
            volumeId: opts.volumeId || "standard",
            autonomy: opts.autonomy || "L1",
            modifiers: {},
            billing: opts.billing || "monthly",
            trial: !!opts.trial,
            answers: opts.answers || {},
            ref: opts.ref || null
        };

        var quote = E.price(state);
        return {
            roleId: roleId, role: role, state: state, quote: quote,
            spec: E.spec(state, quote),
            signals: (opts.signals || []).slice(),
            reasons: (opts.reasons || []).slice()
        };
    }

    /* ---------------------------------------------------------------
     * Adopting model output. Nothing the model says is trusted directly.
     * ------------------------------------------------------------- */
    function adopt(raw) {
        raw = raw || {};
        var out = { signals: [], roles: [], capabilities: [], systems: [],
                    channels: [], notes: [], dropped: [] };

        (raw.signals || []).forEach(function (s) {
            var id = typeof s === "string" ? s : (s && s.id);
            if (SIGNAL_BY_ID[id]) out.signals.push(id);
            else if (id) out.dropped.push("signal:" + id);
        });
        (raw.roles || []).forEach(function (r) {
            var id = typeof r === "string" ? r : (r && r.id);
            if (roleById(id)) out.roles.push(id);
            else if (id) out.dropped.push("role:" + id);
        });
        (raw.capabilities || []).forEach(function (c) {
            var id = typeof c === "string" ? c : (c && c.id);
            if (capById(id)) out.capabilities.push(id);
            else if (id) out.dropped.push("capability:" + id);
        });
        (raw.systems || []).forEach(function (s) {
            var id = typeof s === "string" ? s : (s && s.id);
            if (C.integrations.some(function (i) { return i.id === id; })) out.systems.push(id);
            else if (id) out.dropped.push("system:" + id);
        });
        (raw.channels || []).forEach(function (c) {
            var id = typeof c === "string" ? c : (c && c.id);
            if (C.channels.some(function (x) { return x.id === id; })) out.channels.push(id);
            else if (id) out.dropped.push("channel:" + id);
        });
        (raw.notes || []).forEach(function (n) {
            if (typeof n === "string" && n.trim()) out.notes.push(n.trim());
        });
        out.business = typeof raw.business === "string" ? raw.business : "";
        out.summary = typeof raw.summary === "string" ? raw.summary : "";
        return out;
    }

    /* The instruction fragment every tool appends, so the model is constrained
     * to the catalog rather than asked to be creative about the product. */
    function vocabulary() {
        var lines = [];
        lines.push("SIGNALS you may report (use the id exactly):");
        SIGNALS.forEach(function (s) {
            lines.push("  " + s.id + " — " + s.ask);
        });
        lines.push("");
        lines.push("ROLES you may recommend (use the id exactly):");
        C.roles.forEach(function (r) {
            lines.push("  " + r.id + " — " + r.name + ": " + r.oneLine);
        });
        lines.push("");
        lines.push("SYSTEMS you may name (use the id exactly):");
        lines.push("  " + C.integrations.map(function (i) { return i.id; }).join(", "));
        lines.push("");
        lines.push("RULES:");
        lines.push("  - Never state a price, a fee, or a timeline. Those are computed, not written.");
        lines.push("  - Never invent a role, capability or system id. Anything not on these lists is discarded.");
        lines.push("  - Only report a signal you can point to actual evidence for.");
        return lines.join("\n");
    }

    /* ---------------------------------------------------------------
     * Readiness — how much of this can be built without the operator.
     * ------------------------------------------------------------- */

    /* What each capability needs before it can run for real comes from the
     * catalog (SETUP_NEEDS), so the buyer-facing readiness estimate and the
     * operator's handoff sheet are generated from one list. */
    var NEEDS = (C && C.setupNeeds) || {};

    function readiness(spec) {
        var auto = [], manual = [], gated = [];
        (spec.capabilities || []).forEach(function (c) {
            var cap = capById(c.id);
            if (!cap) return;
            var entry = { id: c.id, name: cap.name, group: cap.group,
                          needs: NEEDS[c.id] || [] };
            if (cap.gate) { entry.gate = cap.gate; gated.push(entry); }
            else if (entry.needs.length) manual.push(entry);
            else auto.push(entry);
        });
        var total = auto.length + manual.length + gated.length;
        return {
            auto: auto, manual: manual, gated: gated, total: total,
            // What can be stood up from the design alone, with no human input.
            percent: total ? Math.round((auto.length / total) * 100) : 0
        };
    }

    global.BlvkDesign = {
        SIGNALS: SIGNALS, SIGNAL_BY_ID: SIGNAL_BY_ID, ROLE_SYSTEMS: ROLE_SYSTEMS,
        NEEDS: NEEDS,
        rank: rank, design: design, adopt: adopt, vocabulary: vocabulary,
        readiness: readiness, relevantSuggestions: relevantSuggestions
    };
})(window);
