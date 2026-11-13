"""Search over document chunks. Access is decided before ranking: a chunk the actor may not see is never a candidate."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from bepmay_host.access import Actor, is_visible
from bepmay_host.chunking import Chunk, chunk_doc
from bepmay_host.corpus import CorpusDoc
from bepmay_host.embeddings import Embedder


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    doc_id: str
    title: str
    kind: str
    text: str
    score: float


class SearchStore(Protocol):
    def search(self, actor: Actor, model_id: str, query_vector: list[float], top_k: int) -> list[Hit]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))) or 1.0)


class MemorySearchStore:
    """Reference adapter: filter in Python, rank by cosine. Defines the behaviour Postgres must match."""

    def __init__(self, docs: list[CorpusDoc], embedder: Embedder):
        self.model_id = embedder.model_id
        self._rows: list[tuple[Chunk, list[float]]] = []
        for doc in docs:
            chunks = chunk_doc(doc)
            vectors = embedder.embed_documents([(c.title, c.text) for c in chunks])
            self._rows += list(zip(chunks, vectors))

    def search(self, actor, model_id, query_vector, top_k):
        if model_id != self.model_id:
            return []
        scored = [
            Hit(c.chunk_id, c.doc_id, c.title, c.kind, c.text, _cosine(query_vector, v))
            for c, v in self._rows
            if is_visible(actor, c.allowed_roles, c.owner_customer_id)
        ]
        return sorted(scored, key=lambda h: (-h.score, h.chunk_id))[:top_k]
