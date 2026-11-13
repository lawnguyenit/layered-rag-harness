"""Split a corpus document into chunks. The corpus is small (one to a few short paragraphs per file), so
chunks are paragraph groups up to a character budget; every chunk keeps its document's access fields."""
from __future__ import annotations

from dataclasses import dataclass

from bepmay_host.corpus import CorpusDoc

MAX_CHARS = 800


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    ord: int
    title: str
    kind: str
    text: str
    allowed_roles: tuple[str, ...]
    owner_customer_id: str | None


def chunk_doc(doc: CorpusDoc, max_chars: int = MAX_CHARS) -> list[Chunk]:
    parts: list[str] = []
    for para in (p.strip() for p in doc.body.split("\n\n") if p.strip()):
        if parts and len(parts[-1]) + len(para) + 2 <= max_chars:
            parts[-1] += "\n\n" + para
        else:
            parts.append(para)
    return [
        Chunk(f"{doc.doc_id}#{i}", doc.doc_id, i, doc.title, doc.kind, text, doc.allowed_roles, doc.owner_customer_id)
        for i, text in enumerate(parts)
    ]
