# Pensieve Platform Plan 3 — React SPA, WebSockets, nginx

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a Vite + React + TypeScript SPA (auth, BYOK chat, notifications/SSE), JWT-authenticated WebSockets on ASGI, and nginx as the compose edge proxy — completing design slices 6–7.

**Architecture:** SPA talks to `/api/v1/` with `Authorization: Bearer <access>`, refresh via httpOnly `refresh` cookie + `X-CSRFToken`, BYOK keys only in `sessionStorage`. Backend wires `django-cors-headers` for the SPA origin. Channels adds a ProtocolTypeRouter beside Django HTTP; WebSocket connects with `?token=<access>` and closes if invalid. nginx terminates `:8080` and proxies `/api/` → backend, `/ws/` → backend, `/` → frontend.

**Tech Stack:** Vite 6, React 19, TypeScript, MUI 6, Redux Toolkit, React Router 7, Vitest + Testing Library; Django Channels + channels-redis; nginx alpine; existing Django 6.1 / DRF / Celery stack.

**Spec:** `docs/superpowers/specs/2026-09-07-pensieve-platform-design.md` (slices 6–7)  
**Base branch:** create `feat/platform-plan3` from current `feat/platform-plan2` HEAD  
**Out of scope:** Render deploy, role→permission matrix, Message user-scoping, Redis chat throttle, replacing Celery, gutting legacy Django templates (keep until SPA is default)

## Global Constraints

- Project root: `/Users/ashishsingh/Project/pensieve`
- Do not modify `/Users/ashishsingh/Project/gemini-chatbot`
- Compose project name stays `pensieve-platform`
- Host ports: **5434** Postgres, **6380** Redis, **8001** backend (direct), **5173** Vite dev, **8080** nginx (compose edge)
- Roles: `user` | `admin` | `super_admin` (matrix deferred; frontend RBAC is UX only)
- API envelope: `{ "success", "message", "data", "errors" }`
- Never persist BYOK provider API keys server-side; store only in `sessionStorage` on the client
- Refresh stays httpOnly cookie path `/api/v1/auth/`; access token in memory (Redux), never `localStorage`
- Prefer reuse over new abstractions; no new backend frameworks beyond Channels
- Commits: frequent, conventional (`feat:`, `fix:`, `chore:`, `docs:`)
- Theme: evolve the existing Pensieve dark glass look from `chatbot/static/chatbot/style.css` — do **not** invent a cream/terracotta or purple-on-white marketing theme

## File map (create / modify)

| Path | Responsibility |
|------|----------------|
| `services/frontend/` | Vite React TS app |
| `env/frontend/.env.example` | `VITE_API_BASE_URL` |
| `services/backend/pensieve/settings.py` | CORS, Channels, CSRF origins |
| `services/backend/pensieve/asgi.py` | ProtocolTypeRouter HTTP + WS |
| `services/backend/realtime/` | WS auth middleware + consumers |
| `docker/frontend/Dockerfile` | multi-stage Vite build → nginx static or node serve |
| `docker/nginx/nginx.conf` | reverse proxy |
| `docker-compose.yml` | `frontend`, `nginx` services |
| `run.py` / `AGENTS.md` | `frontend-dev`, `frontend-test` |
| `docs/decisions/005-spa-cors-auth.md`, `006-websocket-jwt.md`, `007-nginx-edge.md` | ADRs |

## Follow-on (not this plan)

| Item | Notes |
|------|--------|
| Message.user FK / session ownership | IDOR hardening |
| Render deploy | After compose edge is stable |
| Role matrix | Admin UI later |

---

### Task 1: Branch + Vite frontend scaffold

**Files:**
- Create: `services/frontend/` (package.json, vite.config.ts, tsconfig, index.html, src/main.tsx, src/App.tsx)
- Create: `env/frontend/.env.example`
- Modify: `.gitignore` (add `services/frontend/node_modules`, `dist`)

**Interfaces:**
- Consumes: Node 20+
- Produces: `npm run dev` on `http://127.0.0.1:5173`; `npm run build`; `npm test` (vitest stub)

- [ ] **Step 1: Create branch**

```bash
cd /Users/ashishsingh/Project/pensieve
git checkout feat/platform-plan2
git checkout -b feat/platform-plan3
```

