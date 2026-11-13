"""Owner-side ingestion: `python -m bepmay_host.ingest` (env: MIGRATE_DATABASE_URL, HOST_EMBEDDER, HOST_CORPUS_DIR).

Idempotent and cheap to rerun: a chunk is re-embedded only when its embedding input or the model changed
(hash compare), so reruns do not spend provider quota. Access fields are always refreshed. Chunks of
documents that left the corpus are deleted. Embedding happens before any write, so a provider failure
leaves the index untouched.
"""
from __future__ import annotations

import hashlib
import os
import sys

import psycopg

from bepmay_host.chunking import Chunk, chunk_doc
from bepmay_host.corpus import CorpusDoc, load_corpus
from bepmay_host.embeddings import Embedder, embedder_from_env
from bepmay_host.postgres_search import vector_literal
from bepmay_host.seed import owner_url

_UPSERT = """
INSERT INTO chunks (chunk_id, doc_id, ord, title, kind, text, allowed_roles, owner_customer_id,
                    embedding, embedding_model, input_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s, %s)
ON CONFLICT (chunk_id) DO UPDATE SET doc_id = EXCLUDED.doc_id, ord = EXCLUDED.ord, title = EXCLUDED.title,
  kind = EXCLUDED.kind, text = EXCLUDED.text, allowed_roles = EXCLUDED.allowed_roles,
  owner_customer_id = EXCLUDED.owner_customer_id, embedding = EXCLUDED.embedding,
  embedding_model = EXCLUDED.embedding_model, input_hash = EXCLUDED.input_hash
"""
_REFRESH = "UPDATE chunks SET kind = %s, allowed_roles = %s, owner_customer_id = %s WHERE chunk_id = %s"


def input_hash(model_id: str, c: Chunk) -> str:
    return hashlib.sha256(f"{model_id}\x00{c.title}\x00{c.text}".encode()).hexdigest()


def ingest(url: str, docs: list[CorpusDoc], embedder: Embedder) -> dict[str, int]:
    chunks = [c for d in docs for c in chunk_doc(d)]
    with psycopg.connect(url, connect_timeout=3) as conn:
        existing = dict(conn.execute("SELECT chunk_id, input_hash FROM chunks").fetchall())
        todo = [c for c in chunks if existing.get(c.chunk_id) != input_hash(embedder.model_id, c)]
        vectors = embedder.embed_documents([(c.title, c.text) for c in todo]) if todo else []
        todo_ids = {c.chunk_id for c in todo}
        stale = sorted(set(existing) - {c.chunk_id for c in chunks})
        with conn.cursor() as cur:
            for c in chunks:
                if c.chunk_id not in todo_ids:
                    cur.execute(_REFRESH, (c.kind, list(c.allowed_roles), c.owner_customer_id, c.chunk_id))
            for c, vec in zip(todo, vectors):
                cur.execute(_UPSERT, (c.chunk_id, c.doc_id, c.ord, c.title, c.kind, c.text, list(c.allowed_roles),
                                      c.owner_customer_id, vector_literal(vec), embedder.model_id, input_hash(embedder.model_id, c)))
            if stale:
                cur.execute("DELETE FROM chunks WHERE chunk_id = ANY(%s)", (stale,))
    return {"chunks": len(chunks), "embedded": len(todo), "deleted": len(stale)}


def main() -> int:
    url = owner_url()
    if not url:
        print("MIGRATE_DATABASE_URL (or DATABASE_URL) is required", file=sys.stderr)
        return 2
    print(ingest(url, load_corpus(os.getenv("HOST_CORPUS_DIR", "../data/corpus")), embedder_from_env()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
