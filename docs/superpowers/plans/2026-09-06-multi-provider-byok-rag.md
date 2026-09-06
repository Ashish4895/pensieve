# Multi-Provider BYOK RAG Chatbot (Portfolio Hero) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `gemini-chatbot` into a deployable, resume-ready RAG demo where visitors bring their own chat API key (Gemini or OpenAI-compatible), while retrieval stays on a fixed Gemini embedding pipeline, with evals, Docker, and a clear README.

**Architecture:** Django keeps serving the UI and RAG retrieval. Chat generation is routed through a small `ChatProvider` interface (`GeminiProvider`, `OpenAICompatibleProvider`). User keys arrive per-request in headers (never stored in DB). Query/document embeddings always use server-side `GEMINI_API_KEY` so the corpus and cosine similarity stay consistent. Frontend holds provider + key + model in `sessionStorage` only.

**Tech Stack:** Django 6, Google GenAI SDK, `openai` Python SDK (covers OpenAI + OpenRouter via `base_url`), SQLite, vanilla JS/CSS, Docker + Gunicorn, pytest, optional Ragas later as a thin script.

## Global Constraints

- Never persist user API keys to DB, logs, analytics, or `localStorage` (use `sessionStorage` or memory only).
- Do not log request bodies that may contain `X-API-Key`.
- Embeddings remain Gemini (`gemini-embedding-001` or current project model); do not switch embedding space per chat provider in v1.
- Support providers in v1: `gemini`, `openai`, `openrouter` (OpenAI-compatible). No Anthropic until v2.
- Server `GEMINI_API_KEY` required for ingest + retrieval embeddings; chat uses visitor BYOK.
- Keep scope lean: no LiteLLM, no Celery, no pgvector migration in this plan.
- Secrets: `.env` stays gitignored; ship `.env.example` only.

## File Structure

| Path | Responsibility |
|------|----------------|
| `chatbot/providers/base.py` | `ChatMessage`, `ChatProvider` Protocol, shared errors |
| `chatbot/providers/gemini.py` | Gemini chat via `google.genai` |
| `chatbot/providers/openai_compatible.py` | OpenAI + OpenRouter chat |
| `chatbot/providers/factory.py` | `get_provider(name) -> ChatProvider` |
| `chatbot/providers/__init__.py` | Public exports |
| `chatbot/rag_helper.py` | Keep cosine retrieval; use server Gemini key only |
| `chatbot/views.py` | Accept provider/key/model headers; call provider; return sources |
| `chatbot/templates/chatbot/index.html` | Settings panel: provider, key, model, privacy note |
| `chatbot/static/chatbot/main.js` | sessionStorage BYOK; send headers; show sources |
| `chatbot/static/chatbot/style.css` | Settings panel styles |
| `chatbot/tests/test_providers.py` | Provider unit tests (mocked HTTP) |
| `chatbot/tests/test_views_byok.py` | API contract: missing key → 401; key not stored |
| `evals/golden_qa.json` | Fixed Q&A against spaceship doc |
| `evals/run_eval.py` | Offline retrieval+answer smoke eval |
| `evals/FAILURES.md` | Documented failure modes |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore` | Deployable image |
| `requirements.txt` | Pinned runtime deps |
| `.env.example` | Documented env vars |
| `README.md` | Architecture, BYOK, run, eval, deploy |
| Portfolio: `ashish-portfolio/src/data/portfolio.js` | Link project when live URL exists |

---

### Task 1: Provider interface + Gemini chat adapter

**Files:**
- Create: `chatbot/providers/__init__.py`
- Create: `chatbot/providers/base.py`
- Create: `chatbot/providers/gemini.py`
- Create: `chatbot/providers/factory.py`
- Create: `chatbot/tests/test_providers.py`
- Create: `chatbot/tests/__init__.py`
- Modify: `requirements.txt` (create if missing) — add `pytest`, keep `google-genai`, `python-dotenv`, `django`

**Interfaces:**
- Produces:
  - `ChatMessage(role: str, content: str)` dataclass
  - `ChatProvider.complete(messages: list[ChatMessage], system: str | None, api_key: str, model: str) -> str`
  - `UnsupportedProviderError`, `ProviderAuthError`, `ProviderRequestError`
  - `get_provider(name: str) -> ChatProvider`
  - `GeminiProvider` implementing `ChatProvider`

- [ ] **Step 1: Write failing provider tests**

```python
# chatbot/tests/test_providers.py
from unittest.mock import MagicMock, patch
import pytest
from chatbot.providers.base import ChatMessage
from chatbot.providers.factory import get_provider
from chatbot.providers.gemini import GeminiProvider

