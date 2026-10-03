# Outreach: the direct-to-buyer test (from 2026-10-02)

The launch reached almost nobody (results in `README.md`). This is the cheapest experiment
that tells us whether anyone will pay for a kit, run by hand, by you, from your own accounts.

## The experiment

| | |
|---|---|
| Hypothesis | People who build automations for clients will pay $79 for a kit, because it replaces the scoping and safety work they otherwise do by hand or skip. |
| Who | 1. Automation agencies and freelancers (Zapier, Make, n8n). 2. Small service businesses that already use one of those tools. |
| Offer | The free sample kit first; the kit page second. No call, no pitch deck. |
| Volume | 50 contacts in 10 working days: the 31 agencies in `agencies.csv`, plus about 20 from the community posts below. |
| Success | By 16 October: **3 or more real replies** (a question, an objection or a request; not "thanks") **or 1 sale**. |
| Abandon | **0 real replies from 50 contacts.** Then the message or the buyer is wrong, not the product: change who it is for before changing what it is. |
| Track | `agencies.csv` columns `sent`, `reply`, `outcome`. One line per contact, filled in the day it happens. |

Rules: one message per contact, one follow-up after 5 working days, then stop. Never buy
lists, never scrape personal emails, never message anyone who has not listed themselves as
open to work. The agencies in `agencies.csv` are on Zapier's public partner directory, whose
purpose is to be contacted: use the directory's own Contact button.

## Message to an agency (Zapier directory contact form)

```post name="Outreach agency" limit=1200
Hi, I'm Russ, a solo builder in Mississippi. Quick one, no call needed.

When you build an AI agent for a client, someone has to write down what it may do on its own, what waits for approval, what it must never say, and how you prove it works before it touches a customer. I built a generator that writes that part: instructions, tools in OpenAI, Anthropic and MCP formats, a workflow per task, record schemas, tests, and a small Python runtime that enforces the approval rules in code.

Here is a complete sample, every file, free and without an email: https://blvkware.dev/sample-kit/

If it would save you scoping time on a client job, kits are $79 per agent. If it would not, I would genuinely like to know why. That is the most useful thing you could tell me this month.
```

```post name="Outreach agency follow-up" limit=600
Following up once, then I'll leave you be. If the sample kit (https://blvkware.dev/sample-kit/) is not useful for client work, one line on what is missing would help me a lot. Thanks either way.
```

## Message to a freelancer who posted that they build agents

Only to people who publicly advertise automation or agent-building services, in reply to
their own post or through the platform's hire button. Never a cold DM to someone who has not.

```post name="Outreach freelancer" limit=700
Saw you build agents for clients. I made something you might use as the spec layer: you describe the job, it generates the agent's instructions, tools (OpenAI, Anthropic, MCP), workflows, schemas, tests and a small runtime that enforces approvals. Full sample, free, no email: https://blvkware.dev/sample-kit/ Would you hand something like this to a client, or is it missing something?
```

## Community posts

Read each community's rules first. Where self-promotion is limited to a weekly thread,
post there instead. Lead with the free sample and a question, never with the price.

```post name="r/n8n title" limit=300
I generate the spec layer for an AI agent (approvals, never-do rules, tests), one workflow per task to rebuild in n8n. Free sample, blunt feedback wanted
```

```post name="r/n8n body" limit=40000
Most agent workflows I see skip the boring part: what the agent is allowed to do without asking, what has to wait for a human, and how you know it works before it emails a customer.

I built a generator for that part. You pick the job (quote follow-up, inbox, booking, collections and so on), describe the business and its "never" rules, and it writes the kit: the agent's instructions, its tools in OpenAI, Anthropic and MCP formats, one workflow per task (its trigger, the steps in order, and which steps wait for approval) that you rebuild as one n8n workflow, JSON schemas for its records, acceptance tests, and a small Python runtime that enforces the approval rules if you are not doing it in n8n.

Complete sample for a made-up plumbing business, every file readable in the browser, no email: https://blvkware.dev/sample-kit/

What I would love to know from people who build in n8n every day: would you use the workflow files as the starting point for a build, or is the format wrong for how you work?
```

```post name="r/AI_Agents title" limit=300
The part of an agent nobody writes down: approval rules, never-do lists and tests. I generate it per job. Free full sample
```

```post name="r/AI_Agents body" limit=40000
The model is rarely the problem with a small-business agent. The problem is that nobody wrote down which actions it may take alone, which wait for a person, what it must never say, and how you test that before it talks to a customer.

I built a generator that writes exactly that for one job: instructions with the business's own "never" rules, tools in OpenAI, Anthropic and MCP formats (each marked read, internal or external), a workflow per task, record schemas, acceptance tests, and a small stdlib Python runtime that enforces the approval queue, opt-outs and quiet hours in code, with a hash-chained audit log. It also runs as an MCP server.

Full sample kit, every file, no email: https://blvkware.dev/sample-kit/

Honest question for people shipping agents: is the enforcement layer something you would want generated, or do you always end up writing your own?
```

```post name="n8n forum title" limit=200
Generated agent specs (approvals, never-do rules, tests), one workflow per task for n8n: free sample, feedback wanted
```

```post name="n8n forum body" limit=10000
Sharing something I built in case it is useful, and because I would like feedback from people who build in n8n daily.

It generates the specification for one AI agent from a few questions: its instructions with your "never" rules, its tools, one workflow per task (its trigger, the steps in order, and which steps wait for approval, so each becomes one n8n workflow), JSON schemas for what it records, acceptance tests, and the approval rules that decide what may run without a person.

Complete sample kit for a made-up plumbing business, every file readable in the browser: https://blvkware.dev/sample-kit/

Does the workflow format suit how you build, or would you want it shaped differently?
```

## After each reply

Answer within a day, in your own words. The PH reply drafts in `kits.md` cover the likely
questions (prompts, developers, running cost, data, models, mistakes, refunds). Log what
people object to: three people saying the same thing is the product roadmap.
