"""Contract tests for BusinessStore adapters, including the "actor without access" cases.

The Postgres adapter runs only when both URLs are set against a migrated database: the table owner
(HOST_TEST_DATABASE_URL, used to seed) and the non-bypass app role (HOST_TEST_APP_DATABASE_URL, used by
the adapter). Authorisation is row-level security, so the adapter must be tested as the app role.
"""
import os
from pathlib import Path

import pytest

from bepmay_host.corpus import load_corpus
from bepmay_host.memory_store import MemoryBusinessStore
from bepmay_host.postgres_store import PostgresBusinessStore
from bepmay_host.seed import seed_records
from bepmay_host.access import Actor

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"
DB_URL = os.getenv("HOST_TEST_DATABASE_URL", "").strip()
APP_URL = os.getenv("HOST_TEST_APP_DATABASE_URL", "").strip()


@pytest.fixture(
    params=["memory", pytest.param("postgres", marks=pytest.mark.skipif(not (DB_URL and APP_URL), reason="HOST_TEST_DATABASE_URL / HOST_TEST_APP_DATABASE_URL not set"))]
)
def store(request):
    docs = load_corpus(CORPUS)
    if request.param == "memory":
        yield MemoryBusinessStore(docs)
        return
    seed_records(DB_URL, docs)
    pg = PostgresBusinessStore(APP_URL, max_size=2)
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


def listed(store, a, kind, limit=50):
    return [r.ref_id for r in store.list(a, kind, limit)]


def test_list_shows_a_customer_only_their_own_records(store):
    assert listed(store, actor("customer", "c001"), "order") == ["BM-1001"]
    assert listed(store, actor("customer", "c002"), "order") == ["BM-1002"]
    assert listed(store, actor("customer", "c001"), "invoice") == ["INV-2026-0451"]
    assert listed(store, actor("customer", "c001"), "ticket") == ["T01"]


def test_list_is_empty_for_visitor_and_for_a_customer_without_an_id(store):
    for who in (actor("visitor"), actor("customer", None)):
        assert all(listed(store, who, k) == [] for k in ("order", "ticket", "invoice"))


def test_list_matches_the_role_matrix_and_the_python_rule_for_every_actor(store):
    docs = [d for d in load_corpus(CORPUS) if d.ref_id]
    from bepmay_host.access import is_visible
    for who in (actor("customer", "c001"), actor("customer", "c002"), actor("customer", "c003"), actor("support"),
                actor("finance"), actor("manager"), actor("visitor"), actor("customer", None)):
        for kind in ("order", "ticket", "invoice"):
            expected = sorted(d.ref_id for d in docs if d.kind == kind and is_visible(who, d.allowed_roles, d.owner_customer_id))
            assert listed(store, who, kind) == expected, (who, kind)


def test_list_and_get_agree_for_every_actor_and_record(store):
    """Whatever is listed can be opened, and nothing that is not listed can be: the two views never disagree."""
    docs = [d for d in load_corpus(CORPUS) if d.ref_id]
    for who in (actor("customer", "c001"), actor("customer", "c002"), actor("support"), actor("finance"), actor("manager"), actor("visitor")):
        for d in docs:
            assert (d.ref_id in listed(store, who, d.kind)) == (store.get(who, d.kind, d.ref_id) is not None)


def test_list_is_ordered_limited_and_carries_no_body(store):
    manager = actor("manager")
    assert listed(store, manager, "order") == sorted(listed(store, manager, "order"))
    assert len(listed(store, manager, "order", limit=2)) == 2
    first = store.list(manager, "order", 1)[0]
    assert set(vars(first)) == {"kind", "ref_id", "title"}

