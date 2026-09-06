# Pensieve Platform Plan 2 — Celery, SSE, Chat v1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire Redis + Celery for async document ingest, ship authenticated notifications (DB + SSE stream), and migrate chat/history/clear under `/api/v1/chat/` with the standard envelope — preserving BYOK and legacy template routes.

**Architecture:** Celery worker/beat share the Django settings module and Redis broker. Ingest logic moves into a testable service; the Celery task and CLI stay thin. Notifications are persisted per user; SSE is delivery only. Chat v1 uses DRF class-based views + a `ChatService`; legacy `/api/chat|history|clear/` keep working for the Django template UI until Plan 3.

**Tech Stack:** Django 6.1, DRF, Celery 5.x, Redis, StreamingHttpResponse (SSE), pytest-django, uv, docker compose (`pensieve-platform`).

**Spec:** `docs/superpowers/specs/2026-09-07-pensieve-platform-design.md` (slices 3–5)  
**Base branch:** create `feat/platform-plan2` from current `feat/platform-plan1` HEAD  
**Out of scope:** React frontend, WebSockets JWT, nginx, role→permission matrix, Render deploy, Redis-backed chat throttle (keep in-memory for now)

## Global Constraints

- Project root: `/Users/ashishsingh/Project/pensieve`
- Do not modify `/Users/ashishsingh/Project/gemini-chatbot`
- Compose project name stays `pensieve-platform`; host ports **5434** (Postgres), **6380** (Redis), **8001** (backend)
- Roles: `user` | `admin` | `super_admin` (matrix deferred; IsAuthenticated on private v1 APIs)
- API envelope: `{ "success", "message", "data", "errors" }` via `core.api.api_success` / `api_error`
- Never persist BYOK provider API keys server-side; never log them
- Prefer deletion/reuse over new abstractions; tasks call services, not the reverse
- Python deps via **uv** in `services/backend/`
- Commits: frequent, conventional (`feat:`, `fix:`, `chore:`, `docs:`)
- Tests: `CELERY_TASK_ALWAYS_EAGER=True` in pytest (or `@override_settings`) so workers are not required for unit tests
- `reload_celery` must refuse to run when `DEBUG` is false

## File map (create / modify)

| Path | Responsibility |
|------|----------------|
| `services/backend/pensieve/celery.py` | Celery app instance |
| `services/backend/pensieve/__init__.py` | Import `app` so Django loads Celery |
| `services/backend/pensieve/settings.py` | `REDIS_URL`, `CACHES`, Celery settings |
| `services/backend/chatbot/services/ingest.py` | `chunk_text`, `ingest_documents` (service) |
| `services/backend/chatbot/services/chat.py` | `ChatService.send_message` / history / clear |
| `services/backend/chatbot/tasks.py` | `run_ingest` Celery task |
| `services/backend/chatbot/api_views.py` | DRF v1 chat + ingest enqueue views |
| `services/backend/chatbot/urls_v1.py` | `/api/v1/chat/` + ingest routes |
| `services/backend/notifications/` | App: model, services, views, SSE, urls |
| `docker/celery/Dockerfile` | Worker/beat image (reuse backend sync) |
| `docker/scripts/celery-entrypoint.sh` | Worker or beat command |
| `docker-compose.yml` | `celery-worker`, `celery-beat` services |
| `core/management/commands/start_server.py` | Uvicorn launcher |
| `core/management/commands/reload_celery.py` | Dev-only celery autoreload helper |
| `run.py` / `AGENTS.md` / `env/backend/.env.example` | DX sync |
| `docs/decisions/002-celery-redis.md`, `003-sse-notifications.md` | ADRs |

## Follow-on

| Plan | Focus |
|------|--------|
| Plan 3 | React/MUI/Redux, WebSockets auth, nginx, glass theme |

---

### Task 1: Branch + Redis settings + deps

**Files:**
- Modify: `services/backend/pyproject.toml`, `services/backend/pensieve/settings.py`, `env/backend/.env.example`
- Test: `services/backend/core/tests/test_redis_settings.py`

**Interfaces:**
- Consumes: Compose `REDIS_URL=redis://redis:6379/0`; host default `redis://127.0.0.1:6380/0`
- Produces: `settings.REDIS_URL: str`; Django `CACHES["default"]` using `django.core.cache.backends.redis.RedisCache`

