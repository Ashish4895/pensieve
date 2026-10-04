from __future__ import annotations

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from typing import Any

from django.conf import settings
from mcp import Client, StdioServerParameters

from tools.crypto import decrypt_env
from tools.models import McpServer


def build_stdio_params(server: McpServer) -> StdioServerParameters:
    env = {**os.environ, **decrypt_env(server.env_ciphertext)}
    if server.is_builtin:
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "tools.pensieve_mcp"],
            env=env,
            cwd=str(settings.BASE_DIR),
        )
    if not server.command.strip():
        raise ValueError("MCP server command is required")
    args = server.args if isinstance(server.args, list) else []
    return StdioServerParameters(
        command=server.command.strip(),
        args=[str(a) for a in args],
        env=env,
        cwd=str(settings.BASE_DIR),
    )


@asynccontextmanager
async def mcp_session(server: McpServer):
    params = build_stdio_params(server)
    async with Client(params, mode="auto") as client:
        yield client


def _tool_text(result: Any) -> str:
    parts: list[str] = []
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts)
    return str(result)


async def list_remote_tools(server: McpServer) -> list[dict]:
    async with mcp_session(server) as client:
        response = await client.list_tools()
        tools = []
        for tool in response.tools:
            schema = tool.input_schema
            if hasattr(schema, "model_dump"):
                schema = schema.model_dump(by_alias=True, exclude_none=True)
            annotations = tool.annotations
            if annotations is not None and hasattr(annotations, "model_dump"):
                annotations = annotations.model_dump(exclude_none=True)
            tools.append(
                {
                    "name": tool.name,
                    "title": getattr(tool, "title", None) or "",
                    "description": tool.description or "",
                    "input_schema": schema or {},
                    "annotations": annotations or {},
                }
            )
        return tools


async def call_remote_tool(server: McpServer, name: str, arguments: dict) -> str:
    async with mcp_session(server) as client:
        result = await client.call_tool(name, arguments or {})
        return _tool_text(result)


def list_remote_tools_sync(server: McpServer) -> list[dict]:
    return asyncio.run(list_remote_tools(server))


def call_remote_tool_sync(server: McpServer, name: str, arguments: dict) -> str:
    return asyncio.run(call_remote_tool(server, name, arguments))
