# Launch day: Tuesday 29 September 2026

Product Hunt launch: **BlvkWare Agent Kits**, scheduled for **12:01am Pacific = 2:01am Central**.
It goes live on its own. The PH day runs until 11:59pm Pacific (1:59am Wednesday, Central).

Every block named below is in `kits.md`, already checked by `check.py`.

| Link | |
|---|---|
| PH page | https://www.producthunt.com/products/blvkware-agent-kits |
| Kit page | https://blvkware.dev/hire/ |
| Free sample kit | https://blvkware.dev/sample-kit/ |
| Demo video | https://youtu.be/zI-yY7rHAv0 |

## Already done (checked 27 September)

- PH listing: name, tagline, description, 3 launch tags, paid pricing, animated thumbnail,
  6-item gallery with the demo video, maker, 5 shoutouts. PH's pre-launch dashboard shows
  every "strongly encouraged" item ticked.
- Pinned first comment, describing the runtime.
- Gumroad listings: current covers and bullets. Both pages checked live.
- The purchase path, checked live: kit page, then preview (both tiers), then Gumroad
  checkout, then licence check (made-up keys are refused).
- Kit page and homepage show a small "Live on Product Hunt today" link, only on the 29th
  (then "on Product Hunt" until 13 October). It is text only and loads nothing from PH,
  so the privacy notice stays true.

## The day (Central time)

| When | What |
|---|---|
| Mon night | Nothing required. The launch publishes itself. |
| 2:01am | Launch goes live. If you are up, open the PH page: it should show upvoting enabled and the pinned comment. |
| 7 to 9am | **X:** post `X launch day` on its own. Then the kits thread (`X 1` to `X 4`, image `docs/assets/og/sample-kit.png` on the first). |
| 7 to 9am | **LinkedIn:** `LinkedIn post` with `marketing/kits/out/operator-ad-landscape-1200x628.png`, then `LinkedIn launch day comment` as the first comment (links in comments reach further than links in posts). |
| Morning | **Indie Hackers:** if posting has unlocked, post `IH title` and `IH body`. |
| Late morning | **Reddit:** r/SideProject with `Reddit title` and `Reddit body`. Not r/smallbusiness outside its promotion thread. |
| All day | **Reply to every PH comment within the hour.** Drafts: `PH reply: ...` (12 of them). Rewrite them in your own words. |
| Evening | Record the result in `README.md` under Product Hunt: final rank, upvotes, comments, kit page visits if known, Gumroad sales. |

## Product Hunt rules that matter

- Never ask for upvotes, anywhere: not in posts, DMs or the site. "Would love your take" is fine.
  PH can demote launches for vote-asking, and voting rings get caught.
- No new accounts voting, and nobody upvoting from the same network as you.
- Answer questions straight, including "why would I not just use ChatGPT". A defensive reply
  costs more than a hard question.

## If something breaks

| Symptom | Check |
|---|---|
| "See your kit" spins or errors | `https://blvkware-kits.netlify.app/` must answer. Netlify's free plan pauses sites when credits run out (45 of 300 used on 27 Sep). Do not deploy on launch day unless something is broken. |
| Buyer says the key is refused | They are pasting it into a design for a different job (one key is bound to its first job), or the purchase was refunded. The error message says which. |
| Gumroad checkout fails | Gumroad status page. Nothing on our side is involved. |
| PH page looks wrong | Edit at `producthunt.com/posts/blvkware-agent-kits/edit`. The pinned comment is edited from the comment's "..." menu. |
