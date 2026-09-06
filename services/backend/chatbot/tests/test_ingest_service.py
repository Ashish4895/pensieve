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
