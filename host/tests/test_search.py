"""H4 tests: search contract (memory reference vs Postgres+pgvector), ingestion, embedder, HTTP route.

Postgres cases need HOST_TEST_DATABASE_URL (table owner, migrated to head) and HOST_TEST_APP_DATABASE_URL
(non-bypass app role). Embeddings here use the deterministic HashEmbedder: these tests prove access control,
plumbing and idempotency, not retrieval quality (that needs the real embedder and an evaluation set).
"""
import json
import os
from pathlib import Path

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient

from bepmay_host.access import Actor, is_visible
from bepmay_host.api import create_app
from bepmay_host.auth import AuthenticationError
from bepmay_host.chunking import chunk_doc
from bepmay_host.corpus import load_corpus
from bepmay_host.embeddings import EmbeddingUnavailable, GeminiRestEmbedder, HashEmbedder
from bepmay_host.ingest import ingest
from bepmay_host.memory_store import MemoryBusinessStore
from bepmay_host.postgres_search import PostgresSearchStore
from bepmay_host.search_store import MemorySearchStore

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"
OWNER = os.getenv("HOST_TEST_DATABASE_URL", "").strip()
APP = os.getenv("HOST_TEST_APP_DATABASE_URL", "").strip()
needs_pg = pytest.mark.skipif(not (OWNER and APP), reason="HOST_TEST_DATABASE_URL / HOST_TEST_APP_DATABASE_URL not set")

DOCS = load_corpus(CORPUS)
EMB = HashEmbedder()
QUERIES = ["giao hàng khi nào", "hoàn tiền trên ngưỡng", "hóa đơn INV-2026-0451", "khiếu nại giao trễ", "kế hoạch nhân sự", "đơn BM-1002"]
ACTORS = [
    Actor(subject="v", role="visitor"),
    Actor(subject="a", role="customer", customer_id="c001"),
    Actor(subject="b", role="customer", customer_id="c002"),
    Actor(subject="n", role="customer", customer_id=None),
    Actor(subject="s", role="support"),
    Actor(subject="f", role="finance"),
    Actor(subject="m", role="manager"),
]


@pytest.fixture(scope="module")
def stores():
    out = {"memory": MemorySearchStore(DOCS, EMB)}
    if OWNER and APP:
        with psycopg.connect(OWNER) as c:
            c.execute("DELETE FROM chunks")
        ingest(OWNER, DOCS, EMB)
        out["postgres"] = PostgresSearchStore(APP, max_size=2)
    yield out
    if "postgres" in out:
        out["postgres"].close()


@pytest.fixture(params=["memory", pytest.param("postgres", marks=needs_pg)])
def store(request, stores):
    return stores[request.param]


def visible_doc_ids(actor):
    return {d.doc_id for d in DOCS if is_visible(actor, d.allowed_roles, d.owner_customer_id)}


@pytest.mark.parametrize("actor", ACTORS, ids=lambda a: f"{a.role}-{a.customer_id}")
def test_hits_never_include_a_chunk_the_actor_may_not_see(store, actor):
    allowed = visible_doc_ids(actor)
    for q in QUERIES:
        hits = store.search(actor, EMB.model_id, EMB.embed_query(q), 10)
        assert {h.doc_id for h in hits} <= allowed, (q, actor)


def test_customer_cannot_find_another_customers_invoice_even_by_quoting_it(store):
    other = next(d for d in DOCS if d.doc_id == "invoice-c002-inv02")
    hits = store.search(ACTORS[1], EMB.model_id, EMB.embed_query(other.body), 10)
    assert "invoice-c002-inv02" not in {h.doc_id for h in hits}
    mine = store.search(ACTORS[2], EMB.model_id, EMB.embed_query(other.body), 10)
    assert mine and mine[0].doc_id == "invoice-c002-inv02"  # the owner finds it first


