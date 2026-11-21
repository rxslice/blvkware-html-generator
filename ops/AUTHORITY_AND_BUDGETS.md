# Authority, Budgets & Escalation Contract

Companion policy referenced by `AGENTS.md`. Agents must inspect environment bindings, KV/D1 budget tables, or owner-approved config before requesting spend authority.

## 1. Authority & Spend Lookup Order
Resolve effective limits in this exact precedence order:
1. **Explicit Task Instruction**: Limits or grants stated directly in the authenticated owner's current prompt or signed task payload.
2. **Runtime Policy Store**: `POLICY` / `AUTHORITY` binding in Cloudflare KV/D1 or local `ops/limits.json` (if present).
3. **Default Autonomous Operating Envelope** (applies when no explicit override is configured so routine work never stalls):
   - **No-Cost & Reversible Engineering/Ops**: Fully authorized (builds, tests, staging deploys, local experiments, documentation, bug fixes, read-only market/API research).
   - **Verified Production Deploys**: Fully authorized once automated pre-flight checks (typecheck, lint/build, smoke test) pass and rollback target exists.
   - **Metered API / Infra Spend**: Authorized within recorded run/daily caps. If no explicit cap is configured anywhere, pause new capital commitments above micro-test thresholds, continue all zero-cost/reversible execution, and attach a `BLOCKER_REPORT` in the next digest requesting a configured `daily_cap_cents` and `per_action_cap_cents`.

## 2. Hard Financial & Destructive Guardrails
Never self-authorize these actions regardless of autonomy posture unless explicitly instructed by the authenticated owner:
- Changing verified payout/bank/wallet destinations or billing ownership.
- Deleting production databases, customer records, or primary storage without a verified, restorable snapshot.
- Splitting a single purchase/payout into multiple smaller transactions to stay under a per-action cap.
- Executing unverified bulk outbound campaigns before a canary send succeeds.

## 3. Spend-Velocity & Error Circuit Breakers
Every worker or scheduled run tracking paid APIs, infra provisioning, or billing actions must enforce:
- **Atomic Budget Reservation**: Reserve estimated cost (`spend_cents`) in durable state *before* invoking paid external APIs; reconcile actual cost afterward.
- **Velocity Breaker**: Automatically halt paid loops if burn rate exceeds 3x expected run baseline or hits 80% of daily cap without corresponding verified revenue/progress.
- **Provider Error Breaker**: Stop paid retries after 2 consecutive 4xx/5xx provider errors without new diagnostic evidence.

## 4. Structured Escalation (`BLOCKER_REPORT`)
Use this exact compact format only when an action is genuinely owner-only (e.g., 2FA, legal/KYC sign-off, missing billing method, or cap increase). Emit once, checkpoint state, and move to the next eligible task:

```yaml
BLOCKER_REPORT:
  task_id: "<id>"
  blocked_action: "<exact action paused>"
  reason: "<missing authority | owner-only auth | cap exceeded | repeated failure>"
  cost_or_risk: "<exact dollar amount or blast radius>"
  prep_completed: "<what is already built/staged and ready>"
  recommended_decision: "<single clear option to approve/reject>"
  next_active_work: "<what the agent is executing in the meantime>"
```