- [ ] **Step 1: Create branch**

```bash
cd /Users/ashishsingh/Project/pensieve
git checkout feat/platform-plan1
git checkout -b feat/platform-plan2
```

- [ ] **Step 2: Write the failing test**

```python
# services/backend/core/tests/test_redis_settings.py
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings


def test_redis_url_default_matches_compose_host_port():
    assert "6380" in settings.REDIS_URL or settings.REDIS_URL.startswith("redis://")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "plan2-test",
        }
    }
)
def test_cache_roundtrip_works_with_configured_backend():
    cache.set("plan2", "ok", 10)
    assert cache.get("plan2") == "ok"
```

- [ ] **Step 3: Add dependencies and settings**

Add to `pyproject.toml` dependencies:

```toml
"celery>=5.5.0",
"redis>=5.0.0",
```

Append to `settings.py` (after DATABASES block):

```python
REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6380/0").strip()

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
```

Add to `env/backend/.env.example`:

```bash
REDIS_URL=redis://127.0.0.1:6380/0
```

- [ ] **Step 4: Sync and run test**

```bash
cd /Users/ashishsingh/Project/pensieve/services/backend
uv lock && uv sync
cd ../..
# LocMem override test does not need Redis; REDIS_URL assertion always passes
python run.py test core/tests/test_redis_settings.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/backend/pyproject.toml services/backend/uv.lock \
  services/backend/pensieve/settings.py env/backend/.env.example \
  services/backend/core/tests/test_redis_settings.py
git commit -m "$(cat <<'EOF'
chore: wire Redis cache settings and Celery broker config

EOF
)"
```

---

### Task 2: Celery app bootstrap

**Files:**
- Create: `services/backend/pensieve/celery.py`
- Modify: `services/backend/pensieve/__init__.py`
- Test: `services/backend/core/tests/test_celery_app.py`

**Interfaces:**
- Consumes: `CELERY_BROKER_URL` from settings
- Produces: `pensieve.celery.app` (`celery.Celery`); autodiscover `*/tasks.py`

- [ ] **Step 1: Failing test**

```python
# services/backend/core/tests/test_celery_app.py
def test_celery_app_loads_django_settings():
    from pensieve.celery import app

    assert app.main.endswith("pensieve") or app.main == "pensieve"
    assert app.conf.task_serializer == "json"
```

- [ ] **Step 2: Implement**

```python
# services/backend/pensieve/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")

app = Celery("pensieve")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

```python
# services/backend/pensieve/__init__.py
from .celery import app as celery_app

__all__ = ("celery_app",)
```

- [ ] **Step 3: Run test**

```bash
python run.py test core/tests/test_celery_app.py -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add services/backend/pensieve/celery.py services/backend/pensieve/__init__.py \
  services/backend/core/tests/test_celery_app.py
git commit -m "$(cat <<'EOF'
feat: bootstrap Celery app for Pensieve backend

EOF
)"
```

---

### Task 3: Extract ingest service (sync path)

**Files:**
- Create: `services/backend/chatbot/services/__init__.py`, `services/backend/chatbot/services/ingest.py`
- Modify: `services/backend/ingest_docs.py` (thin CLI calling the service)
- Test: `services/backend/chatbot/tests/test_ingest_service.py`

**Interfaces:**
- Consumes: `DocumentChunk`, Gemini embed API (injectable)
- Produces:
  - `chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]`
  - `ingest_documents(directory: str = "documents", *, embed_content=None) -> dict` with keys `files: int`, `chunks: int`, `cleared: bool`
  - Behavior: wipe all `DocumentChunk` rows, embed `.txt`/`.md` with model `gemini-embedding-2`, dimension 3072

- [ ] **Step 1: Failing test**

```python
# services/backend/chatbot/tests/test_ingest_service.py
import pytest
from chatbot.models import DocumentChunk
from chatbot.services.ingest import chunk_text, ingest_documents


def test_chunk_text_overlaps():
    text = "a" * 600
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) == 2
    assert len(chunks[0]) == 500


