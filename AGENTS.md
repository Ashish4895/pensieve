# Pensieve Agent Guide

## Repository layout

- `services/backend/` — Django backend and Python environment
- `env/backend/.env.example` — backend environment template
- `run.py` — root developer command dispatcher

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

Set both `PENSIVE_BOOTSTRAP_EMAIL` and `PENSIVE_BOOTSTRAP_PASSWORD` to create or
update the bootstrap super admin during setup.

Arguments after a command are passed through to the backend tool.

The Compose stack uses Postgres on `5434`, Redis on `6380`, and the backend on
`8001`. It also includes `celery-worker` and `celery-beat` services for
background tasks and scheduled jobs. Start a clean test database with:

```bash
docker compose up -d db
DATABASE_URL=postgres://pensieve:pensieve@127.0.0.1:5434/pensieve \
  python run.py test --create-db
```

## Conventions

- Manage Python dependencies with uv in `services/backend/`.
- Keep business logic out of `run.py`; it only delegates commands.
- Copy `env/backend/.env.example` to a local `.env`; never commit `.env`.
- BYOK chat API keys must never be persisted to the database, logs, or disk.
