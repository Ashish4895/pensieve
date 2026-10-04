"""First-party FastMCP-style server (mcp 2.x: MCPServer)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _bootstrap_django() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
    import django

    django.setup()


_bootstrap_django()

from mcp.server import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

from chatbot.rag_helper import retrieve_relevant_chunks  # noqa: E402

mcp = MCPServer("pensieve_mcp")


@mcp.tool(
    name="pensieve_search_documents",
    title="Search documents",
    description=(
        "Search the Pensieve document corpus with semantic retrieval. "
        "Use when answering questions about uploaded/ingested documents. "
        "Do NOT use for general knowledge unrelated to the corpus."
    ),
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
def pensieve_search_documents(query: str, top_k: int = 3) -> str:
    """Return top matching document chunks for a natural-language query.

    Args:
        query: Question or search phrase.
        top_k: Max chunks to return (1-10).
    """
    k = max(1, min(int(top_k or 3), 10))
    q = (query or "").strip()
    if not q:
        return json.dumps({"results": [], "error": "query is required"})

    chunks = retrieve_relevant_chunks(q, top_k=k, threshold=0.3)
    payload = {
        "results": [
            {
                "source": item["source"],
                "score": round(float(item["score"]), 4),
                "content": item["content"],
            }
            for item in chunks
        ]
    }
    return json.dumps(payload)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
