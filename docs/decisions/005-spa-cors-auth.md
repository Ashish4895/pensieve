# ADR 005: SPA CORS, cookie refresh, and SSE query access

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

The React SPA on Vite (`5173`) and nginx (`8080`) must call credentialed `/api/v1/`
endpoints. Refresh tokens remain httpOnly cookies. Browser `EventSource` cannot
set `Authorization` headers.

## Decision

Enable `django-cors-headers` with an explicit origin allowlist and
`CORS_ALLOW_CREDENTIALS=True`. Keep access tokens in Redux memory (never
`localStorage`). For SSE, accept a short-lived access JWT via `?access=` in
addition to the Bearer header. Proxies and logs must not record SSE query
strings.

## Consequences

- SPA origins must stay listed in `CORS_ALLOWED_ORIGINS` and
  `CSRF_TRUSTED_ORIGINS`.
- Query-string JWTs slightly widen token exposure via Referer/logs; mitigate by
  short access TTL and redaction.
