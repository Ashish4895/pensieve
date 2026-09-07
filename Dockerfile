# Render web image: Vite SPA + Django ASGI (API / SSE / WS) on one service.
FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY services/frontend/package.json services/frontend/package-lock.json ./
RUN npm ci
COPY services/frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    SPA_ROOT=/app/spa

WORKDIR /app

COPY services/backend/pyproject.toml services/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY services/backend/ ./
RUN uv sync --frozen --no-dev

COPY --from=frontend /frontend/dist /app/spa
COPY docker/scripts/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

EXPOSE 8000

ENTRYPOINT ["backend-entrypoint"]
