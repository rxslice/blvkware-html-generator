# Launch pack

Ready-to-paste copy and the images that go with it. Posting needs your own accounts,
so nothing here posts itself.

| File | For | Audience |
|---|---|---|
| `kits.md` | Product Hunt, LinkedIn, X, Reddit, Indie Hackers, Google Ads, Meta ads | Business owners |
| `hallux.md` | Show HN, developer subreddits, X, MCP directories | Developers, agent builders |
| `check.py` | Holds every block to its platform limit, the site's prices and the copy rules | You, before pasting |

Run `python marketing/launch/check.py` after editing any copy. It fails on a block over
its limit, an em or en dash, a price the site does not charge, or a count (jobs, free
checks a day) that no longer matches the catalog or HALLUX.

## Status

| Channel | Status | Needs |
|---|---|---|
| Official MCP Registry | **Listed 2026-09-22** as `dev.blvkware/hallux` (active) | Nothing. Updates: bump `version` in hallux `deploy/mcp-registry/server.json`, run `python dev/publish-registry.py publish` |
| mcp.so | **Submitted 2026-09-22**, [chatmcp/mcpso#4310](https://github.com/chatmcp/mcpso/issues/4310) | Nothing; watch the issue |
| mcpservers.org | **Submitted 2026-09-22**, free tier, review within 2 weeks | Nothing; approval email goes to russ@blvkware.dev |
| PulseMCP | Submissions paused on their side; they help run the official registry | Re-check later |
| Glama (HALLUX) | **Claimed 2026-09-23**, ownership verified (HTTP challenge served by the API at `/.well-known/glama.json`), thumbnail set; Healthy, TDQS A 4.3 | By hand: 3 categories (Developer Tools, Security, Coding Agents) and the Publisher profile; the form's pickers resist automation |
| Glama (pkgguard) | **Submitted for review 2026-09-23** (`rxslice/pkgguard-API`) | Wait for its page at glama.ai/mcp/servers/rxslice/pkgguard-API |
| awesome-remote-mcp-servers | **PR opened**, [punkpeye/awesome-remote-mcp-servers#553](https://github.com/punkpeye/awesome-remote-mcp-servers/pull/553); submission check passed | Maintainer merge |
| awesome-mcp-servers (pkgguard) | Ready, Security section | pkgguard's Glama page first, same reason |
| Smithery | **Listed 2026-09-23** as [`blvkware/hallux`](https://smithery.ai/servers/blvkware/hallux) (namespace `blvkware` created in the account), release SUCCESS, **quality 100/100** with the Typed Output badge (output schemas, full parameter descriptions, uploaded icon) | Optional: Smithery's verified badge needs a paid developer plan plus a DNS TXT record, so it is left alone |
| Show HN | **Refused 2026-09-23**: HN said it is not accepting posts right now "because of the recent surge in volume". The account `blvkware` was created that morning (karma 1), and new accounts are the likely target | Retry on a weekday morning ET; meanwhile a few genuine comments from the account; or ask hn@ycombinator.com (draft in the chat, 2026-09-23) |
| X | **Posted 2026-09-23** by @BlvkWare: full HALLUX thread (3 posts, `og/hallux.png` on the first), [status 2102654767977640348](https://x.com/BlvkWare/status/2102654767977640348) | Kits thread later (`kits.md` X 1-4) |
| Indie Hackers | **Product page live 2026-09-23**: [BlvkWare Agent Kits](https://www.indiehackers.com/product/blvkware-agent-kits) (motivation max 220 chars; tags AI, B2B, Bots, Productivity; solo, bootstrapped, Sales & Transactions). Account `AIWinLab` cannot create posts yet | Comment on a few posts to unlock posting; then `IH title`/`IH body` |
| Product Hunt | **Scheduled for 2026-09-29 12:01am PDT**: [BlvkWare Agent Kits](https://www.producthunt.com/products/blvkware-agent-kits) with `PH *` copy, thumbnail, 5 gallery images, tags AI / Productivity / No-Code, first comment | Upload `marketing/video/out/blvkware-kits-demo.mp4` to YouTube and paste the link in PH's video field; swap the thumbnail for `ph-thumbnail.gif`; add the three shoutouts (copy in `kits.md`). Be around on the 29th to answer comments; share the link on X/LinkedIn that morning |
| Reddit, LinkedIn | Copy in `kits.md` and `hallux.md` | Your accounts |
| Gumroad listings | **Done 2026-09-23**: both descriptions carry a "Read a real kit first" section linking `https://blvkware.dev/sample-kit/`, verified on the public pages | Nothing |

## Images

- Social cards, one per page: `docs/assets/og/<page>.png` (1200x630). Shared links pick
  them up automatically; attach them by hand where a post takes an image.
- Kit ads: `marketing/kits/out/` (square 1080, story 1080x1920, landscape 1200x628,
  Gumroad covers and thumbnails).

## Suggested order

1. **Developers first, because it costs nothing and is testable.** Show HN for HALLUX on a
   weekday morning, US Eastern; the same day, the MCP directory listings (official MCP
   Registry, Smithery, Glama, mcp.so, PulseMCP) and r/mcp.
2. **Kits the following week.** Product Hunt (launch at 12:01am Pacific), then LinkedIn,
   X and r/SideProject the same day, linking the sample kit.
3. **Paid, once organic has shown which message lands.** Google search ads to
   `/sample-kit/` on the keywords in `kits.md`; Meta with the square and story creative.
   Start small and compare against organic before scaling.

## Before posting

- The live site, `https://blvkware.dev/`, shows the Developers menu, the sample kit
  and the per-page social cards.
- Gumroad: both kit products are published. The listings would convert better with a
  link to `https://blvkware.dev/sample-kit/` in their descriptions (a listing edit, so yours).
- Nothing in the copy claims customers, testimonials or results that do not exist. Keep it
  that way: the sample kit is the proof.
