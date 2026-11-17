# Cloudflare Workers & Scheduled Agent Runtime Contract (`blvkware.dev`)

Companion operational standard referenced by `AGENTS.md` for `blvkware.dev` Cloudflare Workers, Cron Triggers, Queues, D1/KV, and Durable Objects powering products, APIs, indexing, and automated quality checks.

## 1. Concurrency & Single-Writer Leases
Cron Triggers and Queues deliver **at-least-once** and may overlap under load or retries:
- Acquire a distributed lease (`lease_key = "lock:{job_id}"`, bounded TTL > max step duration) in Durable Objects or D1/KV before executing mutating work.
- If lease acquisition fails, exit cleanly as a no-op; never run concurrent writers against the same customer, invoice, index batch, or deployment target.

## 2. Deterministic Idempotency & Reconciliation
- Every external side effect (Stripe/payment call, email/webhook dispatch, index submission, DNS/Wrangler mutation, order creation) MUST carry a deterministic idempotency key:
  - Format: `{job_id}:{window_or_run_id}:{entity_id}:{step}`
- Record `PENDING` intent in durable storage *before* making the external call, then update to `SUCCEEDED` or `FAILED` with provider reference ID.
- On worker restart or ambiguous timeout (`5xx` / network drop), **query the external provider using the idempotency key or reference ID** to reconcile state before deciding whether to retry.

## 3. Wall-Clock & Subrequest Chunking
- Workers have strict CPU, subrequest, and execution time limits. Never run unbounded `while` loops inside a single `fetch` or `scheduled` handler.
- Break batch workflows (crawling, indexing, quality probes, catalog syncs) into bounded chunks (e.g., 10–25 items per invocation), checkpoint the `cursor` after each item/chunk, and hand off remaining work via Cloudflare Queues or Durable Object `alarm()`.
- Use `ctx.waitUntil()` only for short non-blocking telemetry/cleanup—never for critical financial mutations or index commits that require guaranteed completion reporting.

## 4. Minimum Durable Checkpoint Schema
Persist per-run state in D1 or Durable Object storage using at least:
```json
{
  "run_id": "uuid",
  "job_id": "string",
  "status": "pending | running | blocked | completed | failed",
  "step": "string",
  "cursor": "string | null",
  "idempotency_key": "string",
  "spend_cents": 0,
  "consecutive_failures": 0,
  "last_error": "string | null",
  "updated_at": "ISO-8601"
}
```

## 5. Deployment & Secret Hygiene
- Store runtime secrets via `wrangler secret put` or encrypted environment bindings—never in `wrangler.toml`/`wrangler.jsonc`, `.dev.vars` committed to git, or source code.
- Before deploying a Worker to production:
  1. Run TypeScript check and test suite.
  2. Validate bindings and dry-run/preview deployment where supported.
  3. Hit health/smoke endpoints post-deploy and confirm `200` + expected schema before marking deployment complete.
  4. Retain previous deployment version ID for instant rollback on error spike.

## 6. `blvkware.dev` Domain Gates: Products, APIs, Indexing & Quality
- **APIs & Endpoints**: Validate authentication, rate limiting, metered/usage accounting, deterministic JSON error envelopes, and p95 latency/status health before and after deploys; auto-pause or roll back if error rates spike across 2 consecutive probe cycles.
- **Indexing & Agent Discoverability**: Verify `sitemap.xml`, `robots.txt`, canonical links, structured metadata (OpenGraph/JSON-LD), and machine-readable agent/API specs (such as `llms.txt`, OpenAPI, and product docs) return `200` with accurate live product state—and never ship accidental `noindex` headers or stale index entries.
- **Product & Quality Sweeps**: Scheduled quality checks must assert functional responses (live API JSON payloads, downloadable/previewable product artifacts, checkout/fulfillment flows, and non-broken assets), never treating an HTTP `200` HTML shell alone as passing.

