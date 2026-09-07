# Task 7 report

## Status

Complete. The notification stream now accepts a validated SimpleJWT access
token via `?access=`, and the React app has a Redux-backed inbox, mark-read
actions, and a native EventSource client.

## Verification

- Backend: 77 passed.
- Frontend: 12 passed.
- Frontend production build: passed.
- Focused SSE coverage verifies query-token authentication, event parsing,
  token URL encoding, error forwarding, closing, and replay deduplication.

## Self-review

No blocking issues found. Native EventSource owns automatic reconnect and sends
`Last-Event-ID`; the client also retains the latest id to suppress replay after
reconnection. Query-string JWTs are required by the EventSource API constraint;
ADR 004 now calls out that proxies and application logs must redact SSE query
strings. Existing staticfiles, bundle-size, Python dependency, and test-database
teardown warnings remain.
# Task 7 Report: Notifications model + list/mark-read API

## Status

Complete.

## Implementation

- Added the `notifications` Django app and registered it in `INSTALLED_APPS`.
- Added the user-owned `Notification` model with newest-first ordering.
- Added serialized list and idempotent mark-read endpoints under `/api/v1/notifications/`.
- Scoped both database queries to the authenticated user; cross-user mark-read returns 404.
- Created and applied `notifications/migrations/0001_initial.py`.

## TDD and verification

- Red: tests initially failed because `notifications.models` did not exist.
- Green: notification API tests passed (`2 passed`).
- Regression: complete backend suite passed (`47 passed`, 24 environment warnings).
- Django checks and `makemigrations --check` passed; lint and `git diff --check` were clean.

## Self-review

- No unrelated source files changed.
- The API uses existing DRF authentication and response-envelope patterns.
- No concerns; warnings are unrelated to this change.
