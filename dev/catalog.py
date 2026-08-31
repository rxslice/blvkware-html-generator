# -*- coding: utf-8 -*-
"""The agent catalog: the single source of truth for what BlvkWare sells.

Everything downstream is generated from this file — the buyer-facing configurator
at /hire/, the public catalog page at /agents/, and the internal fulfilment
console. Nothing else is allowed to hold a price or a capability list.

The reason is not tidiness. The configurator quotes a fixed price the buyer pays
before any work starts, and the fulfilment console tells the operator what to
assemble for that money. If those two could drift by so much as one component,
the difference comes straight out of margin on a real order. Generating both from
here makes drift impossible rather than merely unlikely.

Vocabulary
----------
capability  an atom of what an agent can do. Has a price when added beyond a
            role's core set, a complexity weight, dependencies, the integration
            categories it implies, a build template, and — importantly — an
            acceptance line that can actually be tested at inspection.
role        a named job, defined as a bundle of core capabilities plus a set of
            suggested ones. This is what a buyer chooses first.
tier        Operator or Deputy. DERIVED from the configured scope, never picked
            by the buyer, so a scope that is really a Deputy cannot be bought at
            Operator money.
"""

import json

# --------------------------------------------------------------------------
# Tiers. Prices approved 2026-08-28. Included counts are what the base buys;
# anything past them is charged as a component.
# --------------------------------------------------------------------------

TIERS = {
    1: {
        "key": 1,
        "name": "Operator",
        "label": "Operator · Tier I",
        "build": 3500,
        "ops": 349,
        "opsAnnual": 3490,
        "days": "10 business days",
        "buildDays": 10,
        "actions": 2000,
        "systems": 3,
        "channels": 2,
        # What the base includes is `systems`/`channels`. A Tier I agent can
        # stretch past that for the published per-connection price — without the
        # stretch, ticking a fourth system would jump a buyer from $3,500 to
        # $9,500 in one click, which reads as a trap rather than a tier.
        "maxSystems": 5,
        "maxChannels": 4,
        "blurb": "Owns one job, start to finish.",
    },
    2: {
        "key": 2,
        "name": "Deputy",
        "label": "Deputy · Tier II",
        "build": 9500,
        "ops": 899,
        "opsAnnual": 8990,
        "days": "25 business days",
        "buildDays": 25,
        "actions": 10000,
        "systems": 8,
        "channels": 6,
        "maxSystems": 14,
        "maxChannels": 8,
        "blurb": "Owns an entire function, with judgment and escalation.",
    },
}

TRIAL = 750

# --------------------------------------------------------------------------
# Tier derivation thresholds.
#
# These are not guesses. Measured across the catalog, a Tier I role loaded with
# every capability it suggests reaches at most 18 weight and 5 capability
# groups; a Tier II role's *core* alone sits at 11-14 weight and 3-4 groups.
# Weight and breadth therefore overlap and neither separates the tiers alone —
# so the thresholds sit deliberately ABOVE what a fully-suggested Tier I
# configuration reaches. The effect is that a Tier I role priced at its own
# recommended scope always stays Tier I, and only a buyer who genuinely goes
# past it escalates. Re-run dev/thresholds.py after changing any role or weight.
# --------------------------------------------------------------------------
TIER2_WEIGHT = 20     # measured Tier I ceiling with all suggestions: 18
TIER2_GROUPS = 6      # measured Tier I ceiling with all suggestions: 5
SPLIT_WEIGHT = 30     # past this it is honestly two agents, not one

PRICING = {
    "trial": TRIAL,
    "extraSystem": 750,
    "extraChannel": 950,
    "rushPct": 0.40,
    "secondAgentPct": 0.30,
    "overagePer1000": 75,
    "prebuyPer1000": 30,
    "annualMonths": 10,
    "buyoutMultiple": 12,
    "tier2Weight": TIER2_WEIGHT,
    "tier2Groups": TIER2_GROUPS,
    "splitWeight": SPLIT_WEIGHT,
}

# --------------------------------------------------------------------------
# Volume. Buyers cannot estimate "actions", but they can estimate how often the
# job happens. The bands translate. Pre-buying is cheaper than overage on
# purpose — it converts a variable cost into a known one for both sides.
# --------------------------------------------------------------------------

VOLUME = [
    {"id": "light",    "label": "Under 50 a week",      "actions": 2000,  "hint": "a small team, or a job that happens a few times a day"},
    {"id": "standard", "label": "50 to 200 a week",     "actions": 6000,  "hint": "the usual answer for an established small business"},
    {"id": "heavy",    "label": "200 to 600 a week",    "actions": 15000, "hint": "high volume, or several locations"},
    {"id": "intense",  "label": "More than 600 a week", "actions": 40000, "hint": "this is a Deputy's workload"},
]

# --------------------------------------------------------------------------
# Integration categories. These drive the "what do you run?" question and land
# in the manifest as the list of things to wire on days two and three.
# --------------------------------------------------------------------------