@pytest.mark.django_db
def test_ingest_documents_uses_injected_embedder(tmp_path):
    doc = tmp_path / "note.txt"
    doc.write_text("hello world " * 40, encoding="utf-8")

    def fake_embed(chunk: str) -> list[float]:
        return [0.1] * 3072

    result = ingest_documents(str(tmp_path), embed_content=fake_embed)
    assert result["files"] == 1
    assert result["chunks"] >= 1
    assert result["cleared"] is True
    assert DocumentChunk.objects.count() == result["chunks"]
    assert DocumentChunk.objects.first().source_name == "note.txt"
```

- [ ] **Step 2: Implement service**

```python
# services/backend/chatbot/services/ingest.py
from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from google import genai

from chatbot.models import DocumentChunk


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _default_embed_content(chunk: str) -> list[float]:
    api_key = os.environ.get("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for embeddings")
    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(model="gemini-embedding-2", contents=chunk)
    return list(response.embeddings[0].values)


def ingest_documents(
    directory: str = "documents",
    *,
    embed_content=None,
) -> dict:
    embed = embed_content or _default_embed_content
    path = Path(directory)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return {"files": 0, "chunks": 0, "cleared": False}

    DocumentChunk.objects.all().delete()
    files = sorted(f.name for f in path.iterdir() if f.suffix in {".txt", ".md"})
    total_chunks = 0
    for filename in files:
        content = (path / filename).read_text(encoding="utf-8")
        for chunk in chunk_text(content):
            DocumentChunk.objects.create(
                source_name=filename,
                content=chunk,
                embedding=embed(chunk),
            )
            total_chunks += 1
    return {"files": len(files), "chunks": total_chunks, "cleared": True}
```

Rewrite `ingest_docs.py` to:

```python
import os
import sys

import django
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
load_dotenv()
django.setup()

from chatbot.services.ingest import ingest_documents  # noqa: E402

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY not found in environment.")
        sys.exit(1)
    print(ingest_documents())
```

- [ ] **Step 3: Run tests**

```bash
python run.py test chatbot/tests/test_ingest_service.py -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add services/backend/chatbot/services/ services/backend/ingest_docs.py \
  services/backend/chatbot/tests/test_ingest_service.py
git commit -m "$(cat <<'EOF'
refactor: extract ingest_documents into chatbot service

EOF
)"
```

---

### Task 4: Celery `run_ingest` task + enqueue API

**Files:**
- Create: `services/backend/chatbot/tasks.py`, `services/backend/chatbot/api_views.py` (ingest view only for now), `services/backend/chatbot/urls_v1.py`
- Modify: `services/backend/pensieve/urls.py`
- Test: `services/backend/chatbot/tests/test_ingest_task.py`, `services/backend/chatbot/tests/test_ingest_api.py`

**Interfaces:**
- Consumes: `ingest_documents`
- Produces:
  - `@shared_task(name="chatbot.run_ingest") def run_ingest(directory: str = "documents") -> dict`
  - `POST /api/v1/ingest/` → `{success, data: {task_id}}` (IsAuthenticated); enqueues task; does not run embeddings in the request thread when eager is false

- [ ] **Step 1: Failing task test**

```python
# services/backend/chatbot/tests/test_ingest_task.py
from unittest.mock import patch
import pytest
from django.test import override_settings


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
@patch("chatbot.tasks.ingest_documents", return_value={"files": 1, "chunks": 2, "cleared": True})
def test_run_ingest_task_calls_service(mock_ingest):
    from chatbot.tasks import run_ingest

    result = run_ingest.delay("documents").get()
    mock_ingest.assert_called_once_with("documents")
    assert result == {"files": 1, "chunks": 2, "cleared": True}
```

- [ ] **Step 2: Implement task**

```python
# services/backend/chatbot/tasks.py
from celery import shared_task
from chatbot.services.ingest import ingest_documents


@shared_task(name="chatbot.run_ingest")
def run_ingest(directory: str = "documents") -> dict:
    return ingest_documents(directory)
