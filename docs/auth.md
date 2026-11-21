# BlvkWare auth.md

How an AI agent gets credentials for BlvkWare's APIs and MCP servers, and how
to use them. Machine-readable versions:
[authorization server metadata](https://blvkware.dev/.well-known/oauth-authorization-server)
and [protected resource metadata](https://blvkware.dev/.well-known/oauth-protected-resource).

## Who this is for

Agents and MCP clients calling:

- **HALLUX**: `https://api.blvkware.dev/hallux/v1` and MCP at `https://api.blvkware.dev/hallux/mcp`
- **CORDON**: `https://cordon.blvkware.dev/v1` and MCP at `https://cordon.blvkware.dev/mcp`

## You may not need credentials at all

Both services have an open tier that needs no account and no key:
HALLUX answers 500 identifiers per day, CORDON 50 units per day. Call the
endpoints without an `Authorization` header.

## Credential: a BlvkWare API key

One key works on HALLUX and CORDON. Keys look like `bk_live_...` and are shown
once when issued. We store only a SHA-256 hash of each key.

Send it on every request, either way:

```
Authorization: Bearer bk_live_...
X-API-Key: bk_live_...
```

### Getting a key (human in the loop)

A person buys prepaid credit at https://api.blvkware.dev/buy (PayPal) and
receives the key on the confirmation page. An agent should hand the user that
link rather than trying to pay itself.

### Getting a key into an MCP client (OAuth 2.1)

MCP clients that support OAuth can connect without anyone pasting a key into
a config file:

1. **Register** (anonymous, no identity required): `POST https://blvkware.dev/oauth/register`
   with `{"redirect_uris": ["https://your.client/callback"], "client_name": "..."}`.
   Returns a `client_id`. Public clients only (`token_endpoint_auth_method: none`).
2. **Authorize**: send the user to `https://blvkware.dev/oauth/authorize` with
   `response_type=code`, `client_id`, `redirect_uri`, `state`,
   `code_challenge` and `code_challenge_method=S256`. The user pastes their
   BlvkWare key once; we check it against the API and redirect back with a code.
3. **Token**: `POST https://blvkware.dev/oauth/token` with
   `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id` and
   `code_verifier`. The `access_token` is the user's API key, used as a
   Bearer token on both services. Codes expire after five minutes.

Scopes: `hallux`, `cordon` (one key covers both; scopes are informational).

The `agent_auth` block in the authorization server metadata summarises this:
`register_uri` is the registration endpoint above, `claim_uri` is the
authorize endpoint where the user binds their key, and the only identity type
is `anonymous` (no identity is needed to register; the user's key is the
claim), issuing an `access_token`.

### Paying per call instead (CORDON only)

CORDON accepts x402 (v2, USDC on Base). An unpaid HTTP call returns `402` with
payment requirements; over MCP, an unpaid call returns a `PaymentRequired`
tool result and you retry with the payment in `params._meta["x402/payment"]`.

## Revocation

Subscription keys can be replaced (the old key stops working) at
https://blvkware.dev/hallux/recover/. For a prepaid key, email
agents@blvkware.dev from the address on the receipt.

## Errors

- `401 invalid_api_key`: the key is wrong or revoked. Drop it and fall back to the open tier.
- `402`: credit exhausted, or x402 payment required.
- `429`: the open tier's daily allowance is used up.
