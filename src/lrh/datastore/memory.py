"""In-memory reference adapter: same contract as Postgres, filtering in Python."""
from __future__ import annotations

from lrh.datastore.contracts import BusinessRecord, is_visible
from lrh.datastore.corpus import CorpusDoc
from lrh.request_contracts import Actor


class MemoryBusinessStore:
    def __init__(self, docs: list[CorpusDoc]):
        self._docs = [d for d in docs if d.ref_id is not None]

    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None:
        for d in self._docs:
            if d.kind == kind and d.ref_id == ref_id and is_visible(actor, d.allowed_roles, d.owner_customer_id):
                return BusinessRecord(d.doc_id, d.kind, d.ref_id, d.title, d.body, d.owner_customer_id)
        return None