def test_permission_applies_before_ranking_so_top_k_is_filled_from_permitted_chunks(store):
    visitor = ACTORS[0]
    restricted = next(d for d in DOCS if d.doc_id == "mgmt-staffing-plan")
    assert not is_visible(visitor, restricted.allowed_roles, restricted.owner_customer_id)
    hits = store.search(visitor, EMB.model_id, EMB.embed_query(restricted.body), 3)
    assert len(hits) == 3  # a post-filter on the global top-3 could have returned fewer
    assert all(h.doc_id != "mgmt-staffing-plan" for h in hits)


def test_customer_without_customer_id_sees_only_non_owned_documents(store):
    docs = {h.doc_id for q in QUERIES for h in store.search(ACTORS[3], EMB.model_id, EMB.embed_query(q), 10)}
    assert not any(d.startswith(("order-", "invoice-", "ticket-")) for d in docs)


def test_relevant_public_document_ranks_first_for_a_visitor(store):
    top = store.search(ACTORS[0], EMB.model_id, EMB.embed_query("giao hàng Thứ Hai và Thứ Năm khung giờ"), 3)
    assert top[0].doc_id in {"pub-faq-ordering", "pub-delivery-areas"}


def test_query_embedded_with_a_different_model_matches_nothing(store):
    assert store.search(ACTORS[6], "some-other-model", EMB.embed_query("giao hàng"), 5) == []


@needs_pg
@pytest.mark.parametrize("actor", ACTORS, ids=lambda a: f"{a.role}-{a.customer_id}")
def test_postgres_matches_the_memory_reference(stores, actor):
    for q in QUERIES:
        v = EMB.embed_query(q)
        mem = stores["memory"].search(actor, EMB.model_id, v, 5)
        pg = stores["postgres"].search(actor, EMB.model_id, v, 5)
        assert [h.chunk_id for h in pg] == [h.chunk_id for h in mem]
        assert [round(h.score, 5) for h in pg] == [round(h.score, 5) for h in mem]


@needs_pg
def test_startup_guard_covers_the_chunks_table(stores):
    stores["postgres"].assert_least_privilege()
    owner_store = PostgresSearchStore(OWNER, max_size=1)
    try:
        with pytest.raises(RuntimeError, match="refusing to start"):
            owner_store.assert_least_privilege()
    finally:
        owner_store.close()


@needs_pg
def test_app_role_cannot_read_chunks_without_an_actor_or_write_them():
    with psycopg.connect(APP) as c:
        assert c.execute("SELECT count(*) FROM chunks").fetchone()[0] == 0  # fail closed
        c.rollback()
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            c.execute("DELETE FROM chunks")


@needs_pg
class TestIngest:
    def count(self):
        with psycopg.connect(OWNER) as c:
            return c.execute("SELECT count(*) FROM chunks").fetchone()[0]

    def test_rerun_embeds_nothing_and_changes_nothing(self, stores):
        res = ingest(OWNER, DOCS, EMB)
        assert res["embedded"] == 0 and res["deleted"] == 0 and res["chunks"] == self.count()

    def test_access_change_is_applied_without_re_embedding(self, stores):
        doc = next(d for d in DOCS if d.doc_id == "pub-faq-ordering")
        changed = [d if d is not doc else type(d)(**{**d.__dict__, "allowed_roles": ("manager",)}) for d in DOCS]
        try:
            assert ingest(OWNER, changed, EMB)["embedded"] == 0
            hits = stores["postgres"].search(ACTORS[0], EMB.model_id, EMB.embed_query(doc.body), 10)
            assert "pub-faq-ordering" not in {h.doc_id for h in hits}
        finally:
            ingest(OWNER, DOCS, EMB)
        hits = stores["postgres"].search(ACTORS[0], EMB.model_id, EMB.embed_query(doc.body), 10)
        assert hits[0].doc_id == "pub-faq-ordering"

    def test_removed_document_is_deleted_and_provider_failure_leaves_index_untouched(self, stores):
        before = self.count()

        class Boom(HashEmbedder):
            def embed_documents(self, items):
                raise EmbeddingUnavailable("down")

        edited = [type(d)(**{**d.__dict__, "body": d.body + " thêm"}) for d in DOCS]
        with pytest.raises(EmbeddingUnavailable):
            ingest(OWNER, edited, Boom())
        assert self.count() == before
        try:
            res = ingest(OWNER, [d for d in DOCS if d.doc_id != "pub-faq-ordering"], EMB)
            assert res["deleted"] == len(chunk_doc(next(d for d in DOCS if d.doc_id == "pub-faq-ordering")))
        finally:
            ingest(OWNER, DOCS, EMB)
        assert self.count() == before


