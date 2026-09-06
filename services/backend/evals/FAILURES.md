# Known RAG failure modes

## Character chunking splits mid-sentence

The ingest pipeline uses fixed 500-character windows with 100-character overlap. Facts that span a chunk boundary (e.g. a rule split across two windows) may not appear intact in any single retrieved chunk, producing weak or incomplete answers even when the source document contains the fact.

## Toy corpus only; domain shift fails

Golden evals target `spaceship_protocol.txt`, a tiny synthetic corpus. Retrieval quality and answer faithfulness are not representative of real user documents, varied formatting, or out-of-domain questions. Performance drops sharply under domain shift.

## O(n) cosine over all chunks will not scale

`retrieve_relevant_chunks` embeds the query then uses **Postgres pgvector** cosine distance
to rank chunks. Without an ANN index this is still fine for small corpora; for large document
sets add an HNSW/IVFFlat index on `DocumentChunk.embedding`.

## Cross-provider chat with Gemini embeddings can still hallucinate

Chat may run through OpenAI-compatible BYOK providers while embeddings always use the server Gemini key. Even with relevant chunks retrieved, a low similarity threshold (0.3) can admit weak context, and the model may confabulate beyond retrieved text—especially on negative or underspecified questions.

## No citation forcing in the model prompt

The system prompt instructs the model to use context when available but does not require citing chunk sources or quoting spans. The model can blend retrieved facts with parametric knowledge without traceable attribution, making hallucinations hard to detect in the UI.
