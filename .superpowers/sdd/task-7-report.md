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
