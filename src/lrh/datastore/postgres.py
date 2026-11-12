"""PostgreSQL adapter (H1). Access rule is applied in the WHERE clause of every query.

H2 moves enforcement into row-level security under a non-bypass role; this adapter must keep
passing the same contract tests when that happens.
"""
from __future__ import annotations

import psycopg

from lrh.datastore.contracts import BusinessRecord
from lrh.datastore.corpus import CorpusDoc
from lrh.request_contracts import Actor

_GET = """
SELECT doc_id, kind, ref_id, title, body, owner_customer_id
FROM records
WHERE kind = %(kind)s AND ref_id = %(ref_id)s
  AND %(role)s = ANY(allowed_roles)
  AND (owner_customer_id IS NULL OR %(role)s <> 'customer' OR owner_customer_id = %(cid)s)
"""

_UPSERT = """
INSERT INTO records (doc_id, kind, ref_id, title, body, allowed_roles, owner_customer_id)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (doc_id) DO UPDATE SET kind = EXCLUDED.kind, ref_id = EXCLUDED.ref_id,
  title = EXCLUDED.title, body = EXCLUDED.body, allowed_roles = EXCLUDED.allowed_roles,
  owner_customer_id = EXCLUDED.owner_customer_id
"""


class PostgresBusinessStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None:
        params = {"kind": kind, "ref_id": ref_id, "role": actor.role, "cid": actor.customer_id}
        with psycopg.connect(self.database_url, connect_timeout=3) as conn:
            row = conn.execute(_GET, params).fetchone()
        return BusinessRecord(*row) if row else None

    def seed(self, docs: list[CorpusDoc]) -> int:
        """Idempotent load of synthetic corpus rows that have an exact-lookup reference."""
        rows = [
            (d.doc_id, d.kind, d.ref_id, d.title, d.body, list(d.allowed_roles), d.owner_customer_id)
            for d in docs
            if d.ref_id is not None
        ]
        with psycopg.connect(self.database_url, connect_timeout=3) as conn:
            conn.cursor().executemany(_UPSERT, rows)
        return len(rows)
