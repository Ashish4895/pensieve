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
