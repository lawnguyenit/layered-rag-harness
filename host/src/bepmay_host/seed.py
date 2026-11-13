"""Owner-side setup. Needs the table owner, never the app role.

`python -m bepmay_host.provision` sets the app role password; `python -m bepmay_host.seed` loads the
synthetic corpus. Both read MIGRATE_DATABASE_URL (falls back to DATABASE_URL for a one-role setup).
"""
from __future__ import annotations

import os
import sys

import psycopg

from bepmay_host.corpus import CorpusDoc, load_corpus

_UPSERT = """
INSERT INTO records (doc_id, kind, ref_id, title, body, allowed_roles, owner_customer_id)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (doc_id) DO UPDATE SET kind = EXCLUDED.kind, ref_id = EXCLUDED.ref_id,
  title = EXCLUDED.title, body = EXCLUDED.body, allowed_roles = EXCLUDED.allowed_roles,
  owner_customer_id = EXCLUDED.owner_customer_id
"""


def owner_url() -> str:
    return (os.getenv("MIGRATE_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()


def seed_records(url: str, docs: list[CorpusDoc]) -> int:
    """Idempotent load of synthetic corpus rows that have an exact-lookup reference."""
    rows = [
        (d.doc_id, d.kind, d.ref_id, d.title, d.body, list(d.allowed_roles), d.owner_customer_id)
        for d in docs
        if d.ref_id is not None
    ]
    with psycopg.connect(url, connect_timeout=3) as conn:
        conn.cursor().executemany(_UPSERT, rows)
    return len(rows)


def main() -> int:
    url = owner_url()
    if not url:
        print("MIGRATE_DATABASE_URL (or DATABASE_URL) is required", file=sys.stderr)
        return 2
    count = seed_records(url, load_corpus(os.getenv("HOST_CORPUS_DIR", "../data/corpus")))
    print(f"seeded {count} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