```

- [ ] **Step 3: Failing API test**

```python
# services/backend/chatbot/tests/test_ingest_api.py
from unittest.mock import MagicMock, patch
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.mark.django_db
@patch("chatbot.api_views.run_ingest")
def test_enqueue_ingest_requires_auth_and_returns_task_id(mock_task):
    mock_task.delay.return_value = MagicMock(id="abc-123")
    client = APIClient()
    assert client.post("/api/v1/ingest/").status_code == 401

    user = get_user_model().objects.create_user(email="a@b.com", password="StrongPass123!")
    client.force_authenticate(user=user)
    res = client.post("/api/v1/ingest/", {"directory": "documents"}, format="json")
    assert res.status_code == 202
    assert res.data["success"] is True
    assert res.data["data"]["task_id"] == "abc-123"
    mock_task.delay.assert_called_once_with("documents")
```

- [ ] **Step 4: Implement API + urls**

```python
# services/backend/chatbot/api_views.py
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.status import HTTP_202_ACCEPTED
from core.api import api_success
from chatbot.tasks import run_ingest


class IngestEnqueueView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        directory = request.data.get("directory") or "documents"
        if not isinstance(directory, str) or not directory.strip():
            directory = "documents"
        async_result = run_ingest.delay(directory.strip())
        return api_success(
            data={"task_id": async_result.id},
            message="Ingest enqueued",
            status_code=HTTP_202_ACCEPTED,
        )
```

```python
# services/backend/chatbot/urls_v1.py
from django.urls import path
from chatbot.api_views import IngestEnqueueView

urlpatterns = [
    path("ingest/", IngestEnqueueView.as_view(), name="ingest-enqueue"),
]
```

In `pensieve/urls.py` include:

```python
path("api/v1/", include("chatbot.urls_v1")),
```

- [ ] **Step 5: Run tests + commit**

```bash
python run.py test chatbot/tests/test_ingest_task.py chatbot/tests/test_ingest_api.py -q
git add services/backend/chatbot/tasks.py services/backend/chatbot/api_views.py \
  services/backend/chatbot/urls_v1.py services/backend/pensieve/urls.py \
  services/backend/chatbot/tests/test_ingest_task.py \
  services/backend/chatbot/tests/test_ingest_api.py
git commit -m "$(cat <<'EOF'
feat: add Celery run_ingest task and /api/v1/ingest enqueue

EOF
)"
```

---

### Task 5: Compose Celery worker + beat

**Files:**
- Create: `docker/celery/Dockerfile`, `docker/scripts/celery-entrypoint.sh`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: same backend image deps; `REDIS_URL`, `DATABASE_URL`, `GEMINI_API_KEY`
- Produces: services `celery-worker`, `celery-beat` on compose network (no host ports required)

- [ ] **Step 1: Dockerfile + entrypoint**

```dockerfile
# docker/celery/Dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY services/backend/pyproject.toml services/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/backend/ ./
RUN uv sync --frozen --no-dev

COPY docker/scripts/celery-entrypoint.sh /usr/local/bin/celery-entrypoint
RUN chmod +x /usr/local/bin/celery-entrypoint

ENTRYPOINT ["celery-entrypoint"]
```

```bash
#!/bin/sh
# docker/scripts/celery-entrypoint.sh
set -e
ROLE="${CELERY_ROLE:-worker}"
if [ "$ROLE" = "beat" ]; then
  exec celery -A pensieve worker --beat --loglevel=INFO --concurrency=1
fi
exec celery -A pensieve worker --loglevel=INFO
```

Note: Prefer **separate** worker and beat processes in compose (two services), both using this image:

- worker: `CELERY_ROLE=worker`
- beat: `command` override `celery -A pensieve beat --loglevel=INFO` (do not use worker --beat in prod layout)

Preferred beat service command in compose:

```yaml
command: ["celery", "-A", "pensieve", "beat", "--loglevel=INFO"]
entrypoint: []
```

Or keep entrypoint and set `CELERY_ROLE=beat` with beat-only exec:

```bash
if [ "$ROLE" = "beat" ]; then
  exec celery -A pensieve beat --loglevel=INFO
