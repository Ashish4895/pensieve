import os

from dotenv import load_dotenv
from google import genai
from pgvector.django import CosineDistance

from .models import DocumentChunk

load_dotenv()


def get_query_embedding(query_text):
    """Retrieve the embedding vector for the query text."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=query_text,
    )
    return list(response.embeddings[0].values)


def retrieve_relevant_chunks(query_text, top_k=3, threshold=0.3):
    """
    Retrieve the top_k most similar document chunks using Postgres pgvector
    cosine distance (similarity = 1 - distance).
    """
    if not DocumentChunk.objects.exists():
        return []

    query_vector = get_query_embedding(query_text)
    max_distance = 1.0 - threshold

    ranked = (
        DocumentChunk.objects.annotate(distance=CosineDistance("embedding", query_vector))
        .filter(distance__lte=max_distance)
        .order_by("distance")[:top_k]
    )

    results = []
    for chunk in ranked:
        results.append(
            {
                "score": 1.0 - float(chunk.distance),
                "content": chunk.content,
                "source": chunk.source_name,
            }
        )
    return results
