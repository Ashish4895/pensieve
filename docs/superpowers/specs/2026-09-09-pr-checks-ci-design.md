# PR Checks CI Design

**Date:** 2026-09-09  
**Status:** Approved — implemented  
**Approach:** A — GitHub Actions + service containers (checks only)  
**Product:** Pensieve

## 1. Context

Pensieve has no GitHub Actions workflows yet. Developers run tests locally via `python run.py test`, `python run.py backend-check`, and `python run.py frontend-test`. Backend tests require Postgres + pgvector and Redis (see `AGENTS.md`). Merge into `main` should not be possible while those checks fail.

## 2. Goals

- On every pull request targeting protected branches, run the full automated test suite.
- Block the GitHub merge button until required checks are green.
- Keep CI close to local commands (`run.py`) so failures are reproducible.

## 3. Non-goals

- Deploy to EC2, Render, or any other environment.
- Coverage thresholds, lint-only jobs, or security scanning (can be added later).
- Requiring a real `GEMINI_API_KEY` in CI (tests mock providers).

## 4. Trigger

File: `.github/workflows/pr-checks.yml`

```yaml
on:
  pull_request:
    branches: [main, platform]
```

No `push` deploy jobs. Optional later: same workflow on `push` to `main` for post-merge visibility only (not in this scope).

## 5. Jobs

Two parallel jobs. Both must succeed for the PR to be mergeable under branch protection.

### 5.1 `backend`

| Item | Value |
|------|--------|
| Runner | `ubuntu-latest` |
| Python | 3.13 (match `uv` Docker base) |
| Tooling | `astral-sh/setup-uv`, checkout |
| Services | `pgvector/pgvector:pg16` (port 5432), `redis:7-alpine` (port 6379) |
| Health | Wait on Postgres `pg_isready` / Redis `redis-cli ping` (Actions `options` healthchecks) |

Env (job-level, non-secret):

- `DATABASE_URL=postgres://pensieve:pensieve@localhost:5432/pensieve`
- `REDIS_URL=redis://localhost:6379/0`
- `DJANGO_SECRET_KEY=ci-not-a-secret`
- `DEBUG=true`
- `ALLOWED_HOSTS=localhost,127.0.0.1`
- `GEMINI_API_KEY=` (empty)

Steps:

1. Checkout  
2. Setup uv + Python  
3. From repo root: `python run.py backend-check`  
4. From repo root: `python run.py test` (pass `--create-db` if pytest-django needs it; match local `AGENTS.md`)

Working directory for `uv run` remains `services/backend` via `run.py`.

### 5.2 `frontend`

| Item | Value |
|------|--------|
| Runner | `ubuntu-latest` |
| Node | 22 (match `docker/nginx` Node build stage) |
| Steps | checkout → `npm ci` in `services/frontend` → `npm test -- --run` |

Equivalent to `python run.py frontend-test`.

## 6. Branch protection (merge gate)

Workflow status checks alone do not disable Merge. After the workflow lands on the default branch:

1. GitHub → Settings → Branches → Branch protection rule for `main` (and `platform` if used).  
2. Enable **Require status checks to pass before merging**.  
3. Require checks named exactly: `backend`, `frontend` (job `name:` fields in the workflow).  
4. Enable **Require a pull request before merging** (no direct push to `main` preferred).  
5. Do **not** require admin bypass for normal contributors; keep “Do not allow bypassing” if the org supports it.

Optional: apply the same rule via `gh api` once the user confirms admin access.

**Note:** Status check names only appear in the branch protection UI after the workflow has run at least once on a PR (or after the workflow file exists on the default branch and a PR is opened). First merge of the workflow itself may need a temporary admin merge or a bootstrap PR.

## 7. Secrets

None required for this workflow. Do not put production `DJANGO_SECRET_KEY` or Gemini keys in Actions for PR checks.

## 8. Failure behavior

- Any failing step fails the job → red check → merge blocked when protection is on.  
- Flaky Redis/DB startup: rely on service healthchecks; no custom retry loops unless CI proves flaky.

## 9. Docs touchpoints

- Short note in `AGENTS.md` under Commands: “PR CI runs backend-check, pytest, and frontend Vitest via `.github/workflows/pr-checks.yml`.”  
- This spec is the source of truth for scope.

## 10. Success criteria

- Opening a PR runs `backend` and `frontend` checks.  
- A deliberately failing test on a PR shows a red check and (with protection enabled) blocks merge.  
- Green PR can merge once branch protection requires those two checks.
