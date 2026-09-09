# Pensieve Agent Guide

## Repository layout

- `services/backend/` — Django backend and Python environment (uv)
- `services/frontend/` — Vite + React + TypeScript SPA
- `env/backend/.env.example`, `env/frontend/.env.example` — env templates
- `run.py` — root developer command dispatcher
- `docker/` — backend, celery, nginx images

Do not edit the separate `gemini-chatbot` project while working in this repository.

## Commands

Run these from the repository root:

- `python run.py` or `python run.py help` — list commands
- `python run.py backend-check` — run Django system checks
- `python run.py test` — run the backend test suite
- `python run.py migrate` — apply database migrations
- `python run.py setup` — apply migrations and optionally bootstrap a super admin
- `python run.py start` — start the ASGI server (uvicorn on `PORT`, default 8000)
- `python run.py celery-worker` — run the Celery worker locally
- `python run.py frontend-dev` — Vite SPA on `http://127.0.0.1:5173`
- `python run.py frontend-test` — Vitest
- `python run.py frontend-build` — production SPA build
- PR CI: `.github/workflows/pr-checks.yml` runs `backend-check`, pytest (Postgres + Redis services), and Vitest on every pull request to `main`/`platform`. Require status checks `backend` and `frontend` in branch protection to block merge until green.

Set both `PENSIVE_BOOTSTRAP_EMAIL` and `PENSIVE_BOOTSTRAP_PASSWORD` to create or
update the bootstrap super admin during setup.

## Ports (Compose project `pensieve-platform`)

| Service | Host port |
|---------|-----------|
| Postgres | 5434 |
| Redis | 6380 |
| Backend (direct) | 8001 |
| Vite (dev) | 5173 |
| nginx (SPA + API + WS) | 8080 |

```bash
docker compose up -d db redis
DATABASE_URL=postgres://pensieve:pensieve@127.0.0.1:5434/pensieve \
  python run.py test --create-db
```

Edge stack (when Docker is available): `docker compose up --build nginx` (builds SPA into nginx).

## Auth / BYOK / realtime

- Access JWT lives in Redux memory only; refresh stays httpOnly cookie `refresh`.
- BYOK keys live in `sessionStorage` only (`byok_*`); never Redux, DB, or logs.
- SSE: `EventSource` uses `?access=<jwt>` because it cannot set Authorization.
- WebSocket: `ws/v1/chat/?token=<jwt>`; unauthenticated connections close with 4401.

## Conventions

- Manage Python deps with uv in `services/backend/`; frontend with npm in `services/frontend/`.
- Keep business logic out of `run.py`; it only delegates commands.
- Copy env examples to local `.env`; never commit secrets.
- Frontend RBAC is UX only; backend authorization is authoritative.