- [ ] **Step 2: Scaffold with npm (exact deps)**

```bash
cd /Users/ashishsingh/Project/pensieve
npm create vite@latest services/frontend -- --template react-ts
cd services/frontend
npm install
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material
npm install @reduxjs/toolkit react-redux react-router-dom
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

Configure `vite.config.ts` with `server.port = 5173`, `server.proxy` optional for `/api` → `http://127.0.0.1:8001` (dev convenience).

Add vitest in `vite.config.ts`:

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: "127.0.0.1" },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
  },
});
```

`env/frontend/.env.example`:

```bash
# Browser calls nginx or Vite proxy; leave empty to use same-origin / relative /api
VITE_API_BASE_URL=
```

Minimal `src/App.tsx` renders `<h1>Pensieve</h1>` so build succeeds.

- [ ] **Step 3: Smoke**

```bash
cd services/frontend && npm run build && npm test -- --run
```

Expected: build OK; at least one trivial test `expect(true).toBe(true)` or App smoke.

- [ ] **Step 4: Commit**

```bash
git add services/frontend env/frontend .gitignore
git commit -m "$(cat <<'EOF'
chore: scaffold Vite React TypeScript frontend

EOF
)"
```

---

### Task 2: Backend CORS + CSRF for SPA

**Files:**
- Modify: `services/backend/pensieve/settings.py`, `env/backend/.env.example`
- Test: `services/backend/core/tests/test_cors.py`

**Interfaces:**
- Consumes: `django-cors-headers` (already in pyproject)
- Produces: `CORS_ALLOWED_ORIGINS` from env (default `http://127.0.0.1:5173,http://localhost:5173`); `CORS_ALLOW_CREDENTIALS = True`; `CSRF_TRUSTED_ORIGINS` default includes those origins when empty in DEBUG

- [ ] **Step 1: Failing test**

```python
# services/backend/core/tests/test_cors.py
import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.mark.django_db
@override_settings(
    CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173"],
    CORS_ALLOW_CREDENTIALS=True,
)
def test_cors_preflight_allows_spa_origin():
    client = APIClient()
    res = client.options(
        "/api/v1/auth/login/",
        HTTP_ORIGIN="http://127.0.0.1:5173",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
    )
    assert res.status_code in (200, 204)
    assert res["Access-Control-Allow-Origin"] == "http://127.0.0.1:5173"
    assert res["Access-Control-Allow-Credentials"] == "true"
```

- [ ] **Step 2: Wire settings**

```python
INSTALLED_APPS = [..., "corsheaders", ...]  # before rest_framework is fine
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # high, before CommonMiddleware
    ...
]

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# If CSRF_TRUSTED_ORIGINS empty and DEBUG, default SPA origins:
if not CSRF_TRUSTED_ORIGINS and DEBUG:
    CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
```

Update `env/backend/.env.example` with `CORS_ALLOWED_ORIGINS=...` and ensure `CSRF_TRUSTED_ORIGINS` lists SPA.

- [ ] **Step 3: Test + commit**

```bash
DATABASE_URL=postgres://pensieve:pensieve@127.0.0.1:5433/pensieve_plat \
DJANGO_SECRET_KEY=dev-test-key-at-least-32-chars-long DEBUG=true \
python run.py test core/tests/test_cors.py -q
git commit -am "$(cat <<'EOF'
feat: enable CORS credentials for SPA origins

EOF
)"
```

---

### Task 3: Frontend API client + auth Redux slice

**Files:**
- Create: `services/frontend/src/app/store.ts`, `src/app/hooks.ts`
- Create: `services/frontend/src/features/auth/authSlice.ts`, `src/features/auth/api.ts`
- Create: `services/frontend/src/lib/apiClient.ts`, `src/lib/csrf.ts`
- Test: `services/frontend/src/features/auth/authSlice.test.ts`

**Interfaces:**
- Consumes: `/api/v1/auth/{login,register,refresh,logout,me}/`
- Produces:
  - `apiClient(path, init)` — `credentials: "include"`, attaches `Authorization` from store, reads `csrftoken` cookie into `X-CSRFToken` for unsafe methods
  - `authSlice`: `{ access: string | null, user: { id, email, role } | null, status }`
  - thunks: `login`, `register`, `logout`, `refreshSession`, `loadMe`