INTEGRATIONS = [
    {"id": "email",      "name": "Email",                "eg": "Google Workspace, Microsoft 365, Zoho"},
    {"id": "calendar",   "name": "Calendar / scheduling", "eg": "Google Calendar, Outlook, Calendly, Cal.com"},
    {"id": "crm",        "name": "CRM",                  "eg": "HubSpot, Pipedrive, Salesforce, Zoho, Go High Level"},
    {"id": "fsm",        "name": "Field service / jobs", "eg": "Jobber, ServiceTitan, Housecall Pro"},
    {"id": "accounting", "name": "Accounting",           "eg": "QuickBooks, Xero, FreshBooks"},
    {"id": "payments",   "name": "Payments",             "eg": "Stripe, Square, PayPal"},
    {"id": "helpdesk",   "name": "Help desk / tickets",  "eg": "Zendesk, Freshdesk, Intercom"},
    {"id": "pm",         "name": "Project / task",       "eg": "Asana, Monday, ClickUp, Trello, Jira"},
    {"id": "chatops",    "name": "Team chat",            "eg": "Slack, Microsoft Teams"},
    {"id": "storage",    "name": "Files / storage",      "eg": "Google Drive, Dropbox, SharePoint"},
    {"id": "sheets",     "name": "Spreadsheets",         "eg": "Google Sheets, Excel"},
    {"id": "db",         "name": "Database / warehouse", "eg": "Postgres, MySQL, BigQuery, Airtable"},
    {"id": "ecom",       "name": "E-commerce",           "eg": "Shopify, WooCommerce"},
    {"id": "telephony",  "name": "Phone system",         "eg": "RingCentral, Dialpad, Twilio, a plain mobile number"},
    {"id": "portal",     "name": "A web portal with no API", "eg": "a supplier, insurer, council or bank site you log into by hand"},
    {"id": "inventory",  "name": "Inventory / stock",    "eg": "Cin7, Katana, Zoho Inventory, a spreadsheet"},
    {"id": "carrier",    "name": "Shipping / carriers",  "eg": "ShipStation, Shippo, UPS, FedEx"},
    {"id": "custom",     "name": "Something in-house",   "eg": "your own software, or an API you own"},
]

CHANNELS = [
    {"id": "email",    "name": "Email",              "gate": None},
    {"id": "webchat",  "name": "Web chat",           "gate": None},
    {"id": "inbox",    "name": "A shared inbox",     "gate": None},
    {"id": "chatops",  "name": "Slack or Teams",     "gate": None},
    {"id": "voicein",  "name": "Inbound phone",      "gate": None,    "cap": "voice.inbound"},
    {"id": "sms",      "name": "SMS",                "gate": "10dlc", "cap": "chan.sms"},
    {"id": "whatsapp", "name": "WhatsApp",           "gate": "meta"},
    {"id": "voiceout", "name": "Outbound phone",     "gate": None,    "cap": "voice.outbound"},
]

GATES = {
    "10dlc": {
        "short": "US carrier registration required — weeks, not days",
        "long": "Texting your customers from a US business number requires A2P "
                "10DLC registration with the carriers. Part of it is a manual "
                "review that no supplier can hurry, so budget weeks rather than "
                "days. Everything else in your agent goes live on schedule; SMS "
                "switches on when the registration clears, at no extra cost.",
    },
    "meta": {
        "short": "Meta business verification required — usually days",
        "long": "WhatsApp Business messaging needs Meta to verify the business. "
                "It is normally days rather than weeks, but it is outside our "
                "control and so is not promised inside the delivery window.",
    },
}

# --------------------------------------------------------------------------
# Capabilities.
#
# price   what it costs when added beyond a role's core set
# ops     monthly adder, for capabilities with a real recurring cost
# weight  complexity points, used to derive the tier
# needs   capabilities that must be present for this one to function
# integ   integration categories this implies
# tpl     the fulfilment template to assemble
# accept  the line the operator tests at inspection before delivery
# --------------------------------------------------------------------------

def _c(cid, group, name, blurb, price, weight, ops=0, needs=(), integ=(),
       tpl=None, accept="", gate=None, judgment=False):
    return {
        "id": cid, "group": group, "name": name, "blurb": blurb,
        "price": price, "ops": ops, "weight": weight,
        "needs": list(needs), "integ": list(integ),
        "tpl": tpl or ("tpl-" + cid.replace(".", "-")),
        "accept": accept, "gate": gate, "judgment": judgment,
    }


