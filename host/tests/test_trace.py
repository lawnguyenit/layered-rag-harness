"""Request trace: one structured line per request, no secrets, no query text, same outcome for denied and missing."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bepmay_host.access import Actor
from bepmay_host.api import create_app
from bepmay_host.auth import AuthenticationError
from bepmay_host.corpus import load_corpus
from bepmay_host.embeddings import HashEmbedder
from bepmay_host.memory_store import MemoryBusinessStore
from bepmay_host.search_store import MemorySearchStore
from bepmay_host.trace import TraceRecorder

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"
DOCS = load_corpus(CORPUS)


class FakeVerifier:
    def actor_for(self, token):
        if token == "bad":
            raise AuthenticationError("bad")
        role, _, cid = token.partition(":")
        return Actor(subject=token, role=role, customer_id=cid or None)


class Capture(TraceRecorder):
    def __init__(self):
        super().__init__(None)
        self.lines: list[dict] = []

    def emit(self, record):
        self.lines.append(record)


@pytest.fixture
def setup():
    cap = Capture()
    app = create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS),
                     search_store=MemorySearchStore(DOCS, HashEmbedder()), embedder=HashEmbedder(), trace=cap)
    return TestClient(app), cap


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def test_lookup_line_has_role_route_outcome_and_matching_request_id(setup):
    client, cap = setup
    r = client.get("/v1/orders/BM-1001", headers=auth("customer:c001"))
    line = cap.lines[-1]
    assert r.headers["x-request-id"] == line["request_id"]
    assert (line["route"], line["status"], line["outcome"], line["actor_role"], line["kind"], line["ref"]) == (
        "/v1/orders/{ref_id}", 200, "ok", "customer", "order", "BM-1001")
    assert line["latency_ms"] >= 0 and len(line["actor"]) == 8


def test_denied_and_nonexistent_records_trace_identically(setup):
    client, cap = setup
    client.get("/v1/orders/BM-1002", headers=auth("customer:c001"))  # exists, not theirs
    client.get("/v1/orders/BM-9999", headers=auth("customer:c001"))  # does not exist
    a, b = cap.lines[-2:]
    assert (a["status"], a["outcome"]) == (b["status"], b["outcome"]) == (404, "not_found")


def test_unauthenticated_and_invalid_token_are_distinguished(setup):
    client, cap = setup
    client.get("/v1/orders/BM-1001")
    assert cap.lines[-1]["outcome"] == "unauthenticated" and "actor_role" not in cap.lines[-1]
    client.get("/v1/orders/BM-1001", headers=auth("bad"))
    assert cap.lines[-1]["outcome"] == "invalid_token"


def test_malformed_reference_is_not_echoed_into_the_log(setup):
    client, cap = setup
    client.get("/v1/orders/BM-1001%27%20OR%201=1", headers=auth("manager:"))
    assert cap.lines[-1]["ref"] is None and "OR" not in json.dumps(cap.lines[-1])


def test_search_line_records_counts_but_never_the_query_or_the_token(setup):
    client, cap = setup
    secret_query = "một câu hỏi riêng tư về lương nhân viên"
    client.post("/v1/search", json={"query": secret_query, "top_k": 3}, headers=auth("finance:"))
    line = cap.lines[-1]
    assert (line["kind"], line["top_k"], line["outcome"]) == ("search", 3, "ok") and line["result_count"] == 3
    blob = json.dumps(line, ensure_ascii=False)
    assert secret_query not in blob and "riêng tư" not in blob and "finance:" not in blob


def test_embedding_outage_is_its_own_outcome(setup):
    client, cap = setup
    from bepmay_host.embeddings import EmbeddingUnavailable

    class Down(HashEmbedder):
        def embed_query(self, text):
            raise EmbeddingUnavailable("down")

    app = create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS),
                     search_store=MemorySearchStore(DOCS, HashEmbedder()), embedder=Down(), trace=cap)
    TestClient(app).post("/v1/search", json={"query": "x"}, headers=auth("manager:"))
    assert (cap.lines[-1]["status"], cap.lines[-1]["outcome"]) == (503, "embedding_unavailable")


def test_client_supplied_request_id_is_kept_only_if_well_formed(setup):
    client, cap = setup
    client.get("/healthz", headers={"x-request-id": "harness-req-1234"})
    assert cap.lines[-1]["request_id"] == "harness-req-1234"
    client.get("/healthz", headers={"x-request-id": "bad id\twith junk"})
    assert cap.lines[-1]["request_id"] != "bad id\twith junk" and len(cap.lines[-1]["request_id"]) == 32


def test_trace_file_gets_one_json_line_per_request(tmp_path):
    path = tmp_path / "trace.jsonl"
    app = create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS), trace=TraceRecorder(str(path)))
    c = TestClient(app)
    c.get("/healthz"); c.get("/v1/tickets/T01", headers=auth("support:"))
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert [x["route"] for x in lines] == ["/healthz", "/v1/tickets/{ref_id}"] and all("ts" in x for x in lines)


def test_cors_only_for_configured_origins():
    app = create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(DOCS), cors_origins=["http://localhost:5173"])
    c = TestClient(app)
    ok = c.options("/v1/orders/BM-1001", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
                                                    "Access-Control-Request-Headers": "authorization"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = c.options("/v1/orders/BM-1001", headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in other.headers