- [ ] **Step 1: Failing unit test for login fulfilled**

```ts
// authSlice.test.ts — use configureStore + mocked fetch
import { describe, it, expect, vi, beforeEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import authReducer, { login } from "./authSlice";

describe("authSlice", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          message: "ok",
          data: {
            access: "tok",
            user: { id: 1, email: "a@b.com", role: "user" },
          },
          errors: null,
        }),
      }),
    );
  });

  it("stores access and user on login", async () => {
    const store = configureStore({ reducer: { auth: authReducer } });
    await store.dispatch(
      login({ email: "a@b.com", password: "StrongPass123!" }),
    );
    const state = store.getState().auth;
    expect(state.access).toBe("tok");
    expect(state.user?.email).toBe("a@b.com");
  });
});
```

- [ ] **Step 2: Implement apiClient + slice** (parse envelope; throw on `success: false`)

CSRF helper:

```ts
export function getCookie(name: string): string {
  const row = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return row ? decodeURIComponent(row.split("=").slice(1).join("=")) : "";
}
```

Never write BYOK keys into Redux — only auth meta.

- [ ] **Step 3: `npm test -- --run` + commit**

```bash
git add services/frontend/src
git commit -m "$(cat <<'EOF'
feat: add SPA apiClient and auth Redux slice

EOF
)"
```

---

### Task 4: Auth pages + protected routes + layouts

**Files:**
- Create: `src/features/auth/LoginPage.tsx`, `RegisterPage.tsx`
- Create: `src/routes/ProtectedRoute.tsx`
- Create: `src/layouts/AuthLayout.tsx`, `MainLayout.tsx`
- Create: `src/app/router.tsx`
- Modify: `src/App.tsx`, `src/main.tsx` (Provider + RouterProvider)
- Test: `src/routes/ProtectedRoute.test.tsx`

**Interfaces:**
- Routes: `/login`, `/register` (public); `/` chat, `/notifications` (protected)
- `ProtectedRoute`: if no `access`, redirect to `/login`
- On app load with cookie possible: attempt `refreshSession` then `loadMe` (silent); failure stays logged out

- [ ] **Step 1: Failing ProtectedRoute test** (render with memory router + mock store)

- [ ] **Step 2: Implement pages (MUI TextField/Button; brand “Pensieve” as hero on AuthLayout)**

- [ ] **Step 3: Test + commit**

```bash
git commit -am "$(cat <<'EOF'
feat: add auth pages, layouts, and protected routes

EOF
)"
```

---

### Task 5: Theme (dark glass) + shared shell chrome

**Files:**
- Create: `src/theme/index.ts` (MUI `createTheme` from CSS variables matching legacy dark glass)
- Create: `src/theme/globals.css`
- Modify: `MainLayout` — top bar with Pensieve brand, status, settings gear, logout

**Interfaces:**
- CSS vars: `--bg`, `--glass`, `--accent` derived from `chatbot/static/chatbot/style.css` (dark navy/violet glass — product continuity, not a new marketing look)
- Glass on shell panels only; form controls stay solid enough for a11y

- [ ] **Step 1: Port palette tokens into theme + globals**
- [ ] **Step 2: Visual smoke via Story-less screenshot optional; ensure `npm run build`**
- [ ] **Step 3: Commit**

```bash
git commit -am "$(cat <<'EOF'
feat: add Pensieve dark glass MUI theme and main shell

EOF
)"
```

---

### Task 6: Chat feature (BYOK + `/api/v1/chat/`)

**Files:**
- Create: `src/features/chat/ChatPage.tsx`, `byok.ts`, `chatApi.ts`, `chatSlice.ts` (messages for current session only)
- Test: `src/features/chat/byok.test.ts`

**Interfaces:**
- BYOK keys: `sessionStorage` keys `byok_provider`, `byok_api_key`, `byok_model`, `byok_session_id` (same names as legacy `main.js`)
- `chatApi.sendMessage({ message })` → `POST /api/v1/chat/` with headers `X-Provider`, `X-API-Key`, `X-Model` + Bearer access
- UI: message list, input, settings drawer (provider/key/model), clear session button
- Disable send when no API key (parity with legacy)

- [ ] **Step 1: Failing byok test — roundtrip sessionStorage helpers**

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { loadByok, saveByok } from "./byok";