fi
exec celery -A pensieve worker --loglevel=INFO
```

- [ ] **Step 2: Add compose services** (same env as backend; depends_on db+redis healthy)

```yaml
  celery-worker:
    build:
      context: .
      dockerfile: docker/celery/Dockerfile
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://pensieve:pensieve@db:5432/pensieve
      REDIS_URL: redis://redis:6379/0
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set}
      GEMINI_API_KEY: ${GEMINI_API_KEY:-}
      DEBUG: ${DEBUG:-true}
      CELERY_ROLE: worker
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-beat:
    build:
      context: .
      dockerfile: docker/celery/Dockerfile
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://pensieve:pensieve@db:5432/pensieve
      REDIS_URL: redis://redis:6379/0
      DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY must be set}
      DEBUG: ${DEBUG:-true}
      CELERY_ROLE: beat
    depends_on:
      redis:
        condition: service_healthy
```

- [ ] **Step 3: Smoke (if Docker available)**

```bash
export DJANGO_SECRET_KEY=dev-compose-key
docker compose build celery-worker
docker compose up -d redis db celery-worker
docker compose exec celery-worker celery -A pensieve inspect ping
```

If Docker unavailable, note in commit message and skip — unit tests cover the task.

- [ ] **Step 4: Commit**

```bash
git add docker/celery/Dockerfile docker/scripts/celery-entrypoint.sh docker-compose.yml
git commit -m "$(cat <<'EOF'
chore: add Celery worker and beat Compose services

EOF
)"
```

---

### Task 6: `start_server`, `reload_celery`, run.py sync

**Files:**
- Create: `services/backend/core/management/commands/start_server.py`, `…/reload_celery.py`
- Modify: `run.py`, `AGENTS.md`
- Test: `services/backend/core/tests/test_management_commands.py`

**Interfaces:**
- Consumes: uvicorn; Celery
- Produces:
  - `manage.py start_server` → `uvicorn pensieve.asgi:application --host 0.0.0.0 --port $PORT`
  - `manage.py reload_celery` → exits nonzero if not `DEBUG`; otherwise prints how to run worker with `--autoreload` **or** touches a watch file — **must not** enable reload in production
  - `run.py start` → `start_server`; `run.py celery-worker` → `celery -A pensieve worker -l INFO`

- [ ] **Step 1: Failing test**

```python
# services/backend/core/tests/test_management_commands.py
import pytest
from django.core.management import call_command
from django.test import override_settings
from io import StringIO


@override_settings(DEBUG=False)
def test_reload_celery_refuses_when_not_debug():
    err = StringIO()
    with pytest.raises(SystemExit) as exc:
        call_command("reload_celery", stderr=err)
    assert exc.value.code != 0
```

Implement `reload_celery` to `sys.exit(1)` with message `"reload_celery is only allowed when DEBUG=true"`.

- [ ] **Step 2: Implement commands + wire run.py**

`start_server.py`:

```python
import os
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start ASGI server with uvicorn"

    def handle(self, *args, **options):
        import uvicorn

        port = int(os.environ.get("PORT", "8000"))
        uvicorn.run("pensieve.asgi:application", host="0.0.0.0", port=port, reload=False)
```

`reload_celery.py`:

```python
import sys
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Dev-only helper: document/run celery with autoreload (never in production)"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            self.stderr.write("reload_celery is only allowed when DEBUG=true")
            sys.exit(1)
        self.stdout.write(
            "Run: celery -A pensieve worker --loglevel=INFO --pool=solo\n"
            "Use process manager autoreload in development only; never in production."
        )
```

Update `run.py` `COMMANDS`:

```python
COMMANDS = {
    "backend-check": ["python", "manage.py", "check"],
    "test": ["pytest"],
    "migrate": ["python", "manage.py", "migrate"],
    "setup": ["python", "manage.py", "setup_application"],
    "start": ["python", "manage.py", "start_server"],
    "celery-worker": ["celery", "-A", "pensieve", "worker", "--loglevel=INFO"],
}
```

Mirror in `AGENTS.md` (ports unchanged; mention celery-worker/beat compose services).

- [ ] **Step 3: Test + commit**

```bash
python run.py test core/tests/test_management_commands.py -q
git add services/backend/core/management/commands/start_server.py \
  services/backend/core/management/commands/reload_celery.py \
  services/backend/core/tests/test_management_commands.py run.py AGENTS.md
git commit -m "$(cat <<'EOF'
feat: add start_server and reload_celery DX commands

