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
