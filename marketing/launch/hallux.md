# Launch copy: HALLUX, pkgguard and slopbench

For developers and people building agents. The hook is concrete and testable in one
command: **models invent package names, attackers register the ones they keep inventing,
and HALLUX checks a name against its registry before anything installs it.**

Every claim here is checkable against a live endpoint, which is the point: an HN reader
will run the curl before reading the second paragraph.

Links: `https://blvkware.dev/hallux/` · MCP `https://api.blvkware.dev/hallux/mcp` ·
spec `https://blvkware.dev/docs/hallux-spec` · pkgguard `https://blvkware.dev/pkgguard/` ·
slopbench `https://github.com/rxslice/slopbench`

---

## Show HN

Post on a weekday morning, US Eastern. Stay in the thread for the first two hours.

```post name="HN title" limit=80
Show HN: HALLUX, check if a package your AI suggested actually exists
```

```post name="HN url" limit=200
https://blvkware.dev/hallux/
```

```post name="HN first comment" limit=5000
Hi HN. Coding agents regularly name dependencies that do not exist. Usually the install fails and the agent retries. The bad case is when a name comes up often enough that someone registers it and waits: slopsquatting.

HALLUX answers one question before an agent installs, imports or cites something: does this identifier exist in the registry that owns it? It covers npm, PyPI, crates.io, Go, Maven, NuGet and DOIs, and returns one of six verdicts: exists, deprecated, absent, phantom, squat or unknown.

Try it with no key:

    curl https://api.blvkware.dev/hallux/v1/check/pkg.pypi/requests-oauth2-helper

It is also an MCP server, so a coding agent can check an install command before running it:

    claude mcp add --transport http hallux https://api.blvkware.dev/hallux/mcp

Things I tried to get right:

- A registry it cannot reach answers "unknown" with a reason, never a pass.
- Billing is a function of how many names you ask about, never of the verdict. The quoting function has no parameter a verdict could reach, and a test asserts the charge is identical whatever a batch resolves to. A checker paid per block has a reason to block.
- "phantom" means a name models repeatedly invent that no registry has. The ledger behind it is filled by a daily panel of models from different families, and a name needs 10 attestations from 2 families and absence confirmed twice, 24 hours apart. That ledger started this week, so it is still close to empty, and the method is public: https://blvkware.dev/docs/corpus-methodology

The pre-install gate it grew out of, pkgguard, is Apache 2.0 and runs locally: https://blvkware.dev/pkgguard/

Open tier is 500 names a day per client, no account. I would like to hear where it is wrong.
```

## r/mcp, r/ClaudeAI, r/ChatGPTCoding, r/LocalLLaMA

```post name="Reddit dev title" limit=300
Free MCP server that stops your coding agent installing packages that do not exist (npm, PyPI, crates, Go, Maven, NuGet)
```

```post name="Reddit dev body" limit=40000
Agents invent dependency names, and some of the invented names get registered by someone waiting for exactly that. I built a check for it and exposed it as a remote MCP server, so the agent calls it on its own before running an install.

Connect (no account, no key):

    claude mcp add --transport http hallux https://api.blvkware.dev/hallux/mcp

Any MCP host takes the same URL (Streamable HTTP). Tools:

- hallux_check_command: pass the install command before it runs
- hallux_check_manifest: pass a package.json, requirements.txt, pyproject.toml, Cargo.toml or go.mod after editing it
- hallux_check: check identifiers directly

A registry that does not answer comes back unknown, never as a pass. Free tier is 500 names a day per client.

Page and spec: https://blvkware.dev/hallux/

If you would rather run the check locally, pkgguard is the Apache 2.0 gate it came from: https://blvkware.dev/pkgguard/
```

## X (thread)

Attach to the first post: `docs/assets/og/hallux.png`

```post name="X dev 1" limit=280
Your coding agent will eventually run pip install on a package that does not exist.

HALLUX checks the name against its registry first. npm, PyPI, crates, Go, Maven, NuGet, DOIs. Free, no key:

curl https://api.blvkware.dev/hallux/v1/check/pkg.pypi/requests-oauth2-helper
```

```post name="X dev 2" limit=280
It is an MCP server too, so the agent asks on its own before installing:

claude mcp add --transport http hallux https://api.blvkware.dev/hallux/mcp
```

```post name="X dev 3" limit=280
The part I care about most: it is billed on how many names you ask about, never on what the answer is. A checker paid per block has a reason to block you. This one cannot, and a test proves the charge is the same whatever the verdict.
```

## MCP directories

Submit the same listing to the official MCP Registry, Smithery, Glama, mcp.so and PulseMCP.
Transport: Streamable HTTP. Auth: none. URL: `https://api.blvkware.dev/hallux/mcp`.

```post name="MCP listing name" limit=40
HALLUX
```

```post name="MCP listing short" limit=100
Check that a package, module or DOI exists before an agent installs, imports or cites it.
```

```post name="MCP listing long" limit=1000
HALLUX checks identifiers against the registry that owns them before an agent acts on them: npm, PyPI, crates.io, Go modules, Maven, NuGet and DOIs. Six verdicts: exists, deprecated, absent, phantom (a name models repeatedly invent), squat (such a name that someone has since registered) and unknown. Tools: hallux_check_command reads an install command before it runs, hallux_check_manifest reads a dependency file after an edit, hallux_check takes identifiers directly. A registry that cannot be reached returns unknown, never a pass. No account and no key; the open tier allows 500 identifiers a day per client.
```
