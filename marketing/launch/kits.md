# Launch copy: BlvkWare agent kits

For business owners. The pitch is one thing: **design an agent for one job in your business,
see every file before you pay, download the kit for $79 or $199, one-off.**
The strongest proof is the free sample kit, so most posts lead with it.

Every block below is ready to paste. `python marketing/launch/check.py` holds each one to
its platform's limit, to the prices the site charges, and to the copy rules (no em dashes).

Links: kit page `https://blvkware.dev/hire/` · sample `https://blvkware.dev/sample-kit/` ·
catalog `https://blvkware.dev/agents/` · free job finder `https://blvkware.dev/scan/`

---

## Product Hunt

Live gallery order (2026-09-27): `docs/assets/og/hire.png`, `docs/assets/og/sample-kit.png`,
the YouTube demo, `marketing/kits/out/operator-gumroad-cover-1-hero.png`, `-3-how.png`,
`-2-inside.png`. Thumbnail: `marketing/video/out/ph-thumbnail.gif`.
Launch tags: Productivity, Artificial Intelligence, No-Code.

```post name="PH name" limit=40
BlvkWare Agent Kits
```

```post name="PH tagline" limit=60
Every file your AI agent needs, designed from your answers
```

```post name="PH description" limit=260
Pick the job an agent should own. Answer a few questions. Get its instructions, tools (OpenAI, Anthropic, MCP), workflows, records, tests and a Python runtime that enforces its rules in code. Every file shown before you pay. $79 or $199, one-off.
```

```post name="PH first comment" limit=1500
Hi PH. I build AI agents for small businesses, and the part nobody wants to pay an agency for is the specification: what the agent is allowed to do, in what order, what it must never do, and how you know it works.

So that is what a kit is. You pick the job (chasing quotes, answering the inbox, booking, collections: 23 of them), tell it about your business and the rules it must never break, choose which of your systems it touches, and set how much it may do alone. It starts at Draft: anything a customer would see waits for a person.

The kit page lists every file your kit will contain, with the price, before you pay. If you want to read one first, there is a complete sample kit here, every file, free: https://blvkware.dev/sample-kit/

The part I care most about: the rules are not just asked for in a prompt. Every kit ships a small Python runtime (nothing to install) that checks each action before it runs, holds anything customer-facing in an approval queue with its own approvals page, keeps a tamper-evident log, and honours opt-outs and quiet hours. It also runs as an MCP server, so you can try the agent in Claude Desktop.

What it is not: hosted software. You keep your own model account and data, and wire it into OpenAI or Anthropic tool calling, any MCP client, or n8n, Make and Zapier.

One person built this. I would genuinely like to know which job you would give an agent first.
```

### Product Hunt extras

**Video.** `marketing/video/out/blvkware-kits-demo.mp4`: 94 s, 1080p, captioned, no
sound needed. It is a real run of the live kit page (pick a job, tick systems, choose
capabilities, set autonomy, write the never-do rule, see the file list, the buy button,
the sample kit). Rebuild with `node marketing/video/record.mjs` after the page changes.
Upload it to YouTube as **Unlisted** or Public with `youtube-thumbnail.jpg`, then paste
the link into the PH "Video / Loom" field. PH only takes YouTube or Loom links.

```post name="YouTube title" limit=100
BlvkWare Agent Kits: design an AI agent for one job, see every file before you pay
```

```post name="YouTube description" limit=5000
A walk through the kit page at https://blvkware.dev/hire/

You pick the job an agent should own, tick the systems it may touch, choose what it handles, set how much it may do on its own (every kit starts at Draft: anything a customer would see waits for a person), and write down what it must never do. The page then lists every file in your kit before you pay: instructions, tools in OpenAI, Anthropic and MCP formats, a workflow per task, record schemas, guardrails and acceptance tests.

$79 for an agent that owns one job, $199 for one that runs a whole function. One-off.

Read a complete sample kit first, free: https://blvkware.dev/sample-kit/
```

**Animated thumbnail.** `marketing/video/out/ph-thumbnail.gif` (240x240, 166 KB, loops):
the mark, the kit's folders, the $79 price, "See it first". PH accepts GIF thumbnails;
movement in the feed is what earns the click. Rebuild with `python marketing/video/thumb.py`.

**Hunter.** Keep yourself. A hunter no longer brings their followers to a launch (PH
stopped notifying followers of hunts), and a self-hunted launch is ranked the same way.
Swap only if someone with real reach in small-business or AI circles offers.

**Makers.** `@blvkware` is right. Add anyone else only if they actually built part of it:
PH shows makers as the people answering comments.

**Shoutouts.** Each becomes a founder review on that product's PH page, linking back.
Only name tools the kits really run on. The three below are true of this stack.