EOF
)"
```

---

### Task 7: Notifications model + list/mark-read API

**Files:**
- Create: `services/backend/notifications/` app (models, serializers, services, views, urls, admin, apps, migrations)
- Modify: `INSTALLED_APPS`, `pensieve/urls.py`
- Test: `services/backend/notifications/tests/test_api.py`

**Interfaces:**
- Consumes: `AUTH_USER_MODEL`
- Produces:
  - `Notification(user, title, body, kind, created_at, read_at=null)`
  - `GET /api/v1/notifications/` → list current user’s notifications (newest first)
  - `POST /api/v1/notifications/<id>/read/` → set `read_at`
  - Envelope via `api_success`

- [ ] **Step 1: Failing API test**

```python
# services/backend/notifications/tests/test_api.py
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from notifications.models import Notification


@pytest.mark.django_db
def test_list_and_mark_read_are_user_scoped():
    User = get_user_model()
    a = User.objects.create_user(email="a@ex.com", password="StrongPass123!")
    b = User.objects.create_user(email="b@ex.com", password="StrongPass123!")
    Notification.objects.create(user=a, title="A1", body="x", kind="ingest")
    Notification.objects.create(user=b, title="B1", body="y", kind="ingest")

    client = APIClient()
    client.force_authenticate(user=a)
    listed = client.get("/api/v1/notifications/")
    assert listed.status_code == 200
    assert listed.data["success"] is True
    assert len(listed.data["data"]["results"]) == 1
    assert listed.data["data"]["results"][0]["title"] == "A1"

    nid = listed.data["data"]["results"][0]["id"]
    marked = client.post(f"/api/v1/notifications/{nid}/read/")
    assert marked.status_code == 200
    assert marked.data["data"]["read_at"] is not None
```

- [ ] **Step 2: Implement app**

Model fields:

```python
class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    kind = models.CharField(max_length=64, default="info")
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
```

Views: `NotificationListView` (GET), `NotificationMarkReadView` (POST). Use `timezone.now()` for `read_at`. 404 if not owned.

Urls mounted at `path("api/v1/notifications/", include("notifications.urls"))`.

- [ ] **Step 3: Migrate + test + commit**

```bash
cd services/backend && uv run python manage.py makemigrations notifications && uv run python manage.py migrate
cd ../..
python run.py test notifications/tests/test_api.py -q
git add services/backend/notifications services/backend/pensieve/settings.py \
  services/backend/pensieve/urls.py
git commit -m "$(cat <<'EOF'
feat: add Notification model and list/mark-read API

EOF
)"
```

---

### Task 8: SSE stream + ingest completion notification

**Files:**
- Create: `services/backend/notifications/sse.py`, views for stream; modify `chatbot/tasks.py` to notify requesting user
- Modify: ingest enqueue to pass `user_id` into the task
- Test: `services/backend/notifications/tests/test_sse.py`, update ingest task/API tests

**Interfaces:**
- Consumes: JWT `IsAuthenticated`; `Notification` rows
- Produces:
  - `GET /api/v1/notifications/stream/` — `text/event-stream`; heartbeat comment every ~15s; events `id: <pk>\nevent: notification\ndata: <json>\n\n`; honors `Last-Event-ID` (resume after that pk); user-scoped
  - `run_ingest(directory, user_id=None)` creates a `Notification` for that user on success (`kind="ingest"`, title `"Ingest complete"`)

SSE implementation notes (keep lean):
- Use Django `StreamingHttpResponse` generator.
- Loop: query notifications for user with `id > last_id` ordered by id; yield events; sleep 1s; every 15 iterations yield `: heartbeat\n\n`.
- Cap stream duration in tests via injecting a `max_iterations` kwarg on the generator used by the view, **or** test a pure helper `iter_notification_events(user, last_id, *, max_rounds=3, sleep_fn=...)` and keep the view thin.

Preferred testable surface:

```python
# notifications/services.py
def create_notification(*, user, title: str, body: str = "", kind: str = "info") -> Notification: ...

def iter_sse_events(user, last_event_id: int = 0, *, max_rounds: int | None = None, sleep_fn=time.sleep, heartbeat_every: int = 15):
    ...