CAPABILITIES = [

    # ---- Email and messaging -------------------------------------------
    _c("email.triage", "Email", "Email triage",
       "Reads every incoming message, works out what it is and how urgent it is, and sorts it.",
       850, 2, integ=["email"],
       accept="Given 50 real messages from the last month, classification matches the owner's own sorting on at least 45."),
    _c("email.draft", "Email", "Reply drafting",
       "Writes the reply, in your voice, using your prices and policies rather than generic filler.",
       950, 2, needs=["email.triage"], integ=["email"],
       accept="Ten drafts across the five most common message types are sendable with no edit or a trivial one."),
    _c("email.route", "Email", "Routing and assignment",
       "Sends each message to the right person or queue with the context already attached.",
       650, 1, needs=["email.triage"], integ=["email"],
       accept="Every routing rule in the job description fires correctly against a replayed week."),
    _c("email.sla", "Email", "Response deadlines",
       "Tracks how long anything has been waiting and escalates before a customer has to chase.",
       550, 1, needs=["email.triage"], integ=["email"],
       accept="A message left unanswered past the agreed threshold produces an escalation, every time."),
    _c("email.thread", "Email", "Conversation memory",
       "Holds a multi-message conversation without losing the thread or repeating itself.",
       750, 2, needs=["email.triage"], integ=["email"],
       accept="A five-turn exchange stays coherent and never re-asks something already answered."),
    _c("email.cleanup", "Email", "Backlog clearance",
       "Works through the existing pile once, so you start from zero instead of from four hundred.",
       650, 1, needs=["email.triage"], integ=["email"],
       accept="The historic backlog is classified and dispositioned, with a written summary of what was found."),

    _c("chan.webchat", "Channels", "Web chat",
       "A chat widget on your site that the agent actually staffs.",
       950, 2, accept="A visitor conversation completes end to end on a staging page without a human."),
    _c("chan.chatops", "Channels", "Slack or Teams",
       "It works where your team already talks, and can be asked things directly.",
       950, 1, integ=["chatops"],
       accept="The agent responds in-channel and its actions appear in the audit log."),
    _c("chan.sms", "Channels", "SMS",
       "Texts your customers from a business number and acts on what they text back.",
       950, 2, ops=39, gate="10dlc", integ=["telephony"],
       accept="A round-trip text conversation completes, and opt-outs are honoured immediately and permanently."),
    _c("chan.whatsapp", "Channels", "WhatsApp",
       "The same conversation on WhatsApp, for the customers who live there.",
       950, 2, ops=39, gate="meta",
       accept="A round-trip WhatsApp conversation completes and opt-outs are honoured."),
    _c("voice.inbound", "Channels", "Answers the phone",
       "Picks up in a real voice, understands the call, and takes the actions that come out of it.",
       2500, 4, ops=99, integ=["telephony"],
       accept="Ten test calls covering the agreed scenarios are handled without a human, including one it must escalate."),
    _c("voice.outbound", "Channels", "Places calls",
       "Rings customers to confirm, remind, chase or follow up, and records the outcome.",
       2900, 5, ops=99, needs=["voice.inbound"], integ=["telephony"], judgment=True,
       accept="Outbound calls place, record an outcome against the right record, and respect calling-hour rules."),

    # ---- Lead and revenue ----------------------------------------------
    _c("lead.capture", "Leads", "Lead capture",
       "Catches every enquiry from every source and puts it in one place, with nothing lost.",
       650, 1, integ=["crm"],
       accept="Enquiries from each configured source appear as records within a minute, with no duplicates."),
    _c("lead.enrich", "Leads", "Lead enrichment",
       "Fills in what the enquiry didn't tell you, from public sources, before anyone reads it.",
       850, 2, needs=["lead.capture"],
       accept="Enrichment runs on every new lead and is marked clearly as inferred rather than stated."),
    _c("lead.qualify", "Leads", "Lead qualification",
       "Asks the qualifying questions and scores the lead against what a good customer looks like for you.",
       950, 3, needs=["lead.capture"], judgment=True,
       accept="Scoring against 30 historic leads matches the owner's own judgment on at least 25."),
    _c("lead.route", "Leads", "Lead routing",
       "Hot ones to you immediately, the rest handled without you.",
       450, 1, needs=["lead.qualify"],
       accept="Every routing branch fires correctly on a replayed set of historic leads."),
    _c("lead.nurture", "Leads", "Long-game nurture",
       "Keeps in touch with the ones who said not yet, so they come back to you and not a competitor.",
       1100, 3, needs=["lead.capture"], judgment=True,
       accept="A not-now lead receives the agreed sequence, and it stops the moment they respond."),
    _c("quote.followup", "Leads", "Quote follow-up",
       "Chases every quote until the customer answers one way or the other, then stops.",
       950, 2, judgment=True,
       accept="A quote is chased on the agreed schedule, stops instantly on any reply, and records the reason it was lost."),
    _c("outreach.sequence", "Leads", "Outbound sequences",
       "Runs a multi-step outreach sequence to a list you supply, and stops on any reply.",
       1100, 3, judgment=True,
       accept="Sequences send on schedule, halt on reply, honour suppression, and every send is attributable."),

    # ---- Appointments ---------------------------------------------------
    _c("appt.book", "Appointments", "Booking",
       "Offers real slots that respect travel time and job length, then books them.",
       950, 2, integ=["calendar"],
       accept="Offered slots never conflict, never breach buffer rules, and land on the right calendar."),
    _c("appt.remind", "Appointments", "Reminders and confirmations",
       "Confirms, then reminds at the intervals that actually reduce no-shows.",
       450, 1, needs=["appt.book"], integ=["calendar"],
       accept="Every booking produces the agreed confirmation and reminder sequence."),
    _c("appt.reschedule", "Appointments", "Rescheduling and no-shows",
       "Handles the reschedule conversation without you, and fills a cancellation from the waiting list.",
       850, 2, needs=["appt.book"], integ=["calendar"], judgment=True,
       accept="A reschedule request completes without a human, and a cancelled slot is offered onward."),
    _c("appt.setting", "Appointments", "Outbound appointment setting",
       "Works a list and books meetings into the calendar, rather than waiting to be contacted.",
       1200, 3, needs=["appt.book"], integ=["calendar"], judgment=True,
       accept="A worked list produces booked meetings with correct records and honoured opt-outs."),

    # ---- CRM and systems ------------------------------------------------
    _c("crm.sync", "Systems", "CRM read and write",
       "Reads and updates your CRM itself, so records are right without anyone typing.",
       1200, 3, integ=["crm"],
       accept="Records created and updated by the agent match the field mapping exactly, with no orphan records."),
    _c("crm.logging", "Systems", "Interaction logging",
       "Every call, message and outcome logged against the right record, automatically.",
       500, 1, needs=["crm.sync"], integ=["crm"],
       accept="Every agent interaction appears on the correct record within a minute."),
    _c("crm.hygiene", "Systems", "CRM hygiene",
       "Deduplicates, normalises and fills the gaps, continuously, instead of never.",
       900, 2, needs=["crm.sync"], integ=["crm"],
       accept="A dry run over the live database reports duplicates and fixes, and no merge happens without approval."),
    _c("crm.pipeline", "Systems", "Pipeline discipline",
       "Nothing sits in a stage forever. It moves work along or tells you why it can't.",
       850, 2, needs=["crm.sync"], integ=["crm"], judgment=True,
       accept="Stale records are surfaced on the agreed threshold and progressed or escalated."),
    _c("workflow.multistep", "Systems", "Multi-step process",
       "Runs a whole process across several systems, in order, without a person shepherding it.",
       1800, 4, judgment=True,
       accept="The documented process completes end to end on real data, in the right order, at least three times."),
    _c("workflow.exception", "Systems", "Exception handling",
       "When something doesn't fit the process, it works it out or escalates — it doesn't just stall.",
       850, 3, needs=["workflow.multistep"], judgment=True,
       accept="Each exception listed in the job description is either resolved or escalated with the reason attached."),
    _c("browser.operate", "Systems", "Operates web apps with no API",
       "Logs into the portal and does the work by hand, the way a person would, when there is no other way in.",
       2400, 5, ops=120, integ=["portal"],
       accept="The task completes on the live portal on three consecutive days, and a UI change produces an alert rather than silent failure."),
    _c("browser.extract", "Systems", "Portal data extraction",
       "Pulls what you need out of a system that won't export it.",
       1400, 3, ops=60, integ=["portal"],
       accept="Extracted data matches a hand-checked sample exactly, and a format change raises an alert."),
    _c("files.watch", "Systems", "Watches files and folders",
       "Notices when something lands in a folder or a drive, and acts on it.",
       550, 1, integ=["storage"],
       accept="A file arriving in the watched location triggers the agreed action within the agreed window."),
    _c("api.custom", "Systems", "Your own software",
       "Connects to the in-house system nobody else integrates with.",
       1400, 3, integ=["custom"],
       accept="Read and write against the customer's API succeed, with error handling and retries proven."),

    # ---- Documents and money --------------------------------------------
    _c("doc.generate", "Documents", "Document generation",
       "Produces the quote, contract, invoice or report itself, as a finished PDF.",
       850, 2,
       accept="Generated documents match the approved template exactly, with correct figures on ten samples."),
    _c("doc.parse", "Documents", "Reads incoming documents",
       "Opens the PDF, the invoice, the form, and pulls out what matters.",
       950, 3,
       accept="Extraction from twenty real documents matches a hand-checked result on the agreed fields."),
    _c("pay.collect", "Money", "Payment collection",
       "Sends payment links, takes deposits and issues invoices.",
       1200, 3, integ=["payments"],
       accept="A test transaction completes end to end and reconciles against the right record."),
    _c("pay.chase", "Money", "Chases what's unpaid",
       "Reminds before due, on due, and after — escalating tone gradually, stopping the moment it's paid.",
       850, 2, needs=["pay.collect"], integ=["payments"], judgment=True,
       accept="The dunning sequence runs on schedule and halts within minutes of payment."),
    _c("recon.match", "Money", "Reconciliation",
       "Matches what came in against what was owed, and flags what doesn't line up.",
       1600, 4, needs=["pay.collect"], integ=["accounting"],
       accept="A month of real transactions reconciles, with every discrepancy listed and explained."),

    # ---- Data and intelligence ------------------------------------------
    _c("data.collect", "Data", "Data collection",
       "Pulls the numbers out of the systems they're trapped in, on a schedule.",
       850, 2, integ=["sheets"],
       accept="Scheduled collection runs produce complete datasets, and a failed source raises an alert."),
    _c("data.analyze", "Data", "Analysis and answers",
       "Answers questions about your own numbers, in plain language, with the working shown.",
       1200, 3, needs=["data.collect"], judgment=True,
       accept="Ten questions answered against known data are correct and cite the rows they came from."),
    _c("data.viz", "Data", "Charts and visualisation",
       "Turns the answer into something you can actually look at.",
       1250, 3, ops=49, needs=["data.collect"],
       accept="Charts render correctly on desktop and mobile and match the underlying figures."),
    _c("data.report", "Data", "Scheduled reports",
       "The Monday morning report writes and sends itself.",
       650, 1, needs=["data.collect"],
       accept="The report generates and delivers on schedule for two consecutive cycles."),
    _c("data.alert", "Data", "Threshold alerts",
       "Tells you the moment a number goes somewhere it shouldn't.",
       450, 1, needs=["data.collect"],
       accept="Each configured threshold fires correctly, and does not fire when it shouldn't."),
    _c("research.web", "Data", "Research",
       "Goes and finds out — about a prospect, a competitor, a supplier, a market.",
       850, 2, judgment=True,
       accept="Five research briefs are accurate, sourced, and clearly separate fact from inference."),

    # ---- Support --------------------------------------------------------
    _c("support.answer", "Support", "Answers support questions",
       "Answers from your documentation rather than from the internet, and says so when it doesn't know.",
       950, 2, needs=["knowledge.pack"], integ=["helpdesk"], judgment=True,
       accept="Twenty real questions are answered correctly, and an unknown produces an escalation rather than a guess."),
    _c("support.status", "Support", "Proactive status updates",
       "Tells the customer where things are before they have to ask.",
       650, 1,
       accept="Status updates send at each agreed milestone against a replayed job."),
    _c("support.ticket", "Support", "Ticket handling",
       "Opens, updates, escalates and closes tickets in the system you already use.",
       850, 2, integ=["helpdesk"],
       accept="Full ticket lifecycle completes in the live help desk, with correct priority and ownership."),

    # ---- Onboarding -----------------------------------------------------
    _c("onboard.run", "Onboarding", "Runs the checklist",
       "Takes a new client or new hire through onboarding in order, the same way every time.",
       950, 2, integ=["pm"],
       accept="A full onboarding run completes with every step recorded and nothing skipped."),
    _c("onboard.chase", "Onboarding", "Chases what's missing",
       "Collects the documents and details, and keeps asking the humans who owe them.",
       650, 1, needs=["onboard.run"],
       accept="A missing item produces the agreed chase sequence and stops on receipt."),

    # ---- Control, trust and extras --------------------------------------
    _c("knowledge.pack", "Control", "Knowledge pack",
       "Your prices, policies, documents and SOPs loaded in, so it answers from your business.",
       900, 2,
       accept="Twenty questions drawn from the source material are answered from it, with the source cited."),
    _c("approval.console", "Control", "Approval console",
       "Set the line it stops at — by value, by kind of action, by rule. Every agent already comes with the queue itself; this is the control over what has to land in it and what may go straight out.",
       1100, 2,
       accept="Actions above the configured threshold queue rather than execute, and approval releases them correctly."),
    _c("dashboard", "Control", "Reporting dashboard",
       "Figures rather than a log: what it handled, what it recovered, where it escalated, reconciled against the audit trail. Every agent already shows you what it did; this is the version you can report from.",
       1400, 3,
       accept="Dashboard figures reconcile against the audit log for a full week."),
    _c("whitelabel", "Control", "White-label surfaces",
       "Every page and message it touches carries your domain and your branding.",
       1500, 2,
       accept="No BlvkWare branding appears on any customer-facing surface, and links resolve on the customer's domain."),
    _c("lang.extra", "Control", "Additional language",
       "The same judgment and the same tone, in another language.",
       600, 2,
       accept="Ten exchanges in the additional language are accurate and hold the agreed tone."),
    _c("export.api", "Control", "Data export and API",
       "Everything it knows, available to your other systems, on demand or on a schedule.",
       700, 2,
       accept="Export returns complete, well-formed data and the endpoint is authenticated."),
    _c("staging", "Control", "Staging environment",
       "A safe copy to try changes against before they reach live customers.",
       500, 1,
       accept="A change deploys to staging, is exercised, and promotes to live without touching live data first."),
    _c("training", "Control", "Team training",
       "Ninety minutes, remote, recorded, so your team knows how to work with it and when to overrule it.",
       450, 0,
       accept="Session delivered and the recording handed over."),
    # ---- Orders ---------------------------------------------------------
    # "Where is my order" is the highest-volume support ticket in ecommerce by
    # a wide margin, and returns are the most labour-intensive thing in one.
    # Both are worth an agent. Checkout recovery is here because merchants ask
    # for it and it costs nothing to compose from the sequencer -- but it is a
    # crowded market served well by cheap dedicated tools, so no role is built
    # around it and nobody should be sold it as a differentiator.
    _c("order.status", "Orders", "Answers where my order is",
       "Looks up the real order and the real tracking, and answers the question people ask most.",
       950, 2, integ=["ecom"],
       accept="Twenty real order enquiries are answered from the actual order record, and an order it cannot find escalates instead of guessing."),
    _c("order.track", "Orders", "Watches every shipment",
       "Follows each parcel and spots the ones that have stopped moving before the customer does.",
       1100, 2, ops=49, needs=["order.status"], integ=["carrier"],
       accept="A shipment with no movement past the agreed window is flagged, and a delivered one is not."),
    _c("order.returns", "Orders", "Runs returns and exchanges",
       "Takes the return from request to label to refund, in order, without a person shepherding it.",
       1400, 3, integ=["ecom"], judgment=True,
       accept="A return completes end to end on real data, and anything outside the returns policy is escalated rather than approved."),
    _c("order.recover", "Orders", "Recovers abandoned checkouts",
       "Follows up the carts that were nearly orders, then stops the moment they buy or ask you to.",
       950, 2, integ=["ecom"],
       accept="A recovery sequence sends on schedule, stops instantly on purchase or opt-out, and never messages the same cart twice."),

    # ---- Inventory ------------------------------------------------------
    # Framed as operating the stock system they already run. Replacing an
    # inventory system means fighting ERP, which a one-person shop loses.
    _c("stock.watch", "Inventory", "Watches stock before it runs out",
       "Knows what is running down, how fast, and says so while there is still time to order.",
       1200, 3, ops=49, integ=["inventory"],
       accept="An item projected to run out inside the agreed lead time raises exactly one alert, and a healthy item raises none."),
    _c("stock.reconcile", "Inventory", "Reconciles stock across channels",
       "Compares what each system thinks you have and surfaces every difference rather than picking a winner.",
       1600, 3, needs=["stock.watch"], integ=["inventory", "ecom"],
       accept="A full comparison lists every discrepancy with both figures, and no count is silently overwritten."),
    _c("supplier.chase", "Inventory", "Chases suppliers",
       "Purchase orders nobody confirmed and deliveries that are late, chased on a schedule.",
       850, 2, judgment=True,
       accept="An unconfirmed order is chased on the agreed cadence and stops the moment the supplier replies."),

    # ---- Logistics ------------------------------------------------------
    _c("ship.eta", "Logistics", "Tells customers where things are",
       "Proactive delivery updates, so the customer hears from you before they have to ask.",
       950, 2, needs=["order.track"],
       accept="Each agreed milestone produces one update, and a delivered order stops producing them."),
    _c("ship.claims", "Logistics", "Claims for lost and damaged",
       "Assembles the evidence and files the carrier claim, which is money most businesses quietly write off.",
       1400, 3, integ=["carrier"], judgment=True,
       accept="A claim is assembled with every required document, and one missing a document is held rather than filed."),

    # ---- Retention and compliance ---------------------------------------
    _c("review.request", "Leads", "Asks for the review",
       "Asks after every finished job. Happy customers reach your review page; unhappy ones reach you first.",
       850, 2, judgment=True,
       accept="Every customer is asked the same question, a high rating is offered the public review page, a low one alerts the owner within the minute, and nobody is prevented from posting."),
    _c("renewal.watch", "Compliance", "Never misses a renewal",
       "Contracts, subscriptions and retainers, chased before they lapse rather than after.",
       850, 2, judgment=True,
       accept="A renewal inside the agreed window is actioned once, and one already renewed is left alone."),
    _c("cert.expiry", "Compliance", "Tracks certificates and licences",
       "Insurance, tickets, licences and accreditations, with the chasing done before they expire.",
       750, 2,
       accept="An expiry inside the warning window raises exactly one escalation, and it does not repeat until the record changes."),
]


