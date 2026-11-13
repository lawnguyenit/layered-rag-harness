"""PostgreSQL + pgvector search adapter. Like the records adapter, the query carries no access condition:
row-level security on `chunks` (migration 0003) removes rows the actor may not see before ORDER BY/LIMIT,
so the top-k is taken among permitted chunks only. Needs the non-bypass app role."""
from __future__ import annotations

from psycopg_pool import ConnectionPool

from bepmay_host.access import Actor
from bepmay_host.postgres_store import SET_ACTOR, check_least_privilege
from bepmay_host.search_store import Hit

_SEARCH = """
SELECT chunk_id, doc_id, title, kind, text, 1 - (embedding <=> %(q)s::vector) AS score
FROM chunks
WHERE embedding_model = %(model)s
ORDER BY embedding <=> %(q)s::vector, chunk_id
LIMIT %(k)s
"""


def vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


class PostgresSearchStore:
    def __init__(self, database_url: str, *, min_size: int = 1, max_size: int = 8):
        self.pool = ConnectionPool(database_url, min_size=min_size, max_size=max_size, timeout=3, open=False,
                                   kwargs={"connect_timeout": 3})
        self.pool.open()

    def assert_least_privilege(self) -> None:
        check_least_privilege(self.pool, "chunks")

    def close(self) -> None:
        self.pool.close()

    def search(self, actor: Actor, model_id: str, query_vector: list[float], top_k: int) -> list[Hit]:
        with self.pool.connection() as conn:
            conn.execute(SET_ACTOR, (actor.role, actor.customer_id or ""))
            rows = conn.execute(_SEARCH, {"q": vector_literal(query_vector), "model": model_id, "k": top_k}).fetchall()
        return [Hit(*row[:5], float(row[5])) for row in rows]
