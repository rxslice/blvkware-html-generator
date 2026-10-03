# Research launch: where AI coding models invent packages (2 Oct 2026)

Canonical page: https://blvkware.dev/ai-package-hallucination-data/ (live, in the sitemap,
sent to IndexNow). Data: `/data/hallux-panel-2026-10.csv`, and on GitHub at
https://github.com/rxslice/slopbench/tree/main/reports/2026-10-hallux-panel

Already published: the site, GitHub (slopbench report), links from /pkgguard/ and /hallux/.
Posting to HN and X from here was blocked by the permission system, so these are yours to post.
Every number below comes from the page; `check.py` holds the limits and the copy rules.

## Hacker News (account `blvkware`, logged in)

Submit as a link, original title, no "Show HN" (it is research, not a product). Weekday
morning US Eastern is best. Then add the first comment below straight away.

```post name="HN title" limit=80
AI models invent packages at the frontier, not in the basics
```

```post name="HN first comment" limit=2000
Author here. This is a small panel, not a big benchmark: four model families (gpt-oss-120b, Qwen3.8 27B, Nemotron 3 Super, Gemini 2.5 Flash), 30 prompts across PyPI, npm and crates.io, three samples each, seven collection days. 2,532 package suggestions, read only off code blocks and install lines, each checked against the live registry.

Three things surprised me. The tier gradient: 1 invented package in 582 suggestions on routine prompts, 63 in 1,080 on fast-moving topics. The models were statistically indistinguishable from each other. And registry design decided exposure: every invented PyPI and crates.io name was free to register, while npm scopes and its punctuation rule protected about half of the npm ones.

I have not published the 19 names anyone could register today. Happy to answer questions about the method, and corrections are welcome: intervals are on the page.
```

## X thread (@BlvkWare, logged in)

Attach `docs/assets/og/ai-package-hallucination-data.png` to the first post. Before typing,
click inside the composer: typing with focus elsewhere fires X's keyboard shortcuts.

```post name="Research X 1" limit=280
I asked four AI model families for code 670 times and checked every package they told me to install.

3.8% of 2,532 named a package that does not exist.

The surprise is where: 0.2% on routine tasks, 5.8% on fast-moving ones.

https://blvkware.dev/ai-package-hallucination-data/
```

```post name="Research X 2" limit=280
The model barely mattered. gpt-oss-120b, Qwen3.8, Nemotron 3 Super and Gemini 2.5 Flash all landed between 3.4% and 4.9%, with overlapping intervals.

Changing the prompt from routine to fast-moving moved the rate far more than changing the model.
```

```post name="Research X 3" limit=280
Exposure is decided by the registry.

Of 28 invented names, 19 could be registered by anyone today: every PyPI one, every crates.io one, 8 of 17 on npm.

npm's scopes and its punctuation rule quietly protected the rest.
```

```post name="Research X 4" limit=280
Best finding: three model families told people to add a Rust crate called candle. The real library is candle-core.

That crate exists, and it is an empty placeholder owned by a candle-core maintainer. They reserved the name the models predict. Few projects have.
```

```post name="Research X 5" limit=280
Models also write placeholders straight into install commands, like npm install @your-org/ followed by an invented package name.

A person reads that as a placeholder. An agent runs it. Both @yourorg and @your-org are real npm organisations.
```

```post name="Research X 6" limit=280
I have not published the 19 registrable names: that list would be a shopping list.

If you run coding agents, gate installs before they run. pkgguard is free and open source:
https://blvkware.dev/pkgguard/

Aggregate data is CC BY 4.0, on the page.
```

## LinkedIn

```post name="Research LinkedIn" limit=3000
I ran a small experiment over 11 days: four AI model families, asked for working code with install commands, every suggested package checked against the real registry.

2,532 suggestions. 97 named a package that does not exist (3.8%).

The part worth knowing if your team uses AI coding tools: on routine tasks it happened once in 582 suggestions. On fast-moving topics, the new libraries and protocols where people lean on AI most, it was one in seventeen.

The model mattered far less than the task. And whether an invented name can be exploited depends on the registry: every invented Python and Rust name could be registered by anyone, while npm's scopes protected about half.

One maintainer team had already closed the gap for their project by reserving the name models kept getting wrong. Few have.

Full data, method and limits: https://blvkware.dev/ai-package-hallucination-data/
```

## dev.to, Hashnode, Medium

`research-article.md` is the whole article in Markdown with `canonical_url` set to the
blvkware.dev page, so the search credit stays with the site. dev.to: paste it as a new post
(the front matter is dev.to's format). Medium: use "Import a story" with the page URL, which
sets the canonical link itself. Hashnode: paste the body and set the canonical URL in the
post settings. None of these accounts are logged in on this machine; signing up is yours.

## Who else should see it (no posting needed, just a link)

- Maintainers whose projects the withheld names point at: offer the names privately. Ask before
  sending anything; nothing has been sent.
- The OpenSSF and PyPI security contacts may want the registry finding (no namespaces on PyPI
  means every invention is registrable).
