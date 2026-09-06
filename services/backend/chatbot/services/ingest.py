from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db import transaction
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


@lru_cache(maxsize=None)
def _client(api_key: str):
    return genai.Client(api_key=api_key)


def _default_embed_content(chunk: str) -> list[float]:
    api_key = os.environ.get("GEMINI_API_KEY") or getattr(
        settings,
        "GEMINI_API_KEY",
        None,
    )
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required for embeddings")
    response = _client(api_key).models.embed_content(
        model="gemini-embedding-2",
        contents=chunk,
    )
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

    files = sorted(f.name for f in path.iterdir() if f.suffix in {".txt", ".md"})
    total_chunks = 0
    with transaction.atomic():
        DocumentChunk.objects.all().delete()
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