def test_factory_unknown_provider():
    with pytest.raises(Exception):
        get_provider("anthropic")

def test_gemini_complete_returns_text():
    provider = GeminiProvider()
    messages = [ChatMessage(role="user", content="hi")]
    fake_response = MagicMock()
    fake_response.text = "hello"
    with patch("chatbot.providers.gemini.genai.Client") as Client:
        client = Client.return_value
        chat = client.chats.create.return_value
        chat.send_message.return_value = fake_response
        out = provider.complete(messages, system="be brief", api_key="AIza-test", model="gemini-2.5-flash")
    assert out == "hello"
    Client.assert_called()  # constructed with api key wiring
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ashishsingh/Project/gemini-chatbot && ./venv/bin/pip install pytest -q && ./venv/bin/pytest chatbot/tests/test_providers.py -v`  
Expected: FAIL (modules missing)

- [ ] **Step 3: Implement base + Gemini + factory**

```python
# chatbot/providers/base.py
from dataclasses import dataclass
from typing import Protocol

@dataclass
class ChatMessage:
    role: str  # "user" | "model" | "assistant" (normalize in adapters)
    content: str

class ProviderAuthError(Exception):
    pass

class ProviderRequestError(Exception):
    pass

class UnsupportedProviderError(Exception):
    pass

class ChatProvider(Protocol):
    def complete(
        self,
        messages: list[ChatMessage],
        system: str | None,
        api_key: str,
        model: str,
    ) -> str: ...
```

```python
# chatbot/providers/gemini.py
from google import genai
from google.genai import types
from .base import ChatMessage, ProviderAuthError, ProviderRequestError

class GeminiProvider:
    def complete(self, messages, system, api_key, model):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Missing Gemini API key")
        try:
            client = genai.Client(api_key=api_key.strip())
            history = []
            # All but last message become history; last is the new user turn
            *prior, last = messages
            for m in prior:
                role = "user" if m.role == "user" else "model"
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=m.content)]))
            config = types.GenerateContentConfig()
            if system:
                config.system_instruction = system
            chat = client.chats.create(model=model or "gemini-2.5-flash", history=history, config=config)
            if last.role != "user":
                raise ProviderRequestError("Last message must be from user")
            return chat.send_message(last.content).text
        except ProviderAuthError:
            raise
        except Exception as e:
            msg = str(e).lower()
            if "api key" in msg or "401" in msg or "403" in msg:
                raise ProviderAuthError(str(e)) from e
            raise ProviderRequestError(str(e)) from e
```

```python
# chatbot/providers/factory.py
from .base import UnsupportedProviderError
from .gemini import GeminiProvider

_PROVIDERS = {
    "gemini": GeminiProvider(),
}

def get_provider(name: str):
    key = (name or "").strip().lower()
    if key not in _PROVIDERS:
        raise UnsupportedProviderError(f"Unsupported provider: {name}")
    return _PROVIDERS[key]
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `./venv/bin/pytest chatbot/tests/test_providers.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add chatbot/providers chatbot/tests requirements.txt
git commit -m "feat: add ChatProvider interface and Gemini adapter"
```

---

### Task 2: OpenAI-compatible provider (OpenAI + OpenRouter)

**Files:**
- Create: `chatbot/providers/openai_compatible.py`
- Modify: `chatbot/providers/factory.py`
- Modify: `chatbot/tests/test_providers.py`
- Modify: `requirements.txt` — add `openai>=1.40`

**Interfaces:**
- Consumes: `ChatMessage`, `ChatProvider`, error types from Task 1
- Produces: `OpenAICompatibleProvider(base_url: str | None = None)`; factory keys `openai`, `openrouter`

