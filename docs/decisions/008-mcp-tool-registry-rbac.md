# ADR 008: FastMCP tool registry with platform RBAC

- **Status:** Accepted
- **Date:** 2026-09-28

## Context

Pensieve needs a platform-style tool catalog: operators add MCP servers,
discover tools, and chat uses allowed tools. First-party RAG search should
use the same path as third-party servers. Roles already exist
(`user` / `admin` / `super_admin`); org-scoped ownership is deferred.

## Decision

1. Author MCP servers with the mcp Python SDK high-level server API
   (historically FastMCP; in mcp 2.x: `MCPServer` from `mcp.server`).
2. Ship first-party `pensieve_mcp` as a stdio MCPServer exposing
   `pensieve_search_documents`.
3. Django stores `McpServer` / `ToolDefinition` / `UserToolPreference` and
   discovers/executes tools via the official MCP `Client` over stdio.
4. Encrypt MCP env secrets with Fernet derived from `DJANGO_SECRET_KEY`;
   never return secrets in API responses.
5. RBAC matrix:

| Action | user | admin | super_admin |
|--------|------|-------|-------------|
| List/use enabled tools in chat | yes | yes | yes |
| Personal tool preference toggles | yes | yes | yes |
| CRUD MCP server connections | no | yes | yes |
| Builtin catalog flags / builtin server edits | no | no | yes |

6. Chat tool-calling is Gemini-first; other providers continue without tools
   until a later adapter ships.

## Consequences

- One execution path for builtin and external tools.
- Spawning stdio children per discover/call is simple but not free; HTTP MCP
  transport remains a follow-up.
- Query/tool results may include document text; keep logging redaction and
  never log BYOK or MCP env values.