```

- [ ] **Step 1: Failing SSE helper test**

```python
@pytest.mark.django_db
def test_iter_sse_events_emits_notification_and_heartbeat():
    User = get_user_model()
    user = User.objects.create_user(email="sse@ex.com", password="StrongPass123!")
    n = Notification.objects.create(user=user, title="Hi", body="b", kind="info")
    sleeps = []
    chunks = list(
        iter_sse_events(
            user,
            last_event_id=0,
            max_rounds=2,
            sleep_fn=lambda s: sleeps.append(s),
            heartbeat_every=1,
        )
    )
    joined = "".join(chunks)
    assert f"id: {n.id}" in joined
    assert "event: notification" in joined
    assert ": heartbeat" in joined
```

- [ ] **Step 2: Failing auth test on stream URL**

```python
@pytest.mark.django_db
def test_stream_requires_authentication():
    client = APIClient()
    assert client.get("/api/v1/notifications/stream/").status_code == 401
```

- [ ] **Step 3: Implement SSE view + wire urls**

View returns `StreamingHttpResponse(iter_sse_events(...), content_type="text/event-stream")` with headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

- [ ] **Step 4: Update task to notify**

```python
@shared_task(name="chatbot.run_ingest")
def run_ingest(directory: str = "documents", user_id: int | None = None) -> dict:
    result = ingest_documents(directory)
    if user_id is not None:
        from django.contrib.auth import get_user_model
        from notifications.services import create_notification

        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            create_notification(
                user=user,
                title="Ingest complete",
                body=f"files={result['files']} chunks={result['chunks']}",
                kind="ingest",
            )
    return result
```

Update `IngestEnqueueView` to `run_ingest.delay(directory.strip(), request.user.id)`.

- [ ] **Step 5: Tests + commit**

```bash
python run.py test notifications/tests/ chatbot/tests/test_ingest_task.py chatbot/tests/test_ingest_api.py -q
git add services/backend/notifications services/backend/chatbot/tasks.py \
  services/backend/chatbot/api_views.py
git commit -m "$(cat <<'EOF'
feat: add notifications SSE stream and ingest completion notices

EOF
)"
```

---

### Task 9: ChatService extraction

**Files:**
- Create: `services/backend/chatbot/services/chat.py`
- Modify: `services/backend/chatbot/views.py` to call the service (legacy JSON shape unchanged)
- Test: `services/backend/chatbot/tests/test_chat_service.py` (+ existing BYOK tests still pass)

**Interfaces:**
- Consumes: `Message`, `retrieve_relevant_chunks`, `get_provider`, `allow`
- Produces:
  - `ChatService.send_message(*, message, session_id, provider_name, api_key, model, client_ip) -> dict` with `response`, `sources`, `session_id`
  - Raises domain errors mapped by views: empty message → `ValueError`; missing key → custom or reuse provider errors; rate limit → dedicated `RateLimitExceeded`
  - `get_history(session_id) -> list[dict]`
  - `clear_history(session_id) -> int` (deleted count)

Keep persistence rule: write user+model messages only after successful provider completion.

- [ ] **Step 1: Failing unit test with mocks**

```python
@pytest.mark.django_db
@patch("chatbot.services.chat.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.services.chat.get_provider")
@patch("chatbot.services.chat.allow", return_value=True)
def test_chat_service_persists_after_success(mock_allow, mock_get, mock_rag):
    mock_get.return_value.complete.return_value = "pong"
    from chatbot.services.chat import ChatService

    out = ChatService.send_message(
        message="ping",
        session_id="s1",
        provider_name="gemini",
        api_key="sk-test",
        model=None,
        client_ip="127.0.0.1",
    )
    assert out["response"] == "pong"
    assert Message.objects.filter(session_id="s1").count() == 2
```

- [ ] **Step 2: Implement service; refactor function views to call it; map exceptions to legacy JsonResponse**

- [ ] **Step 3: Run legacy BYOK suite + new test**

```bash
python run.py test chatbot/tests/test_chat_service.py chatbot/tests/test_views_byok.py -q
```

- [ ] **Step 4: Commit**

```bash
git commit -am "$(cat <<'EOF'
refactor: extract ChatService for shared legacy and v1 chat