- [ ] **Step 1: Write failing tests**

```python
def test_openai_compatible_maps_roles():
    from chatbot.providers.openai_compatible import OpenAICompatibleProvider
    provider = OpenAICompatibleProvider()
    messages = [
        ChatMessage(role="user", content="q1"),
        ChatMessage(role="model", content="a1"),
        ChatMessage(role="user", content="q2"),
    ]
    with patch("chatbot.providers.openai_compatible.OpenAI") as OpenAI:
        client = OpenAI.return_value
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="ok"))
        ]
        out = provider.complete(messages, system="sys", api_key="sk-test", model="gpt-4o-mini")
    assert out == "ok"
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][2]["role"] == "assistant"  # model -> assistant
```

```python
def test_factory_openrouter():
    p = get_provider("openrouter")
    assert p is not None
```

- [ ] **Step 2: Run tests — expect FAIL**

Run: `./venv/bin/pytest chatbot/tests/test_providers.py::test_openai_compatible_maps_roles -v`

- [ ] **Step 3: Implement adapter**

```python
# chatbot/providers/openai_compatible.py
from openai import OpenAI, AuthenticationError, APIError
from .base import ChatMessage, ProviderAuthError, ProviderRequestError

OPENROUTER_BASE = "https://openrouter.ai/api/v1"

class OpenAICompatibleProvider:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url

    def complete(self, messages, system, api_key, model):
        if not api_key or not api_key.strip():
            raise ProviderAuthError("Missing API key")
        try:
            client = OpenAI(api_key=api_key.strip(), base_url=self.base_url)
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            for m in messages:
                role = "assistant" if m.role in ("model", "assistant") else "user"
                api_messages.append({"role": role, "content": m.content})
            resp = client.chat.completions.create(
                model=model or "gpt-4o-mini",
                messages=api_messages,
            )
            return resp.choices[0].message.content or ""
        except AuthenticationError as e:
            raise ProviderAuthError(str(e)) from e
        except APIError as e:
            raise ProviderRequestError(str(e)) from e
```

Register in factory:

```python
_PROVIDERS = {
    "gemini": GeminiProvider(),
    "openai": OpenAICompatibleProvider(),
    "openrouter": OpenAICompatibleProvider(base_url=OPENROUTER_BASE),
}
```

- [ ] **Step 4: Run full provider tests — PASS**

Run: `./venv/bin/pip install 'openai>=1.40' -q && ./venv/bin/pytest chatbot/tests/test_providers.py -v`

- [ ] **Step 5: Commit**

```bash
git add chatbot/providers requirements.txt chatbot/tests/test_providers.py
git commit -m "feat: add OpenAI/OpenRouter compatible chat provider"
```

---

### Task 3: BYOK API contract on `send_message` (no key persistence)

**Files:**
- Modify: `chatbot/views.py`
- Modify: `chatbot/rag_helper.py` (ensure embeddings use `os.environ["GEMINI_API_KEY"]` only)
- Create: `chatbot/tests/test_views_byok.py`

**Interfaces:**
- Consumes: `get_provider`, provider errors, `retrieve_relevant_chunks`, `ChatMessage`
- Produces: HTTP API
  - Headers: `X-Provider`, `X-API-Key`, `X-Model` (optional)
  - Body unchanged: `{ "message", "session_id" }`
  - Response adds optional `sources: [{source, score}]` (content optional / truncated)
  - `401` if missing/invalid key; `400` if unsupported provider

- [ ] **Step 1: Write failing API tests**