describe("byok", () => {
  beforeEach(() => sessionStorage.clear());
  it("persists provider and key in sessionStorage only", () => {
    saveByok({ provider: "gemini", apiKey: "sk-test", model: "gemini-2.5-flash" });
    expect(loadByok().apiKey).toBe("sk-test");
    expect(localStorage.getItem("byok_api_key")).toBeNull();
  });
});
```

- [ ] **Step 2: Implement ChatPage + API wiring**
- [ ] **Step 3: Test + commit**

```bash
git commit -am "$(cat <<'EOF'
feat: add BYOK chat page against /api/v1/chat

EOF
)"
```

---

### Task 7: Notifications list + SSE client

**Files:**
- Create: `src/features/notifications/NotificationsPage.tsx`, `notificationsApi.ts`, `sse.ts`, `notificationsSlice.ts`
- Test: `src/features/notifications/sse.test.ts` (parse event blocks; mock EventSource)

**Interfaces:**
- `GET /api/v1/notifications/` → fill inbox in Redux
- `POST /api/v1/notifications/:id/read/`
- `connectNotificationStream({ access, lastEventId, onEvent, onError })` using `EventSource` **cannot** set Authorization headers — **Decision (lock):** use fetch-stream polyfill **or** pass access as `?access=` query **only if backend accepts it for SSE**. Prefer: extend backend SSE view to also accept `access` query param as alternate JWT source (same validator as header), documented in ADR 005. EventSource URL: `/api/v1/notifications/stream/?access=${token}`.
- Reconnect with `Last-Event-ID` via custom fetch streaming client if EventSource+query is insufficient — YAGNI: query token + EventSource first.

Backend change in this task:

```python
# notifications/views.py NotificationStreamView.get
token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
if not token:
    token = request.GET.get("access", "").strip()
# authenticate manually if request.user is anonymous
```

Or simpler: subclass authentication that reads query. Keep IsAuthenticated working.

- [ ] **Step 1: Backend test — stream accepts `?access=` JWT**
- [ ] **Step 2: Frontend SSE client + page**
- [ ] **Step 3: Commit**

```bash
git commit -am "$(cat <<'EOF'
feat: add notifications inbox and SSE client

EOF
)"
```

---

### Task 8: WebSocket JWT auth (Channels)

**Files:**
- Modify: `services/backend/pyproject.toml` — add `channels`, `channels-redis`
- Create: `services/backend/realtime/` app — `auth.py`, `consumers.py`, `routing.py`
- Modify: `pensieve/asgi.py`, `settings.py` (`CHANNEL_LAYERS`, `ASGI_APPLICATION`)
- Test: `services/backend/realtime/tests/test_ws_auth.py` (Channels `WebsocketCommunicator`)

**Interfaces:**
- Route: `ws/v1/chat/` (echo/ping for Plan 3; chat still HTTP — WS proves auth plumbing)
- Connect: `ws://host/ws/v1/chat/?token=<access_jwt>`
- Middleware/auth: validate SimpleJWT access; reject with close code `4401` if missing/invalid
- Consumer: on connect accept; on receive `{"type":"ping"}` reply `{"type":"pong"}`

- [ ] **Step 1: Failing communicator test (reject without token)**

```python
import pytest
from channels.testing import WebsocketCommunicator
from pensieve.asgi import application


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_ws_rejects_missing_token():
    communicator = WebsocketCommunicator(application, "/ws/v1/chat/")
    connected, _ = await communicator.connect()
    assert connected is False
```

- [ ] **Step 2: Implement Channels stack + auth**

```python
# pensieve/asgi.py
import os
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
django_asgi_app = get_asgi_application()

from realtime.auth import JwtAuthMiddlewareStack  # noqa: E402
from realtime.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
})
```

`CHANNEL_LAYERS` Redis using `REDIS_URL`.

- [ ] **Step 3: Add `pytest-asyncio` to backend dev deps; mark tests**
- [ ] **Step 4: Valid token connects + ping/pong test**
- [ ] **Step 5: Commit**

```bash
git commit -am "$(cat <<'EOF'
feat: add Channels WebSocket endpoint with JWT auth

EOF
)"
```

---

### Task 9: Frontend WS client smoke in chat (optional ping)

