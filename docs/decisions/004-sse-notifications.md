# ADR 004: DB-backed notifications with SSE delivery

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

Pensieve needs a user-scoped notification inbox for ingest completion and
future product events. Real-time delivery must work in the browser without
committing to WebSocket infrastructure in Plan 2. Notifications must survive
page reloads and reconnects; the stream is a transport, not the system of
record.

## Decision

Persist notifications in Postgres (`Notification` model, per-user rows). Expose
a panel API (`GET /api/v1/notifications/`, mark-read) for listing and state.
Deliver live updates via authenticated SSE at
`GET /api/v1/notifications/stream/` using `StreamingHttpResponse` with
`text/event-stream`, ~15s heartbeat comments, and event ids equal to the
notification primary key. Clients reconnect with the `Last-Event-ID` header;
the server resumes from `id__gt last_event_id`. Ingest completion creates a
notification row for the requesting user after the Celery task finishes.

Because the browser `EventSource` API cannot set an `Authorization` header, the
stream also accepts a short-lived access JWT in the `access` query parameter.
Header authentication remains preferred for non-browser clients. Proxies and
application logging must not record SSE query strings.

Defer WebSocket auth and a WS notification channel to Plan 3 (React frontend
slice). SSE is sufficient for Plan 2 backend and template-UI consumers.

## Consequences

- Notifications are durable and queryable independent of an open SSE connection.
- Reconnect semantics depend on monotonic integer ids; clients must store the
  last seen id.
- Long-lived SSE connections require ASGI-friendly async iteration (Uvicorn);
  nginx buffering must stay disabled (`X-Accel-Buffering: no`) when proxied.
- WebSocket parity (bidirectional chat, unified realtime layer) waits for Plan 3.
- Missed events while offline are recoverable via the list API, not only SSE.