```python
# chatbot/tests/test_views_byok.py
import json
import pytest
from django.test import Client, override_settings
from unittest.mock import patch

@pytest.fixture
def client():
    return Client()

def test_send_message_requires_api_key_header(client):
    res = client.post(
        "/api/send/",
        data=json.dumps({"message": "hi", "session_id": "t1"}),
        content_type="application/json",
        HTTP_X_PROVIDER="gemini",
    )
    assert res.status_code == 401

@patch("chatbot.views.retrieve_relevant_chunks", return_value=[])
@patch("chatbot.views.get_provider")
def test_send_message_passes_key_to_provider(mock_get, mock_rag, client):
    provider = mock_get.return_value
    provider.complete.return_value = "answer"
    res = client.post(
        "/api/send/",
        data=json.dumps({"message": "hi", "session_id": "t2"}),
        content_type="application/json",
        HTTP_X_PROVIDER="openai",
        HTTP_X_API_KEY="sk-test",
        HTTP_X_MODEL="gpt-4o-mini",
    )
    assert res.status_code == 200
    assert res.json()["response"] == "answer"
    kwargs = provider.complete.call_args.kwargs
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["model"] == "gpt-4o-mini"
```

Also assert `Message` rows never contain the api key string.

- [ ] **Step 2: Run — expect FAIL**

Run: `./venv/bin/pytest chatbot/tests/test_views_byok.py -v`

- [ ] **Step 3: Refactor `views.send_message`**

Core flow:

1. Parse JSON body (`message`, `session_id`).
2. Read `provider = request.headers.get("X-Provider", "gemini")`, `api_key = request.headers.get("X-API-Key")`, `model = request.headers.get("X-Model")`.
3. If not `api_key`: return `JsonResponse({"error": "API key required"}, status=401)`.
4. Load DB history → `list[ChatMessage]` (map `model` role as-is).
5. `context_items = retrieve_relevant_chunks(...)` using **server** Gemini env key inside `rag_helper`.
6. Build `system_instruction` from context (existing prompt text).
7. Append current user message to messages list **after** saving user row (or build messages including new user text for provider; keep DB save order as today).
8. `text = get_provider(provider).complete(...)`.
9. Save model message; return `{ response, sources }` where sources omit full embedding and may truncate content to 200 chars.
10. Map `ProviderAuthError` → 401, `UnsupportedProviderError` → 400, `ProviderRequestError` → 502.

Remove construction of `genai.Client()` at module level for chat (embeddings client stays in `rag_helper` via env).

Update `rag_helper.get_query_embedding` to pass `api_key=os.environ.get("GEMINI_API_KEY")` explicitly into `genai.Client(api_key=...)`.

- [ ] **Step 4: Run view + provider tests — PASS**

Run: `./venv/bin/pytest chatbot/tests/ -v`

- [ ] **Step 5: Commit**

```bash
git add chatbot/views.py chatbot/rag_helper.py chatbot/tests/test_views_byok.py
git commit -m "feat: route chat through BYOK providers; keep server-side embeddings"
```

---

### Task 4: Frontend settings panel (sessionStorage BYOK)

**Files:**
- Modify: `chatbot/templates/chatbot/index.html`
- Modify: `chatbot/static/chatbot/main.js`
- Modify: `chatbot/static/chatbot/style.css`

**Interfaces:**
- Consumes: Task 3 headers API
- Produces: UI state in `sessionStorage` keys: `byok_provider`, `byok_api_key`, `byok_model`
- Default models map: `gemini → gemini-2.5-flash`, `openai → gpt-4o-mini`, `openrouter → openai/gpt-4o-mini`

- [ ] **Step 1: Add settings UI markup**

In `index.html` header area, add a collapsible panel:

- Select `#provider-select` options: Gemini, OpenAI, OpenRouter
- Password input `#api-key-input` (autocomplete="off")
- Text input `#model-input`
- Checkbox or note: “Key stays in this browser tab (sessionStorage). Never stored on the server.”
- Link to Google AI Studio / OpenAI keys
- Update title from “Gemini AI” → “RAG Chatbot” (or “Doc Q&A”)
- Update suggestion chips to spaceship-protocol questions, e.g. “What fuel does the engine use?”, “What is the fire warning phrase?”

- [ ] **Step 2: Wire `main.js`**

On load: restore sessionStorage into inputs.  
On change: persist to sessionStorage.  
On send:

```javascript
const headers = {
  "Content-Type": "application/json",
  "X-Provider": providerSelect.value,
  "X-API-Key": apiKeyInput.value.trim(),
  "X-Model": modelInput.value.trim(),
};
if (!headers["X-API-Key"]) {
  appendMessage("model", "Add your API key in Settings before chatting.");
  return;
}
const response = await fetch("/api/send/", {
  method: "POST",
  headers,
  body: JSON.stringify({ message: text, session_id: SESSION_ID }),
});
```

