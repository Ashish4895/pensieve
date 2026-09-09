# PR Checks CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub Actions PR checks (backend + frontend) and document how to require them before merge.

**Architecture:** One workflow file with two parallel jobs using Actions service containers for Postgres/pgvector and Redis. Branch protection is configured in GitHub settings (or via `gh`), not in the workflow YAML.

**Tech Stack:** GitHub Actions, uv, pytest/Django, Node 22, Vitest, pgvector/pg16, Redis 7.

## Global Constraints

- Checks only — no deploy jobs.
- Triggers: `pull_request` to `main` and `platform`.
- Job names must be exactly `backend` and `frontend` (branch protection).
- No CI secrets; empty `GEMINI_API_KEY`; dummy `DJANGO_SECRET_KEY`.
- Prefer `python run.py …` from repo root so local and CI stay aligned.
- Spec: `docs/superpowers/specs/2026-09-09-pr-checks-ci-design.md`.

---

## File map

| File | Responsibility |
|------|----------------|
| `.github/workflows/pr-checks.yml` | PR CI workflow (create) |
| `AGENTS.md` | One-line note that PR CI exists (modify) |
| `docs/superpowers/specs/2026-09-09-pr-checks-ci-design.md` | Mark status Approved after ship (modify) |

---

### Task 1: Add `pr-checks` workflow

**Files:**
- Create: `.github/workflows/pr-checks.yml`

**Interfaces:**
- Consumes: `run.py` commands `backend-check`, `test`, `frontend-test` equivalents
- Produces: GitHub check runs named `backend` and `frontend`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/pr-checks.yml` with this exact content:

```yaml
name: PR checks

on:
  pull_request:
    branches: [main, platform]

jobs:
  backend:
    name: backend
    runs-on: ubuntu-latest
    services:
      db:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: pensieve
          POSTGRES_USER: pensieve
          POSTGRES_PASSWORD: pensieve
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U pensieve -d pensieve"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 10
    env:
      DATABASE_URL: postgres://pensieve:pensieve@localhost:5432/pensieve
      REDIS_URL: redis://localhost:6379/0
      DJANGO_SECRET_KEY: ci-not-a-secret
      DEBUG: "true"
      ALLOWED_HOSTS: localhost,127.0.0.1
      GEMINI_API_KEY: ""
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          working-directory: services/backend
      - name: Django check
        run: python run.py backend-check
      - name: Pytest
        run: python run.py test -- --create-db

  frontend:
    name: frontend
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: services/frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: services/frontend/package-lock.json
      - name: Install
        run: npm ci
      - name: Vitest
        run: npm test -- --run
```

Note: `python run.py test -- --create-db` — verify `run.py` forwards args after the command. If pytest-django rejects `--create-db`, use `python run.py test` only (pytest-django creates DB via `@pytest.mark.django_db` when migrations are applied). Prefer matching `AGENTS.md`:

```bash
DATABASE_URL=… python run.py test --create-db
```

If `run.py` uses `argparse.REMAINDER`, `--create-db` may need to be `python run.py test --create-db` without the extra `--`. Check `run.py` and use the form that actually reaches pytest.

- [ ] **Step 2: Sanity-check arg forwarding locally**

```bash
cd /Users/ashishsingh/Project/pensieve
python -c "import run; print('ok')"
# Confirm how args are passed:
grep -n REMAINDER run.py
```

Adjust the Pytest step to the working invocation (no double `--` if REMAINDER already strips correctly).

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/pr-checks.yml
git commit -m "ci: add PR checks for backend and frontend"
```

---

### Task 2: Document CI in AGENTS.md and mark spec approved

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-09-09-pr-checks-ci-design.md` (Status line)

**Interfaces:**
- Consumes: workflow job names from Task 1
- Produces: operator-facing docs for branch protection

- [ ] **Step 1: Add a short CI note under Commands in `AGENTS.md`**

After the frontend-build bullet, add:

```markdown
- PR CI: `.github/workflows/pr-checks.yml` runs `backend-check`, pytest (Postgres + Redis services), and Vitest on every pull request to `main`/`platform`. Require status checks `backend` and `frontend` in branch protection to block merge until green.
```

- [ ] **Step 2: Update spec status**

Change header Status to: `Approved — implemented`

- [ ] **Step 3: Commit**

```bash
git add AGENTS.md docs/superpowers/specs/2026-09-09-pr-checks-ci-design.md
git commit -m "docs: note PR CI and mark checks design approved"
```

---

### Task 3: Enable branch protection (manual / gh)

**Files:** none (GitHub settings)

- [ ] **Step 1: Push commits to `origin/main`** (user or agent with approval)

```bash
git push origin main
```

- [ ] **Step 2: Open a throwaway PR (or use the CI PR) so check names register**

After at least one workflow run, configure protection.

- [ ] **Step 3: Apply branch protection via UI or `gh`**

UI: Settings → Branches → Add rule for `main` → Require a pull request → Require status checks → select `backend`, `frontend`.

Or (admin token required):

```bash
gh api repos/Ashish4895/pensieve/branches/main/protection \
  --method PUT \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["backend", "frontend"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
```

If the API shape fails (GitHub API versions differ), fall back to the UI. Repeat for `platform` only if that branch remains in use.

- [ ] **Step 4: Verify**

Open a PR with a deliberate failing assertion → merge button disabled / checks red. Revert → green → mergeable.

---

## Spec coverage

| Spec section | Task |
|--------------|------|
| §4 Trigger | Task 1 |
| §5.1 backend job | Task 1 |
| §5.2 frontend job | Task 1 |
| §6 Branch protection | Task 3 |
| §7 No secrets | Task 1 env |
| §9 AGENTS.md | Task 2 |
| Success criteria | Task 3 verify |

## Placeholder scan

None.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-09-pr-checks-ci.md`. Two execution options:

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute in this session with executing-plans  

Which approach?