```post name="PH shoutout: Claude" limit=500
The kit generator, the site and the kit service were built with Claude as a pair programmer, and the kits themselves ship tool definitions in Anthropic's format. It helped most with the careful parts: the guardrails, the autonomy levels and the acceptance tests every kit carries.
```

```post name="PH shoutout: Gumroad" limit=500
Gumroad takes the payments and issues the licence key that unlocks each kit download. No store to build, refunds and disputes handled, and the licence API made it simple to stop a refunded key from downloading. For a one-person product it was the fastest honest way to sell.
```

```post name="PH shoutout: Netlify" limit=500
The kit service runs as Netlify Functions: it previews the exact file list before you pay and generates the kit when you download it. Functions let a static site do the one thing that needs a server, without me running one.
```

Optional fourth if PH lists it: GitHub (the site is served by GitHub Pages).

**Launch-day replies.** Answer every comment within the hour, in your own words; these
are starting points for the questions most likely to come.

```post name="PH reply: is it just prompts" limit=800
Fair question. The prompt is one file out of about fifty in a kit. The rest is what makes an agent safe to switch on: a tool definition per action in OpenAI, Anthropic and MCP formats, each marked read, internal or external, a workflow per task, JSON schemas for the records it keeps, and a small Python runtime that enforces the approval rules in code, with tests you can run to prove it. The free sample shows all of it: https://blvkware.dev/sample-kit/
```

```post name="PH reply: does it run the agent" limit=800
Partly, and deliberately not hosted. The kit includes a runtime that enforces the rules around your model calls (approvals, opt-outs, quiet hours, an audit log) plus working loops for OpenAI and Anthropic and an MCP server, so you can run it on your own machine today. What you add is your model key and the handlers that talk to your own systems, one documented function per tool. No monthly fee, and your data never passes through me.
```

```post name="PH reply: why not ChatGPT" limit=800
You could get a prompt from ChatGPT. What you would not get is the part that takes the time: which of your systems it may touch and how, what it may do alone at each autonomy level, what must wait for a person, and tests that prove it before it talks to a customer. The kit is generated from your answers, so those are written for your business, and you see every file before you pay.
```

The rest of the likely questions, written looser so they read like you and not like a
FAQ. Change anything that does not sound like you.

```post name="PH reply: do I need a developer" limit=800
Honestly, somewhat technical helps. If you've wired up a Zapier or n8n flow before, you can do most of it: the workflows map straight onto those. For the Python route you'd fill in one small function per tool (it's documented right there in handlers.py) and add your model key. If you've never touched either, hand the kit to whoever builds for you. It's written so they don't have to guess anything.
```

```post name="PH reply: what does it cost to run" limit=800
The kit's a one-off, and nothing in it bills you monthly. Running it costs whatever your model provider charges for the calls (your own OpenAI or Anthropic account) plus whatever your own tools cost, like a phone number if it texts. The runtime itself is plain Python with nothing to install, so it runs on the machine you already have.
```

```post name="PH reply: my data" limit=800
Good thing to ask. The kit service builds your kit and forgets it: your design isn't stored and no copy of the kit is kept. The licence just remembers which job it was bought for. Once you download it, it's all on your side: your model account, your systems, your data. It has no credentials in it and phones home to nobody.
```

```post name="PH reply: vs hosted agent platforms" limit=800
They're good if you want someone else to run it. This is for when you'd rather own it: no monthly seat, your data stays in your accounts, and the rules live in files you can read and change, not in a vendor's settings page. Plenty of people will want the hosted route, and that's fair. This is the other option.
```

```post name="PH reply: which models" limit=800
Anything with tool calling. The tools ship in OpenAI, Anthropic and MCP formats, and there are working loops for both OpenAI and Anthropic in the kit. The MCP server means Claude Desktop or Claude Code can drive it directly too, and the same rules still apply to every call.
```

```post name="PH reply: what if it gets it wrong" limit=800
That's the whole design, really. It starts at Draft, so anything a customer would see waits for you to approve it first. The runtime also holds any draft that names a price or a date, or that breaks one of your own "never" rules, even at higher levels. Every action is logged in a chain you can verify, so you can always see what it did and why. You only loosen it once you've watched it work.
```

```post name="PH reply: refunds" limit=800
You see the full file list and price for your exact design before you pay, so there shouldn't be surprises. If there are, Gumroad's money-back guarantee on the product page applies, and a refunded key just stops downloading. No hoops.
```

```post name="PH reply: thanks" limit=800
Thank you, really appreciate you taking a look. If you try the kit page, I'd love to know which job you picked and whether anything in the file list surprised you.
```

## Gumroad listings (updated and pasted 2026-09-27)

Paste into each product's description; covers and thumbnail are re-rendered in
`marketing/kits/out/` (operator-* and deputy-*) with the current counts.

