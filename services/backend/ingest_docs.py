import os
import sys

import django
from dotenv import load_dotenv
from google import genai

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pensieve.settings")
django.setup()

from chatbot.models import DocumentChunk  # noqa: E402

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    print("Error: GEMINI_API_KEY not found in environment. Please check your .env file.")
    sys.exit(1)

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def chunk_text(text, chunk_size=500, overlap=100):
    """
    Split text into chunks of `chunk_size` characters with `overlap` characters.
    This is a simple character-based chunker for learning first principles.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def ingest_documents(directory="documents"):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created '{directory}/' folder. Place text (.txt/.md) files there and run again.")
        return

    DocumentChunk.objects.all().delete()
    print("Cleared existing document chunks from the database.")

    files = [f for f in os.listdir(directory) if f.endswith((".txt", ".md"))]
    if not files:
        print(f"No .txt or .md files found in '{directory}/' folder.")
        return

    for filename in files:
        filepath = os.path.join(directory, filename)
        print(f"Processing {filename}...")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content, chunk_size=500, overlap=100)
        print(f"Split {filename} into {len(chunks)} chunks.")

        for i, chunk in enumerate(chunks):
            try:
                response = client.models.embed_content(
                    model="gemini-embedding-2",
                    contents=chunk,
                )
                embedding_vector = list(response.embeddings[0].values)
                DocumentChunk.objects.create(
                    source_name=filename,
                    content=chunk,
                    embedding=embedding_vector,
                )
                print(f" Saved chunk {i + 1}/{len(chunks)}")
            except Exception as e:
                print(f" Error generating embedding for chunk {i + 1}: {e}")

    print("Ingestion complete!")


if __name__ == "__main__":
    ingest_documents()
