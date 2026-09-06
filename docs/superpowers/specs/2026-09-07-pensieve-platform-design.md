# Pensieve Platform Design

**Date:** 2026-09-07  
**Status:** Approved — Plan 1 complete; Plan 2 complete (slices 3–5)
**Approach:** Full architecture (brief C), delivered in ordered slices  
**Product name:** Pensieve

## 1. Context

Pensieve is a multi-tenant document Q&A product. Work already done (BYOK multi-provider chat, Gemini embeddings, Postgres + pgvector RAG, Docker, evals) was **copied** to a new project directory and will be reshaped into a production monorepo. The original tree at `/Users/ashishsingh/Project/gemini-chatbot` remains untouched.

**New project root:** `/Users/ashishsingh/Project/pensieve`  
**Git:** Fresh `git init` on `main` (no commits yet at spec time). History of the copy source is not imported.

This design captures decisions approved in brainstorming §§1–3. Implementation must not begin until this spec is reviewed and an implementation plan is written.

## 2. Goals

- Grow Pensieve into a modular full-stack system: auth, RBAC stubs, versioned APIs, React frontend, Redis/Celery, SSE notifications, WebSocket auth, Docker, developer tooling (`run.py`, `AGENTS.md`), docs/ADRs.
- Preserve existing RAG/chat behavior while migrating it under `/api/v1/` and eventually a React UI.
- Prefer clarity over folder count; abstractions only where they earn their keep (brief items #62 / #66.14 still apply inside a “full C” build).

## 3. Non-goals (for this program)

- Mutating or redeploying the live `gemini-chatbot` / Render Pensieve demo as part of this redesign.
- Finalizing fine-grained role → permission matrices (roles exist; rules decided later).
- Billing, SSO, or multi-region HA in the first implementation plan.

## 4. Product & monorepo (§1)

### 4.1 Structure

```text
pensieve/
├── services/
│   ├── frontend/          # Vite + React + TS + MUI + Redux Toolkit + React Router
│   └── backend/           # Django + DRF + ASGI/Uvicorn + Celery apps
├── env/
│   ├── frontend/          # .env.example and env templates only
│   └── backend/
├── docker/
│   ├── frontend/
│   ├── backend/
│   ├── celery/
│   ├── nginx/
│   └── scripts/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── lessons/
│   ├── api/
│   ├── development/
│   ├── deployment/
│   ├── testing/
│   └── superpowers/       # specs & plans
├── run.py
├── AGENTS.md
├── docker-compose.yml
├── .dockerignore
└── .gitignore
```

### 4.2 Foundation reuse

The copied codebase (Django `pensieve` package, `chatbot` app, `ingest_docs.py`, providers, pgvector models, evals, current Docker/Render files) is the starting point. Reshape into `services/backend/` first; keep chat working during the move. Frontend SPA is net-new under `services/frontend/`; current `chatbot/templates` + static JS remain the v0 reference until React chat ships.

## 5. Auth, roles, API (§2)

### 5.1 Authentication

- JWT **access** token + **refresh** token.
- Secure refresh handling (prefer httpOnly cookie for refresh; access token short-lived for API clients). Exact storage choice locked in the implementation plan’s auth task.
- Endpoints: login, logout, refresh, me.
- **BYOK chat API keys** remain client-held (sessionStorage / headers) as today — they are not account credentials and must never be persisted server-side.

### 5.2 Roles (stubs; rules later)

Custom user model with role:

| Role | Intent |
|------|--------|
| `user` | Default member |
| `admin` | Org/workspace administrator |
| `super_admin` | Platform operator |

DRF permission helpers (`IsAdmin`, `IsSuperAdmin`, `HasRole`, ownership checks) are implemented as reusable classes. **Which endpoints require which role is deferred** until product rules are decided; until then, ship stubs and only enforce what is needed for safe defaults (authenticated for private APIs, super_admin for dangerous platform ops if any).

### 5.3 Tenancy

Minimal org/workspace ownership on resources so multi-tenant data isolation is possible. Invite UX, billing, and seat limits are out of scope for the first plan unless needed for a vertical slice.

### 5.4 API shape

- Prefix: `/api/v1/`.
- Feature routes: `/api/v1/auth/`, `/api/v1/users/`, `/api/v1/chat/` (migrated), `/api/v1/notifications/`, etc.
- Class-based DRF views; thin views → serializers (validation) → services (business logic) → models.
- Standard envelope:

```json
{
  "success": true,
  "message": "Request successful",
  "data": {},
  "errors": null
}
```

Errors use the same shape with `success: false` and populated `errors`.
- OpenAPI/Swagger documents all `/api/v1/` endpoints.
- Existing unversioned chat/history/clear endpoints migrate to v1 without dropping behavior; temporary compatibility shims allowed for one slice if needed.

## 6. Frontend, realtime, infra, DX (§3)

### 6.1 Frontend

- Vite + React + TypeScript + MUI + Redux Toolkit + React Router DOM.
- Feature-based `src/features/{auth,chat,notifications,...}`.
- Shared components, central `src/theme/` (glassmorphism where it aids hierarchy; not on every control).
- Layouts: `AuthLayout`, `MainLayout` (dashboard shell as needed).
- Route-level `React.lazy` + Suspense; protected routes for UX only.
- Redux holds genuinely global client state (auth session meta, notification inbox); server state kept minimal and not duplicated carelessly.

### 6.2 Realtime & background work

- **SSE:** `GET /api/v1/notifications/stream/` — authenticated, user-scoped, heartbeat, reconnect-friendly; notifications persisted in DB (SSE is delivery, not sole source of truth).
- **WebSockets:** ASGI support with JWT auth; reject unauthenticated connections; document auth flow.
- **Celery:** worker + beat + result backend (Redis). Use for document ingest/embeddings and other long jobs. Tasks stay thin and call services. Dev-only `reload_celery` management command; never enable reload in production.

### 6.3 Infrastructure

- Compose services: frontend, backend (Uvicorn), Postgres (pgvector), Redis, Celery worker, Celery beat, nginx.
- Dockerfiles and entrypoints under `docker/`.
- Env templates under `env/`; real secrets never committed.
- Python deps via **uv**; **orjson** for API JSON where beneficial.
- Structured logging + request/correlation ID middleware; never log passwords, JWTs, API keys, or BYOK keys.
- Rate throttling via DRF (+ Redis where appropriate).

### 6.4 Developer experience

- Root `run.py` as the manual operations entrypoint (`setup`, `start`, `test`, docker helpers, etc.), delegating to Django management commands / tools — no business logic in `run.py`.
- `AGENTS.md` documents structure, commands, and conventions; **must stay in sync with `run.py`**.
- Management commands: `setup_application` (idempotent), `start_server`, `reload_celery`.
- Docs evolve with ADRs under `docs/decisions/` for meaningful choices (auth storage, SSE vs WS, tenancy model, etc.).

## 7. Data (high level)

- **Postgres + pgvector:** users, orgs, messages/sessions, document chunks + embeddings, notifications.
- **Redis:** cache, Celery broker/backend, throttle counters as needed.
- Reuse existing `DocumentChunk` vector dimensions (3072) and Gemini embedding pipeline unless a later ADR changes the embedding model.

## 8. Security principles

- Backend authorization is authoritative; frontend RBAC is UX only.
- No hardcoded secrets; rotate any keys that appear in chat or logs.
- CSRF/CORS configured appropriately for cookie-based refresh if chosen.
- Do not weaken auth, throttling, or secret handling for developer convenience in production paths.

## 9. Delivery order

Implementation is **full C**, landed in slices so the repo is never an empty scaffold:

| Slice | Outcome |
|-------|---------|
| 0 | Monorepo reshape of the copy (`services/backend`, env/docker stubs, `run.py`, `AGENTS.md`) |
| 1 | Custom user + roles stubs + JWT auth `/api/v1/auth/` |
| 2 | Core envelope, exceptions, middleware, Swagger |
| 3 | Redis + Celery + ingest task path |
| 4 | Notifications model + SSE + basic panel API |
| 5 | RAG/chat under `/api/v1/` (preserve BYOK) |
| 6 | React app (auth + chat + notifications) |
| 7 | WebSockets auth, nginx, glass theme polish, test/docs/ADR pass |

Each slice should leave the app runnable and include focused tests for new behavior.

## 10. Testing

- Backend: models, serializers, services, auth/refresh, permission stubs, envelope/errors, chat/RAG regression, Celery task unit tests, SSE auth, management command smoke.
- Frontend: critical components, auth slice, protected routes, notification list/SSE client behavior.
- Keep Pensieve eval script adapted to the new backend layout.

## 11. Open decisions (explicit, not TBD blockers)

These are intentionally deferred or to be locked in the implementation plan / ADRs:

1. Refresh token transport: httpOnly cookie vs body storage for SPA.
2. Exact org/workspace schema fields.
3. Role → permission matrix for chat, ingest, user admin.
4. Whether Render remains the first deploy target for the new monorepo or local/docker-only until slice 7.

Defaults if unspecified at plan time: (1) httpOnly refresh cookie + CSRF protection, (2) single `Organization` + membership, (3) authenticated-only for private APIs until matrix exists, (4) docker-compose first; Render later.

## 12. Success criteria

- Developer can `python run.py setup` and `python run.py start` (documented) against compose.
- `/api/v1/` auth and chat work; Swagger lists them.
- React app logs in, chats with BYOK, shows notifications over SSE.
- Celery runs ingest without blocking the web process.
- `AGENTS.md` matches `run.py`; at least one ADR per major subsystem choice above.
- Original `gemini-chatbot` tree unchanged.

## 13. Approval record

| Section | Topic | User decision |
|---------|--------|----------------|
| Approach | Full brief C | Approved |
| §1 | Product Pensieve; copy to `/Users/ashishsingh/Project/pensieve` | Approved (copy option 1) |
| §1 | Roles User/Admin/Super Admin; rules later | Approved |
| §2 | JWT, `/api/v1/`, envelope, BYOK preserved | Approved |
| §3 | React/MUI/Redux, SSE/WS, Celery/Redis, Docker, run.py | Approved |
