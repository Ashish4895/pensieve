# Task 10 Report: ADRs + regression

## Changes

- Added ADR 001 for HTTP-only JWT refresh cookies, CSRF protection, rotation,
  and blacklisting.
- Added ADR 002 retaining `pensieve` as the Django project package name.
- Marked the approved design specification as Plan 1 complete.

## Verification

- Command: `DATABASE_URL=postgres://pensieve:pensieve@127.0.0.1:5433/pensieve_plat python run.py test`
- Result: **34 passed, 15 warnings in 1.88s**.
- The first run exposed a local PostgreSQL privilege issue creating the
  `vector` extension. The suite passed after temporarily granting extension
  creation privilege; the `pensieve` role was restored to non-superuser.
- No AUTH_USER_MODEL or JWT regressions were found.

## Commit

`docs: add Plan 1 ADRs`

## Final review blocker fixes

- Isolated Compose as `pensieve-platform` on Postgres `5434`, Redis `6380`,
  and backend `8001`, with project-specific volumes.
- Invalid refresh cookies now become enveloped HTTP 401 responses.
- Production settings require `DJANGO_SECRET_KEY`; the development fallback is
  explicitly insecure and used only with `DEBUG=true`.
- DRF defaults to `IsAuthenticated` while schema and Swagger remain public.
- Removed the stale root Dockerfile, refreshed local setup docs, and synchronized
  the compatibility requirements file with the uv project dependencies.
- Repaired the ignored root `.env` key boundary locally; it remains uncommitted.

### Verification

- Prepared local PostgreSQL 16 template:
  `/opt/homebrew/opt/postgresql@16/bin/psql -h 127.0.0.1 -p 5433 -d template1 -c "CREATE EXTENSION IF NOT EXISTS vector;"`
- Full suite:
  `DATABASE_URL=postgres://pensieve:pensieve@127.0.0.1:5433/pensieve_plat DJANGO_SECRET_KEY=test-only-secret-at-least-32-bytes-long python run.py test --create-db`
- Result: **35 passed, 16 warnings in 1.78s**.
- `python run.py backend-check`: **0 issues**.
- `docker compose config --quiet`: **passed**.
