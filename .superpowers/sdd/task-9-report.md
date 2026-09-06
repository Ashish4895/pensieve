# Task 9 Report: ChatService extraction

## Status

Complete.

## Changes

- Added `ChatService` with send, history, and clear operations.
- Added `RateLimitExceeded` for explicit HTTP 429 mapping.
- Refactored legacy chat views to delegate to the service while preserving response bodies and status codes.
- Kept completed-turn persistence after provider success and made the two message inserts atomic.
- Did not add `/api/v1/chat`.

## TDD and verification

- Red: `test_chat_service.py` initially failed with 3 missing-module failures.
- Green: `python run.py test chatbot/tests/test_chat_service.py chatbot/tests/test_views_byok.py -q`
- Result: 16 passed, 12 pre-existing environment/deprecation warnings.
- `git diff --check` passed; edited files have no IDE linter diagnostics.

## Self-review

- Provider failures and rate-limit rejection do not persist messages.
- Legacy views intentionally retain dependency aliases so existing mocks remain compatible.
- No API keys are persisted or returned.

## Concerns

None blocking. Existing warnings cover Google GenAI Python 3.14 deprecation and a missing `staticfiles/` directory.
# Task 9 Report: `setup_application` + Swagger smoke

## Changes

- Added an idempotent `setup_application` command that applies migrations.
- Added optional `PENSIVE_BOOTSTRAP_EMAIL` and `PENSIVE_BOOTSTRAP_PASSWORD`
  support to create or update a `super_admin`.
- Documented root-level `python run.py setup` usage in `AGENTS.md`.

## Verification

- Root dispatcher setup against the requested database — passed.
- Idempotent bootstrap smoke (run twice, one super admin) — passed.
- `pytest core/tests/test_setup_application.py -q` — **1 passed**.
- `python manage.py check` — no issues.
- Django client `GET /api/docs/` — **200**.

## Commit

`feat: add setup_application management command`
