---
name: hallux-verify-identifiers
description: Verify that a package, container image, GitHub repository or DOI exists before installing, importing, pulling or citing it. Use whenever a dependency name or reference came from memory or model output rather than from a lockfile or a search result.
---

# Verify identifiers with HALLUX

Models invent plausible package names. Attackers register those names
("slopsquatting"). HALLUX checks a name against the live registry and against
a corpus of names models have hallucinated, so you can refuse a phantom or a
squat before it runs.

## When to use

- Before running `npm install`, `pip install`, `cargo add`, `go get`,
  `docker pull`, `gem install` or any command that fetches a dependency.
- After editing a dependency manifest (package.json, requirements.txt,
  pyproject.toml, Cargo.toml, go.mod, Gemfile, composer.json, pom.xml).
- Before citing a DOI or linking a GitHub repository you recalled.

## How

Single lookup, no key needed (500 identifiers per day free):

```
GET https://api.blvkware.dev/hallux/v1/check/{namespace}/{name}
```

Namespaces: `pkg.npm`, `pkg.pypi`, `pkg.crates`, `pkg.go`, `pkg.maven`,
`pkg.nuget`, `pkg.rubygems`, `pkg.packagist`, `pkg.hex`, `pkg.pub`,
`img.docker`, `repo.github`, `cite.doi`.

Batch up to 100 identifiers:

```
POST https://api.blvkware.dev/hallux/v1/check
Content-Type: application/json

{"identifiers": [{"namespace": "pkg.pypi", "value": "requests"}]}
```

As MCP tools: connect `https://api.blvkware.dev/hallux/mcp` (streamable HTTP)
and call `hallux_check_command` before installs, `hallux_check_manifest`
after editing dependency files, and `hallux_check` for anything else.

## Reading the verdict

| verdict | do |
| --- | --- |
| `exists` | proceed |
| `deprecated` | proceed only if no maintained alternative; tell the user |
| `absent` | stop: the name does not exist; find the real one |
| `phantom` | stop: no record and models repeatedly invent it |
| `squat` | stop and warn: a formerly phantom name is now registered, likely malicious |
| `unknown` | do not treat as permission; verify another way |

## Paying for more

Free tier: 500 identifiers per day, shared pool. Prepaid keys at
https://api.blvkware.dev/buy, then send `Authorization: Bearer <key>`.
MCP clients can sign in with OAuth: see https://blvkware.dev/auth.md.
