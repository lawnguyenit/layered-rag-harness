"""Contract tests for BusinessStore adapters, including the "actor without access" cases.

The Postgres adapter runs only when HOST_TEST_DATABASE_URL points at a migrated database
(`alembic upgrade head`); it is seeded from the synthetic corpus by the fixture.
"""
import os
from pathlib import Path

import pytest

from bepmay_host.corpus import load_corpus
from bepmay_host.memory_store import MemoryBusinessStore
from bepmay_host.postgres_store import PostgresBusinessStore
from bepmay_host.access import Actor

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"
DB_URL = os.getenv("HOST_TEST_DATABASE_URL", "").strip()


@pytest.fixture(
    params=["memory", pytest.param("postgres", marks=pytest.mark.skipif(not DB_URL, reason="HOST_TEST_DATABASE_URL not set"))]
)
def store(request):
    docs = load_corpus(CORPUS)
    if request.param == "memory":
        yield MemoryBusinessStore(docs)
        return
    pg = PostgresBusinessStore(DB_URL, max_size=2)
    pg.seed(docs)
    yield pg
    pg.close()


def actor(role, customer_id=None):
    return Actor(subject=f"{role}-{customer_id}", role=role, customer_id=customer_id)


def test_owner_customer_reads_own_records(store):
    a = actor("customer", "c001")
    assert store.get(a, "order", "BM-1001").owner_customer_id == "c001"
    assert store.get(a, "invoice", "INV-2026-0451") is not None
    assert store.get(a, "ticket", "T01") is not None


def test_customer_cannot_read_other_customers_records(store):
    a = actor("customer", "c001")
    assert store.get(a, "order", "BM-1002") is None  # belongs to c002
    assert store.get(a, "ticket", "T02") is None


def test_denied_and_nonexistent_are_indistinguishable(store):
    a = actor("customer", "c001")
    assert store.get(a, "order", "BM-1002") == store.get(a, "order", "BM-9999") is None


def test_customer_without_customer_id_sees_nothing(store):
    assert store.get(actor("customer", None), "order", "BM-1001") is None


def test_visitor_sees_no_business_records(store):
    v = actor("visitor")
    assert store.get(v, "order", "BM-1001") is None
    assert store.get(v, "invoice", "INV-2026-0451") is None


@pytest.mark.parametrize(
    "role,kind,ref,visible",
    [
        ("support", "order", "BM-1001", True),
        ("support", "ticket", "T01", True),
        ("support", "invoice", "INV-2026-0451", False),
        ("finance", "invoice", "INV-2026-0451", True),
        ("finance", "order", "BM-1001", True),
        ("finance", "ticket", "T01", False),
        ("manager", "order", "BM-1001", True),
        ("manager", "ticket", "T01", True),
        ("manager", "invoice", "INV-2026-0451", True),
    ],
)
def test_internal_roles_follow_the_matrix(store, role, kind, ref, visible):
    assert (store.get(actor(role), kind, ref) is not None) is visible


def test_wrong_kind_for_reference_returns_none(store):
    assert store.get(actor("manager"), "invoice", "BM-1001") is None