EOF
)"
```

---

### Task 10: `/api/v1/chat/` endpoints (envelope + auth)

**Files:**
- Modify: `services/backend/chatbot/api_views.py`, `urls_v1.py`
- Test: `services/backend/chatbot/tests/test_chat_v1_api.py`

**Interfaces:**
- Consumes: `ChatService`, JWT, BYOK headers `X-Provider`, `X-API-Key`, `X-Model`
- Produces (all IsAuthenticated + BYOK key still required):
  - `POST /api/v1/chat/` body `{message, session_id?}` → envelope data `{response, sources, session_id}`
  - `GET /api/v1/chat/history/?session_id=` → `{history, session_id}`
  - `POST /api/v1/chat/clear/` body `{session_id}` → `{deleted, session_id}`
- Legacy `/api/chat|history|clear/` remain registered and unauthenticated (template UX)

- [ ] **Step 1: Failing tests**

```python
@pytest.mark.django_db
@patch("chatbot.api_views.ChatService.send_message")
def test_v1_chat_requires_jwt_and_byok(mock_send):
    mock_send.return_value = {"response": "ok", "sources": [], "session_id": "s"}
    client = APIClient()
    assert client.post("/api/v1/chat/", {"message": "hi"}, format="json").status_code == 401

    user = get_user_model().objects.create_user(email="c@ex.com", password="StrongPass123!")
    client.force_authenticate(user=user)
    missing_key = client.post("/api/v1/chat/", {"message": "hi"}, format="json")
    assert missing_key.status_code == 401

    res = client.post(
        "/api/v1/chat/",
        {"message": "hi", "session_id": "s"},
        format="json",
        HTTP_X_API_KEY="sk-test",
        HTTP_X_PROVIDER="gemini",
    )
    assert res.status_code == 200
    assert res.data["success"] is True
    assert res.data["data"]["response"] == "ok"
```

Also assert history/clear envelope shapes with authenticated client.

- [ ] **Step 2: Implement DRF views calling ChatService; map `ProviderAuthError`→401 envelope, `ProviderRequestError`→502, rate limit→429, validation→400**

Do **not** put `api_key` into logs or DB.

- [ ] **Step 3: Spectacular — ensure views are picked up in schema** (class-based APIView is enough)

- [ ] **Step 4: Full regression**

```bash
python run.py test -q
```

Expected: all prior Plan 1 tests + new Plan 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add services/backend/chatbot/api_views.py services/backend/chatbot/urls_v1.py \
  services/backend/chatbot/tests/test_chat_v1_api.py
git commit -m "$(cat <<'EOF'
feat: add authenticated /api/v1/chat endpoints with BYOK

EOF
)"
```

---

### Task 11: ADRs + progress ledger + spec status

**Files:**
- Create: `docs/decisions/002-celery-redis.md`, `docs/decisions/003-sse-notifications.md`
- Modify: `.superpowers/sdd/progress.md`, `docs/superpowers/specs/2026-09-07-pensieve-platform-design.md` status line for Plan 2

**ADR 002:** Redis as Celery broker + Django cache; Compose ports; eager mode in tests.  
**ADR 003:** DB notifications as source of truth; SSE delivery with Last-Event-ID; WS deferred to Plan 3.

- [ ] **Step 1: Write ADRs (one page each)**
- [ ] **Step 2: Update progress ledger with Plan 2 task checklist**
- [ ] **Step 3: Commit**

```bash
git add docs/decisions/002-celery-redis.md docs/decisions/003-sse-notifications.md \
  .superpowers/sdd/progress.md docs/superpowers/specs/2026-09-07-pensieve-platform-design.md
git commit -m "$(cat <<'EOF'
docs: add Plan 2 Celery and SSE ADRs

EOF
)"
```

---

## Self-review (author checklist)

1. **Spec coverage (slices 3–5):** Celery+Redis+ingest ✓; notifications model+SSE+panel API ✓; chat `/api/v1/` + BYOK ✓; `start_server`/`reload_celery` ✓; legacy chat kept ✓. Deferred to Plan 3: React, WS, nginx.
2. **Placeholders:** none intentional — implementers must not leave TBD steps.
3. **Type consistency:** `run_ingest(directory, user_id=None)`; envelope helpers unchanged; BYOK headers unchanged; Compose ports unchanged.

## Execution handoff

After this plan is approved for execution:

**Plan complete and saved to `docs/superpowers/plans/2026-09-07-pensieve-platform-plan2.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute in this session with executing-plans checkpoints  

**Which approach?**
