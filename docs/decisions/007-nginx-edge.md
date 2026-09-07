# ADR 007: nginx as Compose edge proxy

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

The SPA must be served alongside `/api/` and `/ws/` without forcing developers
to juggle CORS in production-like local runs.

## Decision

Build the Vite app into a multi-stage `docker/nginx` image. Expose host port
**8080**. Proxy `/api/` and `/ws/` to `backend:8000` (with WebSocket upgrade and
SSE-friendly buffering off). Keep backend host port **8001** for direct debug.

## Consequences

- One URL origin for browser credentials under nginx.
- Frontend image rebuilds whenever SPA assets change.
- Render/cloud deploy remains a later concern.
