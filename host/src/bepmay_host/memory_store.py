"""In-memory reference adapter: same contract as Postgres, filtering in Python."""
from __future__ import annotations

from bepmay_host.access import Actor, BusinessRecord, RecordSummary, is_visible
from bepmay_host.corpus import CorpusDoc
 


class MemoryBusinessStore:
    def __init__(self, docs: list[CorpusDoc]):
        self._docs = [d for d in docs if d.ref_id is not None]

    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None:
        for d in self._docs:
            if d.kind == kind and d.ref_id == ref_id and is_visible(actor, d.allowed_roles, d.owner_customer_id):
                return BusinessRecord(d.doc_id, d.kind, d.ref_id, d.title, d.body, d.owner_customer_id)
        return None

    def list(self, actor: Actor, kind: str, limit: int) -> list[RecordSummary]:
        rows = [d for d in self._docs if d.kind == kind and is_visible(actor, d.allowed_roles, d.owner_customer_id)]
        return [RecordSummary(d.kind, d.ref_id, d.title) for d in sorted(rows, key=lambda d: d.ref_id)[:limit]]