If response includes `sources`, render a small “Retrieved context” block under the bot bubble (source name + score).

Disable send while empty key; show status “Key required” vs “Online”.

- [ ] **Step 3: Manual test**

Run: `./venv/bin/python manage.py runserver`  
Checklist:
- No key → friendly error, no 500
- Gemini key → RAG answer citing neon green fuel
- OpenAI key + Gemini server embed env set → answer works
- Refresh tab → key still present (sessionStorage)
- New browser session → key gone
- Clear history still works

- [ ] **Step 4: Commit**

```bash
git add chatbot/templates chatbot/static
git commit -m "feat: add BYOK settings panel with sessionStorage"
```

---

### Task 5: Hardening + rate limit + CSRF posture

**Files:**
- Modify: `chatbot/views.py`
- Modify: `chatbot_project/settings.py`
- Create: `chatbot/rate_limit.py` (simple in-memory IP counter)

**Interfaces:**
- Produces: max **30** `/api/send/` requests per IP per hour (configurable via `CHAT_RATE_LIMIT`)
- Logging filter: never log headers named `X-Api-Key` / `X-API-Key`

- [ ] **Step 1: Implement sliding/fixed window counter**

```python
# chatbot/rate_limit.py
import time
from collections import defaultdict, deque
from django.conf import settings

_hits: dict[str, deque[float]] = defaultdict(deque)

def allow(ip: str) -> bool:
    limit = int(getattr(settings, "CHAT_RATE_LIMIT", 30))
    window = 3600
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True
```

Call from `send_message`; on deny return `429`.

- [ ] **Step 2: CSRF**

Keep `@csrf_exempt` only on JSON APIs **or** switch frontend to read CSRF cookie and send `X-CSRFToken` (preferred for deploy). Prefer CSRF token approach:

- Remove `@csrf_exempt` from `send_message` / `clear_history`
- In `main.js`, read `csrftoken` cookie and set header

- [ ] **Step 3: Settings for production**

```python
# settings.py additions
import os
from dotenv import load_dotenv
load_dotenv()
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", SECRET_KEY)
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CHAT_RATE_LIMIT = int(os.environ.get("CHAT_RATE_LIMIT", "30"))
```

- [ ] **Step 4: Manual + pytest for 429**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: rate-limit chat API and tighten deploy settings"
```

---

### Task 6: Golden evals + failure write-up

**Files:**
- Create: `evals/golden_qa.json`
- Create: `evals/run_eval.py`
- Create: `evals/FAILURES.md`

**Interfaces:**
- Consumes: ingested `DocumentChunk` rows + `retrieve_relevant_chunks` + optional chat provider
- Produces: console report with retrieval hit rate; exit code 1 if retrieval hit rate &lt; 0.8

- [ ] **Step 1: Author golden set (spaceship doc)**

```json
[
  {"id": "fuel", "q": "What fuel must be used?", "expect_substring": "Antigravity Fluid"},
  {"id": "preheat", "q": "How long is engine pre-heat?", "expect_substring": "140 seconds"},
  {"id": "comms", "q": "Emergency phrase for communication loss?", "expect_substring": "eagle has landed"},
  {"id": "fire", "q": "Kitchen fire warning signal?", "expect_substring": "Flambé out of control"},
  {"id": "socks", "q": "What socks on Tuesdays?", "expect_substring": "orange flight socks"},
  {"id": "negative", "q": "What is the captain's birthday?", "expect_not_in_docs": true}
]
```

- [ ] **Step 2: Retrieval eval script**

`run_eval.py` boots Django, for each item checks whether any top-3 chunk contains `expect_substring` (or for negative, that system prompt path would say not found — retrieval may be empty/low). Print a markdown table. Write scores into stdout.

- [ ] **Step 3: Write `FAILURES.md`** with at least:
  - Character chunking splits mid-sentence → weak answers on boundary facts
  - Toy corpus only; domain shift fails
  - O(n) cosine over all chunks will not scale
  - Cross-provider chat with Gemini embeddings can still hallucinate if threshold too low
  - No citation forcing in the model prompt beyond “use context”

- [ ] **Step 4: Run eval after ingest**

```bash
./venv/bin/python ingest_docs.py
./venv/bin/python evals/run_eval.py
```

Expected: hit rate ≥ 0.8 on positive questions.

- [ ] **Step 5: Commit**

```bash
git add evals
git commit -m "test: add golden RAG evals and document failure modes"
```

---

### Task 7: Docker + requirements + env example

**Files:**
- Create: `requirements.txt` (complete pin set if not already)
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Modify: `.gitignore` — ensure `.env`, `venv`, `*.sqlite3`, `db.sqlite3` ignored (keep ability to bake empty db or migrate on start)

**Interfaces:**
- Produces: `docker compose up --build` serves app on `:8000`
- Env: `GEMINI_API_KEY`, `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CHAT_RATE_LIMIT`

- [ ] **Step 1: Freeze requirements**

Include at minimum: `django`, `google-genai`, `openai`, `python-dotenv`, `gunicorn`, `pytest`

- [ ] **Step 2: Dockerfile**

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python manage.py migrate --noinput && python ingest_docs.py && gunicorn chatbot_project.wsgi:application --bind 0.0.0.0:8000"]
```