CAP_BY_ID = dict((c["id"], c) for c in CAPABILITIES)

# Sanity: every dependency must exist, or the configurator can silently ship a
# capability that cannot function.
for _c_ in CAPABILITIES:
    for _n in _c_["needs"]:
        assert _n in CAP_BY_ID, "%s needs unknown capability %s" % (_c_["id"], _n)

CAP_GROUPS = []
for _c_ in CAPABILITIES:
    if _c_["group"] not in CAP_GROUPS:
        CAP_GROUPS.append(_c_["group"])


# --------------------------------------------------------------------------
# Roles. `core` is included in the tier base price. `suggested` is pre-ticked
# but removable — this is where most of the configurator's revenue comes from,
# and where a buyer who wants less can genuinely get it cheaper.
# --------------------------------------------------------------------------

def _r(rid, family, name, oneLine, problem, core, suggested=(), minTier=1):
    return {
        "id": rid, "family": family, "name": name, "oneLine": oneLine,
        "problem": problem, "core": list(core), "suggested": list(suggested),
        "minTier": minTier,
    }


ROLES = [

    # ---- Communication --------------------------------------------------
    _r("email-manager", "Communication", "Email Manager",
       "The inbox stops being a swamp",
       "Four hundred unread, three people half-responsible, and the important one from Tuesday still buried. It reads everything, sorts it, routes it, and drafts the replies that write themselves.",
       core=["email.triage", "email.route", "email.draft"],
       suggested=["email.thread", "email.sla", "knowledge.pack", "email.cleanup"]),

    _r("front-desk", "Communication", "Front Desk",
       "All inbound, every channel, one memory",
       "The phone, the texts, the web form, the inbox — one worker owning all of it. A customer who called this morning and texts this afternoon isn't starting over.",
       core=["email.triage", "email.draft", "email.thread", "lead.capture", "appt.book", "knowledge.pack"],
       suggested=["voice.inbound", "chan.webchat", "lead.qualify", "appt.remind", "crm.logging"],
       minTier=2),

    _r("support-agent", "Communication", "Support Agent",
       "Everything after the sale",
       "The part of the business that generates repeat work and referrals, and the part that always loses the fight for attention against new work. It doesn't lose that fight.",
       core=["support.answer", "knowledge.pack", "support.status"],
       suggested=["support.ticket", "email.triage", "chan.webchat", "email.sla"]),

    # ---- Revenue --------------------------------------------------------
    _r("lead-qualifier", "Revenue", "Lead Qualifier",
       "Only the real ones reach you",
       "Most enquiries aren't worth your time and a few are worth dropping everything for. Telling them apart is a job, and right now it's your job.",
       core=["lead.capture", "lead.qualify", "lead.route"],
       suggested=["lead.enrich", "crm.sync", "appt.book", "lead.nurture"]),

    _r("appointment-setter", "Revenue", "Appointment Setter",
       "The calendar fills itself",
       "Booking, confirming, reminding, rescheduling. The admin around appointments is nearly all of the work, and none of it needs a person.",
       core=["appt.book", "appt.remind", "appt.reschedule"],
       suggested=["lead.qualify", "crm.logging", "chan.sms", "appt.setting"]),

    _r("follow-up", "Revenue", "Follow-Up Agent",
       "Nothing you quoted goes quiet",
       "You sent the quote on Tuesday. Nobody rejected it — it just got buried. This chases every estimate until the customer actually answers.",
       core=["quote.followup"],
       suggested=["crm.logging", "lead.nurture", "doc.generate", "appt.book"]),

    _r("outreach", "Revenue", "Outreach Agent",
       "The list gets worked, every day",
       "Prospecting is the first thing to fall off the list when work gets busy, which means it fails hardest exactly when there is most to lose.",
       core=["outreach.sequence", "lead.capture"],
       suggested=["research.web", "lead.enrich", "appt.setting", "crm.sync"]),

    _r("revenue-deputy", "Revenue", "Revenue Deputy",
       "Owns the pipeline end to end",
       "From first enquiry to signed job. It moves work through the pipeline, chases what's stalled, and on Friday tells you what it won, what it lost, and why.",
       core=["lead.capture", "lead.qualify", "quote.followup", "crm.sync", "crm.pipeline", "data.report"],
       suggested=["doc.generate", "appt.book", "lead.nurture", "dashboard", "crm.logging"],
       minTier=2),

    # ---- Operations -----------------------------------------------------
    _r("crm-operator", "Operations", "CRM Operator",
       "The CRM stops lying to you",
       "A CRM is only worth what someone puts into it, which is why yours is half empty. This one keeps it true without anybody typing.",
       core=["crm.sync", "crm.logging", "crm.hygiene"],
       suggested=["lead.enrich", "crm.pipeline", "data.report", "api.custom"]),

    _r("workflow-operator", "Operations", "Workflow Operator",
       "The process runs without a shepherd",
       "The multi-step thing that crosses four systems and only works because one person remembers all of it. That person is the bottleneck, and they'd like a holiday.",
       core=["workflow.multistep", "workflow.exception"],
       suggested=["crm.sync", "files.watch", "doc.generate", "api.custom", "approval.console"]),

    _r("browser-operator", "Operations", "Browser Operator",
       "Works the systems that have no way in",
       "The supplier portal, the insurer's site, the council system — the ones with no API and no export, where somebody logs in and copies things by hand. It does that instead.",
       core=["browser.operate"],
       suggested=["browser.extract", "data.collect", "files.watch", "doc.parse", "data.alert"]),

    _r("onboarding", "Operations", "Onboarding Agent",
       "The first two weeks, identical every time",
       "New client or new hire, same problem: a checklist that exists in one person's head and gets done differently every time.",
       core=["onboard.run", "onboard.chase"],
       suggested=["doc.generate", "email.draft", "appt.book", "files.watch"]),

    # ---- Money ----------------------------------------------------------
    _r("collections", "Money", "Collections Agent",
       "Invoices that chase themselves",
       "Chasing money is the job everyone hates and therefore the job nobody does. This one has no feelings about it and stays polite through every reminder.",
       core=["pay.chase", "pay.collect"],
       suggested=["doc.generate", "recon.match", "crm.logging", "data.alert"]),

    _r("back-office", "Money", "Back Office Deputy",
       "Quote to invoice to paid to reconciled",
       "The whole money pipeline across whatever tools you already run. It doesn't replace your accounting package; it operates it, which is the part nobody has time for.",
       core=["doc.generate", "pay.collect", "pay.chase", "recon.match", "crm.sync"],
       suggested=["doc.parse", "data.report", "data.alert", "approval.console", "dashboard"],
       minTier=2),

    # ---- Intelligence ---------------------------------------------------
    _r("data-analyst", "Intelligence", "Data Analyst",
       "Answers about your own numbers",
       "The figures exist, spread across five systems, and getting a straight answer out of them takes a day you don't have. Ask it instead.",
       core=["data.collect", "data.analyze"],
       suggested=["data.viz", "data.report", "data.alert", "dashboard", "api.custom"]),

    _r("reporting", "Intelligence", "Reporting Agent",
       "The Monday report writes itself",
       "Somebody spends half a day a week assembling a report that three people skim. That half-day is recoverable.",
       core=["data.collect", "data.report"],
       suggested=["data.viz", "data.alert", "dashboard", "browser.extract"]),

    _r("research", "Intelligence", "Research Agent",
       "Finds out, before the meeting",
       "Prospect research, competitor moves, supplier checks — all valuable, all skipped, because it's an hour nobody has.",
       core=["research.web"],
       suggested=["lead.enrich", "data.report", "crm.sync", "email.draft"]),
    # ---- Commerce -------------------------------------------------------
    _r("order-desk", "Commerce", "Order Desk Agent",
       "Nobody has to ask where their order is",
       "Where is my order is the most common question in ecommerce and the least valuable use of anyone time. This one answers it from the real order and the real tracking, in seconds, every time.",
       core=["order.status", "knowledge.pack"],
       suggested=["order.track", "email.triage", "email.draft", "chan.webchat"]),

    _r("returns", "Commerce", "Returns Agent",
       "Returns stop eating the week",
       "A return is six small steps and a judgment call, repeated all day. It is the most labour-intensive thing in an online shop and the least interesting.",
       core=["order.returns", "knowledge.pack"],
       suggested=["order.status", "doc.generate", "email.draft"]),

    _r("ecommerce-deputy", "Commerce", "Ecommerce Deputy",
       "Owns everything after the buy button",
       "The whole post-purchase experience - order questions, tracking, exceptions, returns and the review request - owned by one worker with one memory of the customer.",
       core=["order.status", "order.track", "order.returns", "knowledge.pack", "email.triage"],
       suggested=["ship.eta", "review.request", "email.draft", "chan.webchat", "crm.sync"],
       minTier=2),

    # ---- Operations -----------------------------------------------------
    _r("stock", "Operations", "Stock Agent",
       "You stop finding out too late",
       "Running out is expensive, and finding out from a customer is worse. This watches what is running down, how fast, and says so while there is still time to order.",
       core=["stock.watch", "data.alert"],
       suggested=["stock.reconcile", "supplier.chase", "data.report"]),

    _r("shipments", "Operations", "Shipment Agent",
       "The stuck parcel finds you first",
       "Most delivery problems are known to the carrier long before they are known to you, and to the customer before either. This closes that gap, and claims for what never arrives.",
       core=["ship.eta", "order.track", "order.status"],
       suggested=["ship.claims", "support.status", "email.draft"]),

    _r("renewals", "Operations", "Renewals Agent",
       "Nothing lapses quietly",
       "Contracts, retainers, insurance, tickets and licences all expire on a date somebody was supposed to remember. Revenue and compliance leak through the same gap.",
       core=["renewal.watch", "cert.expiry"],
       suggested=["doc.generate", "email.draft", "crm.sync"]),
]


