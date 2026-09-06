import pytest

from chatbot.models import DocumentChunk
from chatbot.services.ingest import chunk_text, ingest_documents


def test_chunk_text_overlaps():
    text = "a" * 600
    chunks = chunk_text(text, chunk_size=500, overlap=100)
    assert len(chunks) == 2
    assert len(chunks[0]) == 500


@pytest.mark.django_db
def test_ingest_documents_uses_injected_embedder(tmp_path):
    doc = tmp_path / "note.txt"
    doc.write_text("hello world " * 40, encoding="utf-8")

    def fake_embed(chunk: str) -> list[float]:
        return [0.1] * 3072

    result = ingest_documents(str(tmp_path), embed_content=fake_embed)
    assert result["files"] == 1
    assert result["chunks"] >= 1
    assert result["cleared"] is True
    assert DocumentChunk.objects.count() == result["chunks"]
    assert DocumentChunk.objects.first().source_name == "note.txt"


@pytest.mark.django_db
def test_ingest_failure_restores_existing_corpus(tmp_path):
    original = DocumentChunk.objects.create(
        source_name="original.txt",
        content="keep me",
        embedding=[0.1] * 3072,
    )
    (tmp_path / "replacement.txt").write_text("x" * 700, encoding="utf-8")
    calls = 0

    def failing_embed(_chunk: str) -> list[float]:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("embedding failed")
        return [0.2] * 3072

    with pytest.raises(RuntimeError, match="embedding failed"):
        ingest_documents(str(tmp_path), embed_content=failing_embed)

    assert list(
        DocumentChunk.objects.values_list("id", "source_name", "content")
    ) == [(original.id, "original.txt", "keep me")]
