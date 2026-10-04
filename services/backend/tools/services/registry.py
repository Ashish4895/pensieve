from __future__ import annotations

from django.db import transaction

from tools.models import McpServer, ToolDefinition, UserToolPreference
from tools.services.mcp_client import call_remote_tool_sync, list_remote_tools_sync

BUILTIN_SERVER_NAME = "pensieve_mcp"
DOCUMENT_SEARCH_TOOL = "pensieve_search_documents"


def ensure_builtin_server(**kwargs) -> McpServer:
    """Create the first-party FastMCP server row if missing (post_migrate)."""
    server, _ = McpServer.objects.get_or_create(
        name=BUILTIN_SERVER_NAME,
        defaults={
            "transport": McpServer.Transport.STDIO,
            "command": "",
            "args": [],
            "enabled": True,
            "is_builtin": True,
        },
    )
    if not server.is_builtin:
        server.is_builtin = True
        server.save(update_fields=["is_builtin"])
    return server


def document_search_enabled_for(user) -> bool:
    """Respect Tools toggle for pensieve_search_documents (default on).

    Gates both MCP tool use and the chat RAG inject path. If the tool is not
    in the catalog yet, keep legacy always-on retrieval.
    """
    if user is None:
        return True
    tool = ToolDefinition.objects.filter(
        name=DOCUMENT_SEARCH_TOOL,
        enabled=True,
        mcp_server__enabled=True,
    ).first()
    if tool is None:
        return True
    pref = UserToolPreference.objects.filter(user=user, tool=tool).first()
    if pref is None:
        return True
    return pref.enabled


def discover_mcp_tools(server: McpServer) -> list[ToolDefinition]:
    remote = list_remote_tools_sync(server)
    upserted: list[ToolDefinition] = []
    seen: set[str] = set()
    with transaction.atomic():
        for item in remote:
            seen.add(item["name"])
            tool, _ = ToolDefinition.objects.update_or_create(
                mcp_server=server,
                name=item["name"],
                defaults={
                    "title": item.get("title") or item["name"],
                    "description": item.get("description") or "",
                    "input_schema": item.get("input_schema") or {},
                    "annotations": item.get("annotations") or {},
                    "enabled": True,
                },
            )
            upserted.append(tool)
        ToolDefinition.objects.filter(mcp_server=server).exclude(name__in=seen).delete()
    return upserted


def tools_for_user(user) -> list[ToolDefinition]:
    """Enabled catalog tools, respecting personal preferences (default on)."""
    qs = (
        ToolDefinition.objects.filter(
            enabled=True,
            mcp_server__enabled=True,
        )
        .select_related("mcp_server")
        .order_by("name")
    )
    prefs = {
        p.tool_id: p.enabled
        for p in UserToolPreference.objects.filter(user=user, tool__in=qs)
    }
    return [t for t in qs if prefs.get(t.id, True)]


def execute_tool(*, user, name: str, arguments: dict | None = None) -> str:
    allowed = {t.name: t for t in tools_for_user(user)}
    tool = allowed.get(name)
    if tool is None:
        raise PermissionError(f"Tool not allowed: {name}")
    if not tool.mcp_server.enabled:
        raise PermissionError(f"MCP server disabled: {tool.mcp_server.name}")
    return call_remote_tool_sync(tool.mcp_server, tool.name, arguments or {})
