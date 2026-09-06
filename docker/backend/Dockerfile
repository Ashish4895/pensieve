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

COPY docker/scripts/backend-entrypoint.sh /usr/local/bin/backend-entrypoint
RUN chmod +x /usr/local/bin/backend-entrypoint

EXPOSE 8000

ENTRYPOINT ["backend-entrypoint"]
