"""PostgreSQL adapter. Authorisation is enforced by row-level security (migration 0002), not here.

The connection must be the non-bypass app role. Every read sets the actor as transaction-local
settings that the policy reads; the query itself deliberately carries no access condition, so a
query that forgets one still cannot leak rows. Seeding needs the table owner: see seed.py.
"""
from __future__ import annotations

from psycopg_pool import ConnectionPool

from bepmay_host.access import Actor, BusinessRecord

_SET_ACTOR = "SELECT set_config('app.role', %s, true), set_config('app.customer_id', %s, true)"

_GET = """
SELECT doc_id, kind, ref_id, title, body, owner_customer_id
FROM records
WHERE kind = %(kind)s AND ref_id = %(ref_id)s
"""


_ROLE_CHECK = """
SELECT r.rolsuper, r.rolbypassrls,
       EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'records' AND tableowner = current_user),
       COALESCE((SELECT c.relrowsecurity AND c.relforcerowsecurity FROM pg_class c WHERE c.relname = 'records'), false)
FROM pg_roles r WHERE r.rolname = current_user
"""


class PostgresBusinessStore:
    """Small pool; one transaction per call so the actor settings cannot outlive the request."""

    def __init__(self, database_url: str, *, min_size: int = 1, max_size: int = 8):
        self.database_url = database_url
        self.pool = ConnectionPool(
            database_url, min_size=min_size, max_size=max_size, timeout=3, open=False,
            kwargs={"connect_timeout": 3},
        )
        self.pool.open()

    def assert_least_privilege(self) -> None:
        """Refuse to run as a role that would silently defeat RLS. Called once at server start."""
        with self.pool.connection() as conn:
            superuser, bypass, owner, rls_on = conn.execute(_ROLE_CHECK).fetchone()
        problems = [
            name for name, bad in (
                ("role is a superuser", superuser),
                ("role has BYPASSRLS", bypass),
                ("role owns the records table", owner),
                ("RLS is not enabled and forced on records (run migrations)", not rls_on),
            ) if bad
        ]
        if problems:
            raise RuntimeError("refusing to start, row-level security would not protect data: " + "; ".join(problems))

    def close(self) -> None:
        self.pool.close()

    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None:
        with self.pool.connection() as conn:
            conn.execute(_SET_ACTOR, (actor.role, actor.customer_id or ""))
            row = conn.execute(_GET, {"kind": kind, "ref_id": ref_id}).fetchone()
        return BusinessRecord(*row) if row else None