```post name="Gumroad Operator description" limit=2500
An AI agent that owns one job in your business, start to finish, specified down to the last file and generated from your own answers.

You design it first at blvkware.dev/hire: pick the job (chasing quotes, answering the inbox, booking, collections and 19 more), tick the systems it may touch, write down what it must never do, and set how much it may do on its own. The page shows every file in your kit before you pay.

What you download:
- Its instructions, written for your business with your "never do" rules built in word for word
- Its tools in OpenAI, Anthropic and MCP formats, each marked read, internal or external
- A workflow per task: what starts it, the steps in order, which steps wait for your approval
- A JSON Schema for every record it keeps, including an approval queue and an audit log
- An autonomy policy with four levels. It starts at Draft: nothing reaches a customer unapproved
- The rules, in code: a small Python runtime that sits between the model and your systems and checks every action first. It keeps a real approval queue with its own approvals page, a tamper-evident log, never contacts anyone who opted out, holds sends until morning, and holds any draft that names a price or a date or breaks one of your rules
- A handlers file with one documented function per tool, ready for your own systems
- Tests you can run that prove every one of those rules holds, plus working loops for OpenAI and Anthropic

It is not hosted software and contains no credentials: you, or whoever builds for you, run it with your own model account. Read a complete sample kit first, free: blvkware.dev/sample-kit

$79, one-off. Change the design and download again, up to 20 times.
```

```post name="Gumroad Deputy description" limit=2500
One AI agent for a whole function (front desk, revenue, back office or e-commerce), specified down to the last file and generated from your own answers.

A Deputy works across more systems and channels, makes judgment calls and escalates the exceptions. You design it at blvkware.dev/hire and see every file before you pay; a Deputy key also covers any Operator-sized design.

What you download:
- Its instructions, written for your business with your "never do" rules built in word for word
- Its tools in OpenAI, Anthropic and MCP formats, each marked read, internal or external
- A workflow per task, with the steps that wait for your approval marked
- A JSON Schema for every record it keeps, including an approval queue and an audit log
- An autonomy policy with four levels, starting at Draft
- The rules, in code: a small Python runtime that checks every action before it runs. It keeps a real approval queue with its own approvals page, a tamper-evident log, honours opt-outs and quiet hours, holds refunds above your limit, and holds any draft that names a price or a date or breaks one of your rules
- A handlers file with one documented function per tool, ready for your own systems
- Tests you can run that prove every one of those rules holds, plus working loops for OpenAI and Anthropic

It is not hosted software and contains no credentials. Read a complete sample kit first, free: blvkware.dev/sample-kit

$199, one-off. Change the design and download again, up to 20 times.
```

## LinkedIn

Attach: `marketing/kits/out/operator-ad-landscape-1200x628.png`

```post name="LinkedIn post" limit=3000
Most small businesses do not need another tool to operate. They need the job done.

The job that quietly costs the most is usually one nobody owns: the quote nobody chases, the enquiry that sits until Monday, the invoice that goes 60 days late.

I have been building AI agent kits for exactly those jobs. You pick the job, answer a few questions about your business, choose which of your systems it may touch, and set how much it may do on its own. The kit is everything a builder needs to make that agent real: its instructions, its tools in OpenAI, Anthropic and MCP formats, a workflow per task, the records it keeps, the rules it must never break, and the tests it has to pass before it talks to a customer.

It starts at Draft. Anything a customer would see waits for a person until you decide otherwise. And that is enforced, not just requested: every kit ships a small runtime that checks each action before it runs, keeps the approval queue and a tamper-evident log, and never contacts anyone who opted out.

You see every file before you pay. $79 for an agent that owns one job, $199 for one that runs a whole function. One-off.

If you want to see what you would actually get, here is a complete sample kit, every file, free to read:
https://blvkware.dev/sample-kit/
```

## X (thread)

Attach to the first post: `docs/assets/og/sample-kit.png`

```post name="X 1" limit=280
I made a free, complete AI agent kit you can read file by file before anyone asks you for money.

Instructions, tools (OpenAI, Anthropic, MCP), workflows, records, guardrails, acceptance tests. For a plumbing business that does not exist:

https://blvkware.dev/sample-kit/
```

```post name="X 2" limit=280
Why a kit and not a chatbot builder: the hard part of an agent is not the model. It is writing down what it may do, in what order, what it must never do, and how you know it works. That is what the files are.
```

```post name="X 3" limit=280
Every agent starts at Draft. It keeps your records straight, and anything a customer would see waits for a person. Each tool is marked read, internal or external, so the limit can be enforced in code, not just asked for in a prompt.
```

```post name="X 4" limit=280
Yours is generated from your answers: your job, your "never" list, your systems, your channels. The kit page shows every file before you pay. $79 for one job, $199 for a whole function. One-off.

https://blvkware.dev/hire/
```

