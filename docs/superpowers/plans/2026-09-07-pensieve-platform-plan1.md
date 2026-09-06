# Pensieve Platform Plan 1 — Monorepo, Auth, Core API

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reshape the copied Pensieve codebase into a monorepo backend under `services/backend/`, add JWT auth with User/Admin/Super Admin role stubs, and ship `/api/v1/` with a standard response envelope + OpenAPI — without breaking existing chat/RAG.

**Architecture:** Keep Django project package name `pensieve` inside `services/backend/`. Add apps `core`, `accounts`, keep `chatbot`. Refresh tokens use httpOnly cookies; access tokens in JSON. BYOK keys stay client-only.

**Tech Stack:** Django 6.1, DRF, simplejwt, drf-spectacular, Postgres+pgvector, pytest-django, uv, docker compose.

**Spec:** `docs/superpowers/specs/2026-09-07-pensieve-platform-design.md`
**Out of scope:** React, Celery, SSE/WS, nginx, chat `/api/v1/` migration (Plans 2–3).

## Global Constraints

- Project root: `/Users/ashishsingh/Project/pensieve`
- Do not modify `/Users/ashishsingh/Project/gemini-chatbot`
- Roles: `user` | `admin` | `super_admin` (matrix deferred; IsAuthenticated on private v1 APIs)
- API envelope: `{ "success", "message", "data", "errors" }`
- Never persist BYOK provider API keys server-side
- Prefer deletion/reuse over new abstractions
- Python deps via **uv** after Task 2
- Commits: frequent, conventional (`feat:`, `fix:`, `chore:`)

## Follow-on plans

| Plan | Focus |
|------|--------|
| Plan 2 | Celery/ingest, SSE, chat `/api/v1/` |
| Plan 3 | React/MUI/Redux, WS, nginx |

---

### Task 1: Baseline commit of the copy

**Files:**
- Modify: `.gitignore` (ensure `.env` ignored)

**Interfaces:**
- Consumes: copied tree at repo root
- Produces: first git commit on branch `feat/platform-plan1`

- [ ] **Step 1: Verify copy and ignore secrets**

```bash
cd /Users/ashishsingh/Project/pensieve
test -f manage.py && test -f docs/superpowers/specs/2026-09-07-pensieve-platform-design.md
grep -E '^\.env$' .gitignore || echo '.env' >> .gitignore
git checkout -b feat/platform-plan1
```

- [ ] **Step 2: Commit baseline**

```bash
git add -A
git status   # confirm .env is NOT staged
git commit -m "$(cat <<'EOF'
chore: import Pensieve baseline from gemini-chatbot copy

EOF
)"
```

---

### Task 2: Move backend into `services/backend/`

**Files:** Move `manage.py`, `pensieve/`, `chatbot/`, `ingest_docs.py`, `evals/`, `documents/`, `pytest.ini`, `requirements.txt`, `bot.py` → `services/backend/`

- [ ] **Step 1:** `mkdir -p services/backend && git mv manage.py pensieve chatbot ingest_docs.py evals documents pytest.ini requirements.txt bot.py services/backend/`
- [ ] **Step 2:** venv + `pip install -r requirements.txt` + `python manage.py check`
- [ ] **Step 3:** pytest.ini with `DJANGO_SETTINGS_MODULE = pensieve.settings`; `pytest chatbot/tests/test_providers.py -q`
- [ ] **Step 4:** Commit `chore: move Django app under services/backend`

---

### Task 3: uv + root `run.py` + `AGENTS.md`

**Files:** Create `services/backend/pyproject.toml`, `run.py`, `AGENTS.md`, `env/backend/.env.example`

**Interfaces:** `python run.py` → `help|backend-check|test|migrate|setup`

- [ ] **Step 1:** pyproject with Django 6.1.1, DRF, simplejwt, drf-spectacular, cors, RAG deps, uvicorn, orjson; dev pytest
- [ ] **Step 2:** `uv sync && uv run python manage.py check`
- [ ] **Step 3:** `run.py` delegates to uv in `services/backend` — no business logic
- [ ] **Step 4:** `AGENTS.md` lists same commands; no gemini-chatbot edits; BYOK never stored
- [ ] **Step 5:** env example DATABASE_URL port 5433
- [ ] **Step 6:** Commit `chore: add uv, run.py, and AGENTS.md for backend DX`

---

### Task 4: Compose Postgres + Redis + backend Docker

**Files:** `docker-compose.yml`, `docker/backend/Dockerfile`, `docker/scripts/backend-entrypoint.sh`

- [ ] **Step 1:** pgvector pg16 host 5433, redis 6379, backend service
- [ ] **Step 2:** entrypoint migrate + collectstatic + uvicorn
- [ ] **Step 3:** `docker compose up -d db redis` (or note if Docker unavailable)
- [ ] **Step 4:** Commit `chore: add compose Postgres/Redis and backend Docker layout`

---

### Task 5: Custom User + Organization stubs

**Interfaces:** `User.role` ∈ `user|admin|super_admin`; Organization; Membership; `AUTH_USER_MODEL`

- [ ] **Step 1:** Failing test `accounts/tests/test_models.py` default role user
- [ ] **Step 2:** Run expect FAIL
- [ ] **Step 3:** Implement email User + roles + Org/Membership; fresh Postgres DB; migrate
- [ ] **Step 4:** Pass + commit `feat: add accounts.User roles and Organization stubs`

---

### Task 6: API envelope + exception handler

**Interfaces:** `api_success`, `api_error`, `custom_exception_handler`

- [ ] **Step 1:** Failing shape tests for `{success,message,data,errors}`
- [ ] **Step 2:** Implement + wire EXCEPTION_HANDLER
- [ ] **Step 3:** Pass + commit `feat: add standard API success/error envelope`

---

### Task 7: JWT auth `/api/v1/auth/`

**Interfaces:** register/login/refresh/logout/me; cookie `refresh`; body `access`; keep chatbot urls; Swagger `/api/docs/`

- [ ] **Step 1:** Failing APIClient test
- [ ] **Step 2:** AuthService + views + urls + SIMPLE_JWT
- [ ] **Step 3:** Pass + commit `feat: add JWT auth under /api/v1/auth`

---

### Task 8: RBAC stubs + request ID middleware

**Interfaces:** `IsAdmin`, `IsSuperAdmin`, `HasRole`; header `X-Request-ID` — do not wire to chat yet

- [ ] **Step 1:** Failing permission unit test
- [ ] **Step 2:** Implement middleware + permissions
- [ ] **Step 3:** Commit `feat: add RBAC permission stubs and request ID middleware`

---

### Task 9: `setup_application` + Swagger smoke

- [ ] **Step 1:** Idempotent migrate + optional `PENSIVE_BOOTSTRAP_EMAIL`/`PASSWORD`
- [ ] **Step 2:** `python run.py setup`; curl `/api/docs/` → 200
- [ ] **Step 3:** Commit `feat: add setup_application management command`

---

### Task 10: ADRs + regression

- [ ] **Step 1:** `docs/decisions/001-jwt-refresh-cookie.md`, `002-django-package-name-pensieve.md`
- [ ] **Step 2:** `python run.py test`
- [ ] **Step 3:** Commit `docs: add Plan 1 ADRs`

---

## Plan 1 self-review

Slices 0–2 covered. Roles/cookie/envelope names consistent. No TBD placeholders.
