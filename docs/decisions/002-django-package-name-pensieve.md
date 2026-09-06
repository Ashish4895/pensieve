# ADR 002: Keep the Django project package named `pensieve`

- **Status:** Accepted
- **Date:** 2026-09-07

## Context

The copied application already uses `pensieve` as its Django project package.
The monorepo reshape moves that package under `services/backend/`. Renaming it
would require changing settings, URL, WSGI, ASGI, command, and deployment
references without resolving a functional conflict.

## Decision

Keep `pensieve` as the Django project package name inside `services/backend/`.
Use the surrounding `services/backend/` path to distinguish the backend service
from the Pensieve product and repository.

## Consequences

- Existing Django imports and entrypoints continue to work after the reshape.
- Deployment and developer commands retain stable settings-module names.
- Product, repository, and Django package share a name; documentation should
  use "backend service" or the full path when that distinction matters.
- A future rename remains possible but must include all Django and deployment
  entrypoints in one migration.
