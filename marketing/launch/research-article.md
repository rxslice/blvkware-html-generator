---
title: AI models invent packages at the frontier, not in the basics
published: true
tags: security, ai, opensource, python
canonical_url: https://blvkware.dev/ai-package-hallucination-data/
cover_image: https://blvkware.dev/assets/og/ai-package-hallucination-data.png
---

*Originally published, with charts, at [blvkware.dev](https://blvkware.dev/ai-package-hallucination-data/).*

Between 22 September and 2 October 2026, a small panel of AI models was asked, on seven separate days, to write code and say what to install. Of 2,532 package suggestions, 97 named a package that does not exist. Almost none of them came from routine work. Most came from the newest corners of each ecosystem, which is exactly where a developer is least able to tell. And 19 of the invented names could be registered by anyone this afternoon.

This is the first full write-up of that panel's data. The panel is the collection arm of [HALLUX](https://blvkware.dev/hallux/), a record of identifiers that AI models emit and that do not exist. The figures below come from its own run files, nobody else has them, and every number here can be checked against the downloadable summary at the end.

## The short version

- **3.8% of package suggestions named something that does not exist** (97 of 2,532; 95% interval 3.2% to 4.7%).
- **The task matters far more than the model.** Routine prompts produced one invention in 582 suggestions. Prompts in fast-moving areas, where training data is thin, produced one in seventeen.
- **The four model families were statistically indistinguishable**, between 3.4% and 4.9%, with overlapping intervals.
- **Most inventions are one-offs; the dangerous few repeat.** 20 of the 28 invented names appeared once. The two most repeated were each produced by three of the four families, in 17 samples, on two different days.
- **Whether an invention can be exploited depends on the registry.** Every invented PyPI and crates.io name was free to register. On npm, scopes and a naming rule protected nearly half.
- **One maintainer team got there first.** The Rust name that three families sent people to is a deliberately empty crate owned by the project's own maintainer.

## How the data was collected

The panel is deliberately plain, so that it can be repeated and argued with.

- **Four model families, one model each:** OpenAI's open-weight gpt-oss-120b and Alibaba's Qwen3.8 27B (both through Groq), NVIDIA's Nemotron 3 Super (through OpenRouter) and Google's Gemini 2.5 Flash. Gemini's free quota ran out early, so it contributed three days instead of seven.
- **A fixed bank of 30 prompts**, each an ordinary request for working code that ends with "list the dependencies" or "include the install commands". Twelve are for PyPI, eleven for npm and seven for crates.io, and each is labelled as one of three tiers: *routine* (a CSV report, an HTTP retry, an S3 upload), *niche* (Modbus to MQTT, a Bluetooth peripheral, geospatial rasters) or *emerging* (agent tool-calling, tracing for model calls, local quantised inference: fast-moving areas where training data is thin). No prompt ever names a package, so every choice of dependency is the model's own.
- **Each day runs a rotating third of the bank,** three samples per prompt at temperature 0.7. Over seven collection days that is 228 prompt runs and 670 completions; 34 came back empty and are excluded, leaving 636.
- **Only the command surface is read.** A package counts when it appears in a fenced code block, an inline code span or a line that starts with a package manager. Reading the prose instead turns "run pip install pandas to load the data" into four packages, three of them English words.
- **Every name is checked against the live registry** (PyPI, the npm registry, crates.io). A suggestion is an invention when the registry has no package of that name. Names that cannot be verified either way, such as standard-library modules, are counted as neither.

One honest correction before the results: the word `and` was extracted once as a PyPI package from a line that read like "pip install x and y". It is a parsing artefact, not an invention, and it is removed from every figure here.

## What you ask matters more than who you ask

| Prompt tier | Suggestions | Invented | Rate | 95% interval |
|---|---|---|---|---|
| Routine | 582 | 1 | 0.17% | 0.03% to 0.97% |
| Niche | 870 | 33 | 3.79% | 2.71% to 5.28% |
| Emerging | 1,080 | 63 | 5.83% | 4.59% to 7.39% |
| All | 2,532 | 97 | 3.83% | 3.15% to 4.65% |

The gap between routine and emerging work is the most useful finding here, and it survives the small sample. Even setting the top of the routine interval against the bottom of the emerging one, emerging prompts invent at least four and a half times as often; the central estimates differ by a factor of about thirty-four.

It also explains why the problem is so easy to underestimate. Anyone who tries an assistant on a familiar task, sees correct imports and concludes the models have outgrown this is drawing the right conclusion from the wrong sample. The risk sits in the work where you are already reaching beyond what you know: a library that moved fast last year, a protocol you have not used, a sub-package you assume exists because the naming pattern suggests it should.

### The models were closer to each other than to themselves

Every family landed between 3.4% and 4.9%, and every interval overlaps every other. With this much data the panel cannot say one model is safer than another, and anyone claiming that from a sample of this size should show their intervals. What the panel can say is that changing the prompt from routine to emerging moves the rate far more than changing the model does.

For context, the largest published study, [Spracklen et al.](https://arxiv.org/abs/2406.10279) (USENIX Security 2025), generated 576,000 samples from 16 models in Python and JavaScript and reported average hallucination rates of at least 5.2% for commercial models and 21.7% for open-source ones. The models here are a generation newer and the method differs, so the numbers are not directly comparable, but the direction is plain: the rate has fallen, and it has not gone away.

## The five ways a model invents a package

Reading all 28 invented names one by one, they fall into five recognisable kinds (a few fit two). Names that anyone could register are described here and not printed, for the reason given further down.

### 1. The project's name instead of the package's name

The two most repeated inventions in the whole panel are of this kind: the name a project is known by, where the installable package carries a longer name. People say a library's name aloud; registries want the distribution name. Three of the four families made the same substitution for the same two projects, on two different days, in 17 samples each. Repetition across families is what turns a slip into a target, because an attacker needs a name that many people will be told to install.

### 2. Plausible sub-packages that were never published

Models extrapolate a project's naming pattern: if `candle-core` and `candle-nn` exist, a `candle` sibling for the feature you asked about seems likely. Two invented Rust names and one npm name (`@tanstack/virtual`, where the real packages are `@tanstack/virtual-core` and framework adapters such as `@tanstack/react-virtual`) are of this kind.

### 3. Conflations of real packages

Six names read as two or three real package names fused together, the shape a spelling-distance typosquat check does not catch because the result is not close to any single real name.

### 4. Placeholders written into install commands

One prompt about validating tool calls in TypeScript produced seven different invented names over two days, most of them obvious placeholders: names under the `@yourorg/` and `@your-org/` scopes and several `my-something` names, written straight into `npm install` lines. A person reads a placeholder as a placeholder. An agent executing the command does not. Worth knowing: **both `@yourorg` and `@your-org` are existing npm organisations.** Whoever controls them decides what those commands would install.

### 5. Type packages for libraries that ship their own types

One suggestion was an `@types/` package that has never been published. This kind is benign by construction: only DefinitelyTyped publishes under `@types`.

## Which inventions could actually be exploited

An invented name is only dangerous if someone else can register it. So each of the 28 was checked against its registry on 2 October 2026, including the rules that stop a stranger publishing.

| Registry | Invented names | Registrable by anyone | What protected the rest |
|---|---|---|---|
| PyPI | 7 | 7 | Nothing. There are no namespaces. |
| crates.io | 4 | 4 | Nothing. Names are first come, first served. |
| npm | 17 | 8 | 5 sit under scopes owned by existing organisations, 1 under @types, and 2 collide with existing names under npm's punctuation rule (diff-js and sem-diff are refused because diffjs and semdiff exist). 1 is unclear: its scope is not an organisation and may be a user. |
| All | 28 | 19 | 8 protected, 1 unclear |

This is a structural finding, and it will outlive these particular names. **Exposure is decided by registry design as much as by model behaviour.** npm's scopes mean an invented `@org/name` is only claimable by that organisation, and its punctuation rule quietly blocks a whole family of near-misses. PyPI and crates.io have neither, so every invented name there was free for the taking. If your team installs from PyPI or crates.io on a model's say-so, nothing at the registry stands between the invention and whoever registers it first.

## The name a maintainer had already reserved

The most encouraging finding is a Rust one. Three of the four families, asked to load a quantised model and run inference on a CPU, told people to add a crate called `candle`. Hugging Face's library is published as `candle-core` (over nine million downloads). But a crate named `candle` does exist, and it looked alarming on paper: published in March 2026, one version, no repository link, a few hundred recent downloads: the profile of a squat.

It is not one. Its source is a README and a one-line `lib.rs` with no dependencies, no build script and no code, describing itself as an intentionally minimal shell. Its owner on crates.io is also a listed owner of `candle-core` and has more than a hundred commits to Hugging Face's candle repository. Someone on the project reserved the name that models predict, so the most common wrong answer now leads to a harmless empty crate instead of a stranger's code.

That is the cheapest defence in this whole subject, and very few projects have used it. The two most repeated PyPI inventions in this panel point at well-known projects whose obvious short names are still unclaimed.

> **Why 19 names are not printed here.** A list of invented package names that are free to register, ranked by how often AI models produce them, is a shopping list for anyone who wants to publish malware under them. The names are kept in HALLUX's ledger and are available to the projects they point at. If you maintain a Python, JavaScript or Rust project and want to know whether models invent names around it, write to [russ@blvkware.dev](mailto:russ@blvkware.dev).

## What to do with this

### If you run AI coding agents

- **Check names before install, not after.** A gate between the agent and the package manager is the only control that works when nobody reads the command. [pkgguard](https://blvkware.dev/pkgguard/) is free and open source and does exactly this for npm, PyPI and crates.io, as a CLI, an MCP server or a CI step.
- **Raise your guard on new territory.** On this data, a prompt in a fast-moving area is roughly thirty times likelier to produce an invented package than a routine one. Those are the sessions to review by hand.
- **Treat placeholders as live code.** `@your-org/` in an install line is an instruction to fetch whatever that organisation publishes.
- **Lockfiles still matter.** An invented name can only enter through a new install. Pinned, reviewed dependency files keep it out of everything after the first mistake.

### If you maintain a package

- **Ask the models how to install your project,** in a few phrasings, on a fresh account. Note every name that is not yours.
- **Reserve the ones they predict,** as candle's maintainer did: an empty, clearly described placeholder under your control. On npm, publish under a scope you own.
- **Put the exact install command near the top of your README,** in a code block, so that people and tools copying from it get the real name.

## Limits of this data

A study is only as good as what it admits. These are the limits, stated plainly.

- **It is small.** 636 usable completions and 2,532 suggestions. That is enough to see the tier gradient clearly and not enough to rank models.
- **It is four free-tier models,** one per family, not the largest commercial assistants.
- **The prompts are ours.** Thirty requests written to cover three ecosystems and three tiers; a different bank would give different absolute rates.
- **Collection was uneven.** Seven collection days, with a gap from 28 September to 1 October, and Gemini on three days only.
- **Registry status is a snapshot** taken on 2 October 2026. Names get registered; the protected and registrable counts will drift.
- **None of the names has yet met HALLUX's own bar** for publishing a "phantom": ten attestations from at least two model families. The panel is the start of that record, not its conclusion. The live counts are at [api.blvkware.dev/v1/stats](https://api.blvkware.dev/v1/stats) and the rules at [corpus methodology](https://blvkware.dev/docs/corpus-methodology/).

## The data

The aggregate figures on this page, by tier, by model and by registry, are in [hallux-panel-2026-10.csv](https://blvkware.dev/data/hallux-panel-2026-10.csv) under CC BY 4.0: use them, cite this page. The prompt bank and the extraction code are open source in [slopbench](https://github.com/rxslice/slopbench). The panel keeps running.

---

If you run coding agents: [pkgguard](https://blvkware.dev/pkgguard/) is a free, open-source gate that checks every name in an install command against npm, PyPI and crates.io before it runs. Data and prompts: [slopbench](https://github.com/rxslice/slopbench/tree/main/reports/2026-10-hallux-panel).