Launch day only, posted on its own (not in the thread) once the PH page is live. PH frowns
on asking for upvotes, so it asks for opinions instead.

```post name="X launch day" limit=280
BlvkWare Agent Kits is live on Product Hunt today.

Design an AI agent for one job in your business and see every file before you pay. The rules are enforced in code, not just asked for in a prompt.

Honest takes welcome:
https://www.producthunt.com/products/blvkware-agent-kits
```

```post name="LinkedIn launch day comment" limit=1250
It is on Product Hunt today, if you would like to see what people make of it or ask me anything there: https://www.producthunt.com/products/blvkware-agent-kits
```

## Reddit

r/smallbusiness bans promotion outside its threads for it; post there only in the weekly
promotion thread. r/SideProject, r/EntrepreneurRideAlong and r/AI_Agents accept this as is.

```post name="Reddit title" limit=300
I built a way to design an AI agent for one job in your business and read every file of it before paying (free sample inside)
```

```post name="Reddit body" limit=40000
Solo builder here. The thing I kept seeing small businesses stuck on with AI agents was not the model. It was the specification: what the agent is allowed to do, in what order, what it must never do, and how you know it works before it emails a customer.

So I built a configurator that writes that specification for you. You pick the job (quote follow-up, inbox, booking, collections, returns: 23 in the catalog), describe your business and the rules it must never break, choose the systems it touches, and set how much it may do alone. It starts at Draft, so anything a customer would see waits for a person.

What you get is a kit: the agent's instructions, its tools in OpenAI, Anthropic and MCP formats, a workflow per task (usable in n8n, Make or Zapier), record schemas, guardrails and acceptance tests, plus a small Python runtime that enforces the rules. Plain JSON, Markdown and Python.

To show what that actually means, here is a complete sample kit for a fictional plumbing business, every file readable in the browser, no email required: https://blvkware.dev/sample-kit/

It also ships a small Python runtime that enforces those rules in code (approval queue, opt-outs, quiet hours, a tamper-evident log). It is not hosted: you or a developer connect it to your own model account and systems.

Pricing is on the page: $79 for an agent that owns one job, $199 for one that runs a whole function, one-off. Happy to answer anything, including "why would I not just prompt ChatGPT".
```

## Indie Hackers

```post name="IH title" limit=120
Selling AI agent specifications instead of AI agents: $79 kits, every file shown before you pay
```

```post name="IH body" limit=10000
I retired a done-for-you agent service in favour of self-serve kits, because every sale needed me on a call and every build needed me after it. A kit is the part of that work that can be generated: the agent's instructions, tools, workflows, records, guardrails and tests, written from the buyer's answers.

How it sells without me: the buyer designs the agent on the site, the kit page lists every file and the price, Gumroad takes the payment, and the licence key downloads the zip. Nobody talks to anybody unless they want to.

The part that made it worth the price, I think: the rules are enforced, not just written down. Every kit ships a small stdlib Python runtime that checks each action before it runs, holds anything customer-facing for approval, keeps a hash-chained audit log and honours opt-outs, with tests the buyer can run. It doubles as an MCP server.

The conversion bet is transparency. The file list is shown before payment, and there is now a complete sample kit anyone can read: https://blvkware.dev/sample-kit/

$79 or $199, one-off. I would love feedback on the sample: is it the thing you would pay for?
```

## Google Ads (responsive search ad)

Final URL: `https://blvkware.dev/sample-kit/`. Keywords to start: ai agent for small business,
ai quote follow up, ai receptionist template, n8n ai agent template, ai agent template.

```post name="GA headline 1" limit=30
AI Agent Kits From $79
```

```post name="GA headline 2" limit=30
See Every File Before You Pay
```

```post name="GA headline 3" limit=30
Read a Full Sample Kit Free
```

```post name="GA headline 4" limit=30
Built for One Job, Done Right
```

```post name="GA headline 5" limit=30
OpenAI, Anthropic and MCP
```

```post name="GA description 1" limit=90
Instructions, tools, workflows, guardrails and tests for one agent. $79 or $199, one-off.
```

```post name="GA description 2" limit=90
Starts at Draft: anything a customer sees waits for a person. Read a whole kit free first.
```

## Meta ads

Creative: `marketing/kits/out/operator-ad-square-1080x1080.png` (feed),
`operator-ad-story-1080x1920.png` (stories). Destination: `https://blvkware.dev/sample-kit/`.

```post name="Meta primary text" limit=500
The quote you sent Tuesday is still sitting there. An AI agent can chase it, but only if someone writes down exactly what it may say and what it must never do. That is what a BlvkWare kit is, generated from your answers. Read a complete one free before you buy yours.
```

```post name="Meta headline" limit=40
Read a full AI agent kit, free
```

```post name="Meta description" limit=30
From $79, one-off
```