**Files:**
- Create: `src/features/chat/wsClient.ts`
- Modify: `ChatPage` — on mount open WS with access token; show “live” indicator when open; close on unmount
- Test: `wsClient.test.ts` mock `WebSocket`

**Interfaces:**
- `createChatSocket(access: string, baseWsUrl: string)` → WebSocket to `${baseWsUrl}/ws/v1/chat/?token=...`
- `VITE_WS_BASE_URL` default `ws://127.0.0.1:8001` in dev; empty under nginx (same host `wss?` derived)

- [ ] **Step 1–3: Implement, test, commit**

```bash
git commit -am "$(cat <<'EOF'
feat: connect chat shell to authenticated WebSocket ping

EOF
)"
```

---

### Task 10: Docker frontend + nginx edge

**Files:**
- Create: `docker/frontend/Dockerfile`, `docker/nginx/nginx.conf`, `docker/nginx/Dockerfile` (or single nginx image with conf mount)
- Modify: `docker-compose.yml` — services `frontend`, `nginx`
- Create: `env/frontend/.env.example` already exists; add compose env as needed

**Interfaces:**
- `frontend` builds static assets; serves via nginx container **or** `frontend` is build-only artifact copied into nginx image (prefer **one nginx** that serves SPA `root` + proxies API/WS)
- Host **8080:80** on nginx
- Backend remains on **8001** for direct debug; nginx proxies:
  - `/api/` → `http://backend:8000/api/`
  - `/ws/` → `http://backend:8000/ws/` (Upgrade headers)
  - `/` → SPA `try_files`

Minimal `nginx.conf`:

```nginx
upstream backend {
  server backend:8000;
}
server {
  listen 80;
  root /usr/share/nginx/html;
  location /api/ {
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
  location /ws/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
  }
  location / {
    try_files $uri /index.html;
  }
}
```

Multi-stage Dockerfile: build frontend → copy `dist/` into nginx image with conf.

- [ ] **Step 1: Add files + compose services (`depends_on` backend)**
- [ ] **Step 2: `docker compose config` validates; smoke build if Docker available**
- [ ] **Step 3: Commit**

```bash
git commit -am "$(cat <<'EOF'
chore: add frontend build and nginx edge proxy

EOF
)"
```

---

### Task 11: DX sync + ADRs + spec status

**Files:**
- Modify: `run.py` — `frontend-dev` → `npm run dev` in `services/frontend`; `frontend-test` → `npm test -- --run`; `frontend-build` → `npm run build`
- Modify: `AGENTS.md` — document ports 5173/8080, SPA auth/BYOK rules, WS URL
- Create: `docs/decisions/005-spa-cors-auth.md`, `006-websocket-jwt.md`, `007-nginx-edge.md`
- Modify: design spec status → Plan 3 complete (slices 6–7)
- Modify: `.superpowers/sdd/progress.md`

**ADR 005:** SPA uses cookie refresh + CSRF; CORS credentials; access in Redux memory; SSE `?access=` for EventSource.  
**ADR 006:** WS JWT via query `token`; reject unauthenticated; Channels + Redis layer.  
**ADR 007:** nginx is compose edge on 8080; backend 8001 remains for debug.

- [ ] **Step 1: Write ADRs + DX**
- [ ] **Step 2: Full backend pytest + frontend vitest**
- [ ] **Step 3: Commit**

```bash
git commit -am "$(cat <<'EOF'
docs: add Plan 3 SPA, WebSocket, and nginx ADRs

EOF
)"
```

---

## Self-review (author checklist)

1. **Spec coverage (slices 6–7):** React auth+chat+notifications ✓; WS JWT ✓; nginx ✓; glass theme ✓; run.py/AGENTS ✓; ADRs ✓. Deferred: Render, role matrix, Message ownership.
2. **Placeholders:** none — EventSource JWT via `?access=` is an explicit locked decision.
3. **Type consistency:** refresh cookie name `refresh`; BYOK sessionStorage keys match legacy; ports unchanged for db/redis/backend.

## Execution handoff

**Plan complete and saved to `docs/superpowers/plans/2026-09-07-pensieve-platform-plan3.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
**2. Inline Execution** — execute in this session with executing-plans checkpoints  

**Which approach?**
