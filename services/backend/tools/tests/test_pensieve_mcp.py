import json

import pytest

from tools.pensieve_mcp import pensieve_search_documents


@pytest.mark.django_db
def test_pensieve_search_documents_empty_query():
    payload = json.loads(pensieve_search_documents(""))
    assert payload["results"] == []
    assert "error" in payload


@pytest.mark.django_db
def test_pensieve_search_documents_uses_retriever(monkeypatch):
    monkeypatch.setattr(
        "tools.pensieve_mcp.retrieve_relevant_chunks",
        lambda query, top_k=3, threshold=0.3: [
            {"source": "doc.txt", "score": 0.9, "content": "hello"}
        ],
    )
    payload = json.loads(pensieve_search_documents("hello", top_k=2))
    assert payload["results"][0]["source"] == "doc.txt"