ROLE_BY_ID = dict((r["id"], r) for r in ROLES)

for _r_ in ROLES:
    for _cid in _r_["core"] + _r_["suggested"]:
        assert _cid in CAP_BY_ID, "%s references unknown capability %s" % (_r_["id"], _cid)

ROLE_FAMILIES = []
for _r_ in ROLES:
    if _r_["family"] not in ROLE_FAMILIES:
        ROLE_FAMILIES.append(_r_["family"])


# --------------------------------------------------------------------------
# Modifiers the buyer can add that are not capabilities.
# --------------------------------------------------------------------------

MODIFIERS = [
    {"id": "rush", "name": "Rush delivery", "kind": "pct", "pct": PRICING["rushPct"],
     "blurb": "Half the timeline. Priced against the build because it displaces other work."},
]

AUTONOMY = [
    {"id": "L0", "name": "Watch",   "blurb": "Observes and reports. Takes no action.", "needs": []},
    {"id": "L1", "name": "Draft",   "blurb": "Prepares anything a customer would see; a human sends it. Keeps your records up to date as it goes.", "needs": []},
    {"id": "L2", "name": "Approve", "blurb": "Acts on its own, but stops for you above a line you set.", "needs": ["approval.console"]},
    {"id": "L3", "name": "Operate", "blurb": "Acts within scope, escalates exceptions. Enabled in writing after supervision.", "needs": ["approval.console"]},
]


