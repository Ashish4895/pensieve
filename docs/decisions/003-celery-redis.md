# ADR 003: Redis as Celery broker and Django cache

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

Plan 2 (slices 3–5) moves document ingest off the web request thread. Celery
needs a broker and result backend; Django also needs a shared cache for future
throttling and session-adjacent work. Local development runs Redis via Compose
while pytest must not require a live worker or Redis instance.

## Decision

Use a single `REDIS_URL` for Django `CACHES["default"]` (Redis backend), Celery
broker, and Celery result backend. Compose exposes Redis on host port **6380**
(mapped to container 6379) alongside Postgres **5434** and backend **8001**.
Inside Compose, services use `redis://redis:6379/0`; on the host the default is
`redis://127.0.0.1:6380/0`.

Run Celery worker and beat as separate Compose services sharing the backend
image and Django settings module. Keep ingest logic in a service; Celery tasks
stay thin wrappers. In tests, use `CELERY_TASK_ALWAYS_EAGER=True` (via
`@override_settings` or pytest defaults) so unit tests enqueue synchronously
without a worker process.

## Consequences

- One Redis instance serves cache, broker, and results; ops stay simple for Plan 2.
- Host port 6380 avoids clashing with a local Redis on 6379.
- Eager mode hides broker wiring bugs in tests; integration smoke against real
  worker/Redis remains deferred (Docker Celery smoke not in Plan 2 scope).
- Production must run worker and beat; web process alone cannot drain the queue.
- `reload_celery` remains dev-only (`DEBUG=True`); never enable autoreload in prod.
