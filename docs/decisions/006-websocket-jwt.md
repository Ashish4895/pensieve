# ADR 006: WebSocket JWT auth via query token

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

Plan 3 requires ASGI WebSockets with authenticated connections. Browser
WebSocket constructors cannot set arbitrary headers reliably across stacks.

## Decision

Use Django Channels with a Redis channel layer. Authenticate
`ws/v1/chat/?token=<access_jwt>` through middleware that validates SimpleJWT
access tokens. Reject missing/invalid tokens with close code `4401`. Plan 3
ships a ping/pong consumer to prove the auth plumbing; chat turns remain HTTP.

## Consequences

- Same-origin nginx upgrades `/ws/` to the backend.
- Tokens in query strings share the SSE exposure caveats (short TTL, no logging).
- Future bidirectional chat can reuse the same middleware stack.