def test_gemini_rest_embedder_sends_one_request_per_text_and_checks_dimensions():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.headers["x-goog-api-key"], json.loads(request.content)))
        return httpx.Response(200, json={"embedding": {"values": [0.1, 0.2, 0.3, 0.4]}})

    emb = GeminiRestEmbedder("test-key", dim=4, client=httpx.Client(base_url="https://x.test", transport=httpx.MockTransport(handler)))
    vecs = emb.embed_documents([("T1", "a"), ("T2", "b")])
    assert len(vecs) == 2 and len(seen) == 2  # never one batched/pooled call
    assert seen[0][0].endswith(":embedContent") and seen[0][2]["outputDimensionality"] == 4
    assert seen[0][2]["content"]["parts"][0]["text"].startswith("title: T1 | text: a")
    assert emb.model_id == "gemini-embedding-2@4"
    assert "search result" in (emb.embed_query("hỏi") and seen[-1][2]["content"]["parts"][0]["text"])


@pytest.mark.parametrize("response", [
    httpx.Response(429, text="quota exceeded for key SECRET-KEY"),
    httpx.Response(200, json={"embedding": {"values": [1.0, 2.0]}}),  # wrong dimension
    httpx.Response(200, json={"oops": 1}),
])
def test_gemini_rest_embedder_failures_become_embedding_unavailable_without_leaking(response):
    emb = GeminiRestEmbedder("SECRET-KEY", dim=4, client=httpx.Client(base_url="https://x.test", transport=httpx.MockTransport(lambda r: response)))
    with pytest.raises(EmbeddingUnavailable) as err:
        emb.embed_query("x")
    assert "SECRET-KEY" not in str(err.value)


class FakeVerifier:
    def actor_for(self, token):
        if token == "bad":
            raise AuthenticationError("bad")
        role, _, cid = token.partition(":")
        return Actor(subject=token, role=role, customer_id=cid or None)


@pytest.fixture
def client():
    return TestClient(create_app(
        token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS),
        search_store=MemorySearchStore(DOCS, EMB), embedder=EMB,
    ))


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_search_route_requires_a_token_and_validates_input(client):
    assert client.post("/v1/search", json={"query": "x"}).status_code == 401
    assert client.post("/v1/search", json={"query": "x"}, headers=auth("bad")).status_code == 401
    assert client.post("/v1/search", json={"query": ""}, headers=auth("visitor:")).status_code == 422
    assert client.post("/v1/search", json={"query": "x", "top_k": 99}, headers=auth("visitor:")).status_code == 422


def test_search_route_returns_only_permitted_chunks(client):
    r = client.post("/v1/search", json={"query": "hóa đơn INV-2026-0451 tổng tiền", "top_k": 10}, headers=auth("customer:c002"))
    assert r.status_code == 200
    ids = {h["doc_id"] for h in r.json()["results"]}
    assert "invoice-c001-inv01" not in ids
    r = client.post("/v1/search", json={"query": "kế hoạch nhân sự quản lý", "top_k": 10}, headers=auth("visitor:"))
    assert all(h["doc_id"] != "mgmt-staffing-plan" for h in r.json()["results"])


def test_search_route_reports_embedder_outage_as_503():
    class Down(HashEmbedder):
        def embed_query(self, text):
            raise EmbeddingUnavailable("down")

    app = create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS),
                     search_store=MemorySearchStore(DOCS, EMB), embedder=Down())
    r = TestClient(app).post("/v1/search", json={"query": "x"}, headers=auth("manager:"))
    assert (r.status_code, r.json()["detail"]) == (503, "embedding_unavailable")