# --------------------------------------------------------------------------
# What a capability needs from the customer before it can run for real.
#
# This is what separates "the forge built it" from "it is ready". Anything
# listed here that a design cannot supply becomes operator work, and saying so
# up front is what stops "live in 10 business days" from being a guess. It lives
# in the catalog rather than in the tools so the buyer-facing readiness estimate
# and the operator's handoff sheet can never disagree.
# --------------------------------------------------------------------------

SETUP_NEEDS = {
    "knowledge.pack":   ["their documents, prices and policies"],
    "email.triage":     ["a sample of real inbox traffic to calibrate against"],
    "email.draft":      ["examples of how they already write to customers"],
    "email.cleanup":    ["access to the existing backlog"],
    "lead.qualify":     ["what a good customer looks like to them"],
    "lead.enrich":      ["which sources they consider acceptable"],
    "appt.book":        ["job durations, travel buffers and working hours"],
    "appt.setting":     ["the list to work, and calling-hours rules"],
    "doc.generate":     ["their document template and branding"],
    "doc.parse":        ["ten real documents to check extraction against"],
    "pay.collect":      ["a payment provider account"],
    "pay.chase":        ["their escalation tone and terms"],
    "recon.match":      ["a month of real transactions to reconcile against"],
    "browser.operate":  ["portal credentials and a recorded walkthrough"],
    "browser.extract":  ["portal credentials and the page layout"],
    "api.custom":       ["API documentation and a credential"],
    "files.watch":      ["the folder to watch and what should happen"],
    "crm.sync":         ["field mapping to their CRM"],
    "crm.hygiene":      ["a decision on what may be merged automatically"],
    "crm.pipeline":     ["their stages and what counts as stale"],
    "chan.sms":         ["A2P 10DLC registration — weeks, outside our control"],
    "chan.whatsapp":    ["Meta business verification"],
    "voice.inbound":    ["a phone number and a call-flow walkthrough"],
    "voice.outbound":   ["a phone number and calling-hours rules"],
    "whitelabel":       ["their domain and brand assets"],
    "lang.extra":       ["which languages, and a native reviewer"],
    "workflow.multistep": ["the process written down, step by step"],
    "workflow.exception": ["the exceptions they already know about"],
    "support.answer":   ["their documentation or help centre"],
    "support.ticket":   ["their help desk and priority rules"],
    "onboard.run":      ["their onboarding checklist"],
    "data.collect":     ["credentials for each source"],
    "data.analyze":     ["the questions they actually want answered"],
    "data.report":      ["who receives it, and when"],
    "data.alert":       ["the thresholds that matter to them"],
    "research.web":     ["what a useful brief looks like to them"],
    "training":         ["a date and the attendee list"],
    "order.status":     ["a read connection to their store and their order fields"],
    "order.track":      ["carrier accounts, or the tracking data already in their store"],
    "order.returns":    ["their returns policy, and who may approve an exception"],
    "order.recover":    ["their checkout data and what they are willing to offer"],
    "stock.watch":      ["reorder points and supplier lead times"],
    "stock.reconcile":  ["which system is authoritative when two disagree"],
    "supplier.chase":   ["supplier contacts and the agreed cadence"],
    "ship.eta":         ["which milestones the customer should hear about"],
    "ship.claims":      ["carrier accounts and the documents each claim needs"],
    "review.request":   ["their public review link, and when a job counts as finished"],
    "renewal.watch":    ["the contracts, their dates and their notice periods"],
    "cert.expiry":      ["the certificates to track and how early to warn"],
}

for _cid in SETUP_NEEDS:
    assert _cid in CAP_BY_ID, "SETUP_NEEDS references unknown capability %s" % _cid


def payload():
    """The catalog as the browser sees it."""
    return {
        "tiers": TIERS,
        "pricing": PRICING,
        "volume": VOLUME,
        "integrations": INTEGRATIONS,
        "channels": CHANNELS,
        "gates": GATES,
        "capabilities": CAPABILITIES,
        "capGroups": CAP_GROUPS,
        "roles": ROLES,
        "roleFamilies": ROLE_FAMILIES,
        "modifiers": MODIFIERS,
        "autonomy": AUTONOMY,
        "setupNeeds": SETUP_NEEDS,
    }


def as_json(indent=None):
    return json.dumps(payload(), ensure_ascii=False, indent=indent, sort_keys=False)


if __name__ == "__main__":
    d = payload()
    print("roles         %d" % len(d["roles"]))
    print("capabilities  %d" % len(d["capabilities"]))
    print("groups        %s" % ", ".join(d["capGroups"]))
    print("families      %s" % ", ".join(d["roleFamilies"]))
    print("json bytes    %d" % len(as_json()))
