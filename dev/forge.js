/* The forge: turn a paid order into a configured agent.
 *
 * A build template is generic — a sequencer, a triage, a router. What makes it
 * *this customer's* agent is configuration: their labels, their routing table,
 * their chase cadence, their qualification criteria, their words. Producing
 * that configuration is the work the forge automates, and it is the difference
 * between an order arriving as a to-do list and arriving mostly finished.
 *
 * The rule, again, is that the model writes content and never structure. It is
 * given a strict per-template schema, and `accept()` discards every key it was
 * not asked for. A hallucinated config key would either be silently ignored by
 * the runtime or crash a capability at 2am; neither is acceptable, so it never
 * reaches the manifest.
 *
 * What the forge cannot invent — credentials, a real inbox sample, a phone
 * number, someone's actual price list — is reported as operator work rather
 * than guessed at. Overstating readiness is the one failure that would make the
 * whole pipeline dishonest.
 *
 * Reads window.BLVK_CATALOG / BlvkEngine / BlvkDesign. Exposes window.BlvkForge.
 */
(function (global) {
    "use strict";

    var C = global.BLVK_CATALOG;
    var E = global.BlvkEngine;
    var D = global.BlvkDesign;

    /* Per-capability config the forge is allowed to write, and the shape of it.
     * Anything not described here is not forgeable and falls to the operator. */
    var SCHEMA = {
        "email.triage": {
            keys: { labels: "array", samples: "array" },
            ask: 'labels: 4-7 categories this business\'s inbox actually contains, as ' +
                 '[name, description, route, priority(1-4), escalate(true/false)]. ' +
                 'samples: 3 realistic example messages as [text, expected_label].'
        },
        "email.draft": {
            keys: { purpose: "string", template: "string" },
            ask: 'purpose: one line describing the reply job. template: a short reply ' +
                 'skeleton using {name} and {detail} placeholders, in their voice.'
        },
        "email.route": {
            keys: { rules: "array", default: "string" },
            ask: 'rules: routing table as [{when:{label:"..."}, to:"queue-or-person", why:"...", notify:true/false}]. ' +
                 'default: where anything unmatched goes.'
        },
        "email.sla": { keys: { hours: "number" },
            ask: 'hours: how long a message may wait before somebody is told.' },
        "lead.qualify": {
            keys: { criteria: "array", hot_at: "number" },
            ask: 'criteria: what a good customer looks like here, as ' +
                 '[{field, op:"present|gte|lte|eq|contains|in", value, weight, why}]. ' +
                 'hot_at: the score at which a lead should reach a human.'
        },
        "lead.route": { keys: { rules: "array", default: "string" },
            ask: 'rules: where leads go by score, as [{when:{score:{op:"gte",value:70}}, to:"...", why:"..."}].' },
        "quote.followup": { keys: { steps: "array", subject: "string" },
            ask: 'steps: the chase cadence as [days_after, purpose_of_this_message]. ' +
                 'Three is usually right, and the last must make declining easy. subject: the email subject.' },
        "lead.nurture": { keys: { steps: "array", subject: "string" }, ask: "same shape as a follow-up cadence, but months not days" },
        "outreach.sequence": { keys: { steps: "array", subject: "string" }, ask: "same shape as a follow-up cadence" },
        "pay.chase": { keys: { steps: "array", subject: "string" }, ask: "the dunning cadence; tone escalates but stays polite" },
        "appt.remind": { keys: { steps: "array", subject: "string" }, ask: "confirmation and reminder cadence" },
        "appt.setting": { keys: { steps: "array", subject: "string" }, ask: "outbound booking cadence" },
        "support.status": { keys: { steps: "array", subject: "string" }, ask: "proactive status update cadence" },
        "onboard.chase": { keys: { steps: "array", subject: "string" }, ask: "chase cadence for a missing onboarding item" },
        "appt.book": { keys: { duration_min: "number", buffer_min: "number", days: "number" },
            ask: 'duration_min: typical job length. buffer_min: travel/turnaround. days: how far ahead to offer.' },
        "support.ticket": { keys: { labels: "array" },
            ask: 'labels: ticket categories as [name, description, route, priority(1-4), escalate].' },
        "onboard.run": { keys: { checklist: "array" },
            ask: 'checklist: the onboarding steps in order, as short strings.' },
        "doc.generate": { keys: { doc_kind: "string", template: "string" },
            ask: 'doc_kind: what document. template: a skeleton using {title} {ref} {date} {lines} {total}.' },
        "doc.parse": { keys: { fields: "object" },
            ask: 'fields: {field_name: "what it is"} for the fields worth extracting here.' },
        "data.analyze": { keys: { question: "string" },
            ask: 'question: the question this business actually wants answered about its numbers.' },
        "data.report": { keys: { group_by: "string", measure: "string" },
            ask: 'group_by and measure: the two columns their report should summarise.' },
        "data.alert": { keys: { thresholds: "array" },
            ask: 'thresholds: [{name, field, op:"gte|lte", value, measure:"sum|mean|max|min"}].' },
        "crm.hygiene": { keys: { required: "array", key: "string" },
            ask: 'required: fields a record must have. key: the field that identifies a duplicate.' },
        "crm.pipeline": { keys: { stale_days: "number" },
            ask: 'stale_days: how long a deal may sit in a stage before it is flagged.' },
        "workflow.multistep": { stepShape: "process", keys: { steps: "array" },
            ask: 'steps: the process as [{name, category, action:"create|send", collection}].' },
        "workflow.exception": { keys: { known: "object" },
            ask: 'known: {exception_name: "how to handle it"} for exceptions this business already knows about.' },
        "voice.inbound": { keys: { needed: "array", purpose: "string" },
            ask: 'needed: facts the caller must give. purpose: what the agent is trying to achieve on the call.' },
        "chan.webchat": { keys: {}, ask: "" },
        "knowledge.pack": { keys: { documents: "array" },
            ask: 'documents: [title, body] for facts stated in the order that the agent should answer from. ' +
                 'Only what the customer actually told us — never invented policy or prices.'
        },
        "research.web": { keys: { fields: "object" }, ask: 'fields: {name: "what to find out"} for a useful brief here.' },
        "email.thread": { keys: { needed: "array", purpose: "string" }, ask: 'needed: facts to collect. purpose: the job.' },
        "files.watch": { keys: { collection: "string" }, ask: 'collection: the folder to watch.' },
        "lead.capture": { keys: { collection: "string", key: "string" }, ask: 'collection and key for their CRM.' },
        "crm.sync": { keys: { collection: "string", key: "string" }, ask: 'collection and key for their CRM.' },
        "order.returns": { stepShape: "process", keys: { steps: "array" },
            ask: 'steps: their returns process as [{name, category, action:"create|send", collection}], in the order it actually happens here.' },
        "order.recover": { keys: { steps: "array", subject: "string" },
            ask: "steps: the checkout recovery cadence as [days_after, purpose]. Keep it short and offer help rather than a discount unless they said otherwise." },
        "order.track": { keys: { stall_days: "number" },
            ask: "stall_days: how many days without a carrier scan should count as stuck for this business." },
        "stock.watch": { keys: { lead_days: "number" },
            ask: "lead_days: their supplier lead time, so a warning arrives while there is still time to order." },
        "supplier.chase": { keys: { steps: "array", subject: "string" },
            ask: "steps: the supplier chase cadence as [days_after, purpose]. Firm but not rude; these are relationships." },
        "ship.eta": { keys: { steps: "array", subject: "string" },
            ask: "steps: the delivery update cadence as [days_after, purpose], covering only milestones a customer cares about." },
        "ship.claims": { stepShape: "process", keys: { steps: "array" },
            ask: 'steps: the claim process as [{name, category, action:"create|send", collection}].' },
        "review.request": { keys: { threshold: "number" },
            ask: "threshold: the star rating at or above which a customer is offered the public review page. Never propose blocking anyone from posting." },
        "renewal.watch": { keys: { warn_days: "number", noun: "string" },
            ask: "warn_days: how far ahead to raise a renewal. noun: what they call these (contract, retainer, subscription)." },
        "cert.expiry": { keys: { warn_days: "number", noun: "string" },
            ask: "warn_days: how far ahead to warn. noun: what they call these (certificate, licence, ticket, insurance)." },

        /* These five were falling to the operator for no reason: agentcore
         * already knows how to tailor them, because their template's fields are
         * read by the runtime. The key names below are agentcore's own, so what
         * gets written is what gets consumed. */
        "crm.logging": { keys: { required: "array" },
            ask: 'required: the fields an interaction record must carry to be worth having here, as short strings. Their fields, not every field the CRM offers.' },
        "browser.extract": { keys: { fields: "array" },
            ask: 'fields: the fields that must be present for an extraction to count as valid, as short strings. These are a tripwire: if the portal layout changes and one goes missing, extraction stops rather than returning a wrong answer.' },
        "browser.operate": { keys: { fields: "array" },
            ask: 'fields: the fields that must be present for the operation to be considered done, as short strings. Do not invent the steps of a portal nobody has seen; name only what a finished result must contain.' },
        "whitelabel": { keys: { surfaces: "array" },
            ask: 'surfaces: every place a customer of theirs will see this agent, as short strings (for example "quote emails", "booking page", "SMS sender name"). Never include BlvkWare in any of them.' },
        "lang.extra": { keys: { languages: "array" },
            ask: 'languages: the language codes this business actually serves, as short strings such as ["en","es"]. Only languages they told us about.' },

        /* Two of the dashboard extensions carry a real decision rather than a
         * setting: which number this business watches, and which figures it is
         * willing to show its own customers. Both are answerable from what they
         * told us, so neither should reach the operator as a question. */
        "dash.metric": { keys: { name: "string", measure: "string" },
            ask: 'name: what this business calls the number it watches, in their words. measure: which figure on the board it maps to, one of handled, waiting, held_back, escalated, prepared, sent, recovered.' },
        "dash.share": { keys: { published: "array" },
            ask: 'published: the figures they would be willing to show their own customers, as short strings from handled, waiting, held_back, escalated, prepared, sent, recovered. When in doubt publish less; this is a read-only link that leaves the building.' }
    };

    function forgeable(capId) { return !!SCHEMA[capId]; }

    /* Which capabilities in this order the forge can configure. */
    function plan(spec) {
        var can = [], cannot = [];
        (spec.capabilities || []).forEach(function (c) {
            var id = c.id || c;
            var cap = E.capById(id);
            if (!cap) return;
            (forgeable(id) ? can : cannot).push({
                id: id, name: cap.name, group: cap.group,
                ask: (SCHEMA[id] || {}).ask || "",
                needs: (C.setupNeeds && C.setupNeeds[id]) || []
            });
        });
        return { can: can, cannot: cannot };
    }

    /* The instruction. The model is told exactly which keys it may fill. */
    function instruction(spec, business) {
        var p = plan(spec);
        var lines = [];
        lines.push("Configure a working agent for this business.");
        lines.push("");
        lines.push("BUSINESS: " + (business.business || "unnamed"));
        lines.push("WHAT THEY DO: " + (business.whatWeDo || "not stated"));
        lines.push("THE JOB, IN THEIR WORDS: " + (business.jobDescription || "not stated"));
        lines.push("MUST NEVER DO WITHOUT ASKING: " + (business.neverDo || "not stated"));
        lines.push("ROLE: " + ((spec.role || {}).name || ""));
        lines.push("");
        lines.push("Return STRICT JSON: an object whose keys are the capability ids below, " +
                   "each holding only the keys named for it.");
        lines.push("");
        p.can.forEach(function (c) {
            if (!c.ask) return;
            lines.push('"' + c.id + '"  (' + c.name + ')');
            lines.push("    " + c.ask);
        });
        lines.push("");
        lines.push("RULES");
        lines.push("- Write in the customer's own vocabulary, using their trade's words.");
        lines.push("- Never invent a price, a policy, a guarantee or a fact they did not state.");
        lines.push("- Never add a key that was not named above; it will be discarded.");
        lines.push("- Copy should be plain and short. No marketing voice, no filler.");
        lines.push("- Honour the 'must never do' rule in every cadence and template you write.");
        lines.push("- Output raw JSON only. First character must be {");
        return lines.join("\n");
    }

    /* Validate one capability's forged config against its schema. */
    function acceptOne(capId, raw) {
        var schema = SCHEMA[capId];
        if (!schema || !raw || typeof raw !== "object") return { config: null, dropped: [] };
        var out = {}, dropped = [];
        Object.keys(raw).forEach(function (k) {
            var want = schema.keys[k];
            if (!want) { dropped.push(capId + "." + k); return; }
            var v = raw[k];
            var ok = (want === "array") ? Array.isArray(v)
                   : (want === "object") ? (v && typeof v === "object" && !Array.isArray(v))
                   : (want === "number") ? (typeof v === "number" && isFinite(v))
                   : (typeof v === "string" && v.length > 0);
            if (ok) out[k] = v; else dropped.push(capId + "." + k + " (wrong type)");
        });

        // Two different kinds of capability carry a `steps` key and they are not
        // the same shape: a cadence is [days, purpose] pairs, a process is
        // [{name, category, action}] objects. Validating both against the
        // cadence shape silently threw away every process the forge wrote —
        // which looked like the model failing rather than the validator.
        if (out.steps) {
            var wantProcess = schema.stepShape === "process";
            var steps = out.steps.filter(function (s) {
                if (wantProcess) {
                    return s && typeof s === "object" && !Array.isArray(s) &&
                           typeof s.name === "string" && typeof s.category === "string";
                }
                return Array.isArray(s) && s.length >= 2 &&
                       typeof s[0] === "number" && typeof s[1] === "string";
            });
            if (steps.length) out.steps = steps;
            else {
                delete out.steps;
                dropped.push(capId + ".steps (not a valid " +
                             (wantProcess ? "process" : "cadence") + ")");
            }
        }
        if (out.labels) {
            var labels = out.labels.filter(function (l) {
                return Array.isArray(l) && l.length >= 2 &&
                       typeof l[0] === "string" && typeof l[1] === "string";
            }).map(function (l) {
                return [l[0], l[1], l[2] || "", typeof l[3] === "number" ? l[3] : 3, !!l[4]];
            });
            if (labels.length >= 2) out.labels = labels;
            else { delete out.labels; dropped.push(capId + ".labels (too few usable)"); }
        }
        if (out.samples) {
            out.samples = out.samples.filter(function (s) {
                return Array.isArray(s) && s.length >= 2 && typeof s[0] === "string";
            });
            if (!out.samples.length) delete out.samples;
        }
        return { config: Object.keys(out).length ? out : null, dropped: dropped };
    }

    function accept(raw) {
        var config = {}, dropped = [], forged = [];
        Object.keys(raw || {}).forEach(function (capId) {
            if (!E.capById(capId)) { dropped.push("unknown capability: " + capId); return; }
            var got = acceptOne(capId, raw[capId]);
            dropped = dropped.concat(got.dropped);
            if (got.config) { config[capId] = got.config; forged.push(capId); }
        });
        return { config: config, forged: forged, dropped: dropped };
    }

    /* Knowledge is handled separately: it is content, not configuration, and it
     * goes into the agent's pack rather than a capability's settings. */
    function knowledge(config) {
        var pack = (config["knowledge.pack"] || {}).documents || [];
        return pack.filter(function (d) {
            return Array.isArray(d) && d.length >= 2 && d[0] && d[1];
        }).map(function (d) { return { title: String(d[0]), body: String(d[1]) }; });
    }

    /* What the forge achieved, measured the same way the operator's handoff
     * sheet measures it — so the number a buyer sees and the number on the
     * build sheet are the same number. */
    function outcome(spec, config) {
        var withConfig = JSON.parse(JSON.stringify(spec));
        withConfig.config = config;
        var before = D.readiness(spec);
        var after = D.readiness(spec);

        // A capability whose setup need is now supplied by forged config counts
        // as standing. Anything needing a credential, a real sample or a human
        // decision never does, whatever the model produced.
        // A credential is only one of the things a model cannot supply. Real
        // data, access to a live system, a human being and the customer's own
        // existing material are equally unforgeable, and a capability whose
        // acceptance test needs one of them is not standing however good the
        // configuration is. email.triage is the case that exposed this: it is
        // configured from invented example messages, but its acceptance test
        // needs fifty of the owner's real ones, so it cannot pass yet.
        var UNFORGEABLE = new RegExp([
            "credential", "account", "registration", "verification",
            "phone number", "domain", "API documentation",   // secrets and identifiers
            "real inbox", "real transaction", "a month of", "backlog",
            "sample of real",                                // data that has to exist
            "read connection", "access to", "walkthrough",   // access to a live system
            "native reviewer", "reviewer",                   // a person
            "documentation", "help centre", "brand assets", "price list"
        ].join("|"), "i");

        var stood = [], remaining = [];
        after.manual.forEach(function (c) {
            var supplied = !!config[c.id];
            var blocked = (c.needs || []).some(function (n) { return UNFORGEABLE.test(n); });
            if (supplied && !blocked) stood.push(c); else remaining.push(c);
        });

        var total = after.total;
        var standing = after.auto.length + stood.length;
        return {
            spec: withConfig,
            before: before.percent,
            after: total ? Math.round((standing / total) * 100) : 0,
            standing: standing, total: total,
            forgedNow: stood, stillManual: remaining, gated: after.gated
        };
    }

    global.BlvkForge = {
        SCHEMA: SCHEMA, forgeable: forgeable, plan: plan,
        instruction: instruction, accept: accept, acceptOne: acceptOne,
        knowledge: knowledge, outcome: outcome
    };
})(window);
