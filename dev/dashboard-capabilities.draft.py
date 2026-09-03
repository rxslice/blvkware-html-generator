# Draft dashboard capabilities for CAPABILITIES in dev/catalog.py.
#
# NOT WIRED IN. This file is a proposal — adding these makes them buyable at
# /hire/, which changes what the checkout sells, so it needs a decision rather
# than a commit.
#
# The pricing answers the "charge per metric / param / integration" question by
# mapping it onto the model already in catalog.py rather than inventing a
# parallel scheme. Two deliberate choices:
#
#   * A metric is cheap ($250). It is a query and a tile. Charging real money
#     per number punishes the customer for the thing that makes the dashboard
#     worth having, and invites haggling over line items.
#   * A data source is not ($750 + ops). That is where the build cost actually
#     lives — auth, schema, rate limits, the thing that breaks at 3am. Price the
#     work, not the pixels.
#
# Both keep the promise the rest of the site makes: the price is on the page and
# the bill arrives the same shape as the quote.

DASHBOARD_CAPABILITIES = [

    _c("dash.core", "Dashboard", "Operations dashboard",
       "The window onto the agent. What it did, what it is waiting on, and what it is about to do, "
       "on one screen that is worth opening every morning.",
       950, 2, ops=40, integ=[],
       accept="Every action the agent took in a replayed week appears, in order, with its evidence "
              "attached and nothing missing."),

    _c("dash.refusals", "Dashboard", "Refusal log",
       "Every action the agent declined and the rule that stopped it, in the same feed as the work "
       "it completed.",
       650, 1, needs=["dash.core"],
       accept="Each refusal names the rule, the record and the evidence that would clear it — a "
              "reviewer can act on it without opening anything else."),

    _c("dash.brand", "Dashboard", "Your branding",
       "Your logo, colours, typeface and words. Not a vendor product with your name in the corner.",
       550, 1, needs=["dash.core"],
       accept="Placed beside your own site, a colleague cannot tell it was built by somebody else."),

    _c("dash.source", "Dashboard", "One more data source",
       "A second system feeding the same screen — the CRM, the accounting package, the spreadsheet "
       "somebody still maintains by hand.",
       750, 2, ops=25, needs=["dash.core"],
       accept="Figures reconcile against the source system for a full period, to the cent."),

    _c("dash.metric", "Dashboard", "An extra tracked number",
       "One more measure on the board, defined the way your business actually defines it rather "
       "than the way the software finds convenient.",
       250, 1, needs=["dash.core"],
       accept="The number matches the one the owner works out by hand, for the same period."),

    _c("dash.share", "Dashboard", "Client-facing view",
       "A read-only version your own customers can open, showing only what you choose to show.",
       650, 1, ops=20, needs=["dash.core"],
       accept="Nothing outside the published set is reachable from the shared link, including by "
              "editing the address."),

    _c("dash.digest", "Dashboard", "Scheduled digest",
       "The same picture pushed to an inbox or a channel on your schedule, so nobody has to remember "
       "to look.",
       450, 1, ops=15, needs=["dash.core"], integ=["email"],
       accept="Arrives on time for two consecutive periods with figures matching the live board."),
]

# Worked example — an agent with a fully branded dashboard:
#   Operator tier                              3,500
#   dash.core + dash.refusals + dash.brand     2,150
#   two extra sources, three extra metrics     2,250
#                                             ------
#                                              7,900 build, plus monthly ops
#
# Which lands just under the operating-system build, as it should: this is the
# window onto one agent, not the machine that runs a whole process.