- [ ] **Step 3: docker-compose.yml**

Map port `8000:8000`, `env_file: .env`, volume optional for sqlite.

- [ ] **Step 4: Smoke test**

```bash
docker compose up --build
curl -s http://localhost:8000/ | head
```

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore .env.example requirements.txt .gitignore
git commit -m "chore: add Docker deploy path and env example"
```

---

### Task 8: README (portfolio-grade)

**Files:**
- Create: `README.md`

Must include:
1. One-paragraph problem statement (grounded Q&A over private docs)
2. Architecture diagram (mermaid): Browser → Django → (RAG/Gemini embed + ChatProvider)
3. BYOK security model (sessionStorage, header, not stored)
4. Provider table (Gemini / OpenAI / OpenRouter) + embedding note
5. Local run + Docker run
6. How to get API keys
7. Eval section + link to `evals/FAILURES.md`
8. Cost note: host pays embeddings; user pays chat
9. Screenshots placeholder
10. License / personal project disclaimer

- [ ] **Step 1: Write README**
- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add portfolio README for multi-provider RAG chatbot"
```

---

### Task 9: Deploy + portfolio link

**Files:**
- Modify (later): `/Users/ashishsingh/Desktop/Projects/ashish-portfolio/src/data/portfolio.js` — add/update project entry with `url` / demo link once live
- Modify: `ProjectCard.jsx` already supports points; ensure `url` field is wired if not (add `href` on ExternalLink if missing)

**Steps:**
- [ ] Deploy to Railway / Render / Fly / VPS with `GEMINI_API_KEY` + `DJANGO_SECRET_KEY`
- [ ] Verify HTTPS
- [ ] Add live URL + GitHub URL to portfolio `PROJECTS` (top card or replace Knowledge Hub duplicate if overlapping)
- [ ] Record 60–90s demo (optional asset)
- [ ] Commit + push both repos

---

## Out of Scope (explicit YAGNI)

- Anthropic provider, LiteLLM, LangChain rewrite
- pgvector / Postgres migration
- User accounts, billing, key vaults
- Streaming SSE responses (nice-to-have later)
- Re-embedding corpus per chat provider
- Hosted “free demo” key with shared quota

## Self-Review

1. **Spec coverage:** BYOK ✓, multi-provider (Gemini/OpenAI/OpenRouter) ✓, fixed embeddings ✓, no key persistence ✓, evals ✓, Docker ✓, README ✓, portfolio link ✓  
2. **Placeholders:** none intentional  
3. **Type consistency:** `ChatMessage`, `ChatProvider.complete(...)`, headers `X-Provider` / `X-API-Key` / `X-Model` used consistently across tasks

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-09-06-multi-provider-byok-rag.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run tasks in this session with checkpoints  

Which approach?
