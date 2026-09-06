# Task 10 Report

## Status

Complete.

## Changes

- Added authenticated `POST /api/v1/chat/`, `GET /api/v1/chat/history/`, and `POST /api/v1/chat/clear/` DRF views.
- Required `X-API-Key` on all three endpoints and passed BYOK provider/model headers only to `ChatService`.
- Added standard success/error envelopes and mapped validation, provider auth, unsupported provider, rate-limit, and upstream errors.
- Preserved all legacy chat URL registrations and behavior.
- Added OpenAPI annotations and a schema regression test for all three paths.
- Removed the unused legacy `Message` import and corrected its stale test mock.

## TDD and Verification

- Red: 12 new API tests failed before implementation because all routes returned 404.
- Targeted: `24 passed` for v1 and legacy chat tests.
- Final full suite: `70 passed, 39 warnings` via `python run.py test -q`.
- Schema generation includes all three `/api/v1/chat/` paths.
- `git diff --check` and edited-file IDE lint checks passed.

## Self-review

- API keys are neither logged nor persisted by the new views.
- Authentication and missing-key failures use the standard error envelope.
- Known service failures map to the required HTTP statuses.
- Concern: chat history remains keyed only by client-provided `session_id`; the existing data model has no user ownership field, so cross-user isolation is not enforceable in this task.
- Existing schema warnings remain for unrelated unannotated APIViews (ingest and notifications).
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
