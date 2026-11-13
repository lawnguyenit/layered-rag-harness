"""H2 acceptance tests: row-level security enforced by the database, not by the query text.

Written first (red), then made green by migration 0002 (policy + app role).
They deliberately run *raw* SQL with no WHERE clause as the app role: if the database is
doing the filtering, a forgotten condition in a future query cannot leak rows.

Needs two connection URLs (both against a migrated and seeded database):
  HOST_TEST_DATABASE_URL      table owner / superuser (setup + the "owner bypasses" control)
  HOST_TEST_APP_DATABASE_URL  the non-bypass app role `bepmay_app` (password set out of band)
The actor convention the policy must read is fixed here so the adapter and policy agree:
  SET LOCAL app.role = '<role>';  SET LOCAL app.customer_id = '<id or empty>'
"""
import os
from pathlib import Path

import psycopg
import pytest

from bepmay_host.corpus import load_corpus
from bepmay_host.seed import seed_records

OWNER_URL = os.getenv("HOST_TEST_DATABASE_URL", "").strip()
APP_URL = os.getenv("HOST_TEST_APP_DATABASE_URL", "").strip()
CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"

pytestmark = pytest.mark.skipif(
    not (OWNER_URL and APP_URL), reason="HOST_TEST_DATABASE_URL and HOST_TEST_APP_DATABASE_URL not set"
)


@pytest.fixture(scope="module", autouse=True)
def seeded():
    seed_records(OWNER_URL, load_corpus(CORPUS))


def as_actor(conn, role, customer_id=""):
    """Open a transaction on conn and set the actor, the way the adapter must."""
    conn.execute("SELECT set_config('app.role', %s, true)", (role,))
    conn.execute("SELECT set_config('app.customer_id', %s, true)", (customer_id,))


@pytest.fixture
def app():
    with psycopg.connect(APP_URL) as conn:
        yield conn


def refs(conn, sql="SELECT ref_id FROM records"):
    return {r[0] for r in conn.execute(sql).fetchall()}


def test_app_role_cannot_bypass_rls():
    with psycopg.connect(APP_URL) as conn:
        sup, bypass = conn.execute(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
        owns = conn.execute("SELECT count(*) FROM pg_tables WHERE tablename = 'records' AND tableowner = current_user").fetchone()[0]
    assert (sup, bypass, owns) == (False, False, 0)


def test_table_has_rls_enabled_and_forced():
    with psycopg.connect(OWNER_URL) as conn:
        enabled, forced = conn.execute(
            "SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = 'records'"
        ).fetchone()
    assert enabled and forced


def test_no_actor_set_sees_nothing(app):
    assert refs(app) == set()  # fail closed: unset settings must not mean "everyone"


def test_unknown_role_sees_nothing(app):
    as_actor(app, "root")
    assert refs(app) == set()


def test_customer_raw_select_without_where_sees_only_own_rows(app):
    as_actor(app, "customer", "c001")
    got = refs(app)
    assert {"BM-1001", "T01", "INV-2026-0451"} <= got
    assert "BM-1002" not in got and "T02" not in got


def test_guessing_another_customers_id_returns_zero_rows(app):
    as_actor(app, "customer", "c001")
    assert app.execute("SELECT * FROM records WHERE ref_id = 'BM-1002'").fetchall() == []


def test_customer_with_empty_customer_id_sees_nothing(app):
    as_actor(app, "customer", "")
    assert refs(app) == set()


def test_visitor_sees_nothing(app):
    as_actor(app, "visitor")
    assert refs(app) == set()


def test_internal_roles_follow_the_matrix(app):
    as_actor(app, "support")
    got = refs(app)
    assert "BM-1001" in got and "T01" in got and "INV-2026-0451" not in got
    as_actor(app, "finance")
    got = refs(app)
    assert "INV-2026-0451" in got and "T01" not in got


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE records SET title = 'x'",
        "DELETE FROM records",
        "INSERT INTO records VALUES ('d','order','BM-9','t','b','{manager}',NULL)",
    ],
)
def test_app_role_cannot_write_even_as_manager(app, sql):
    as_actor(app, "manager")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute(sql)


def test_actor_does_not_leak_across_transactions():
    with psycopg.connect(APP_URL) as conn:
        as_actor(conn, "manager")
        assert refs(conn)  # inside the transaction
        conn.commit()
        assert refs(conn) == set()  # next transaction on the same connection: settings gone


def test_control_table_owner_bypasses_without_force_proves_why_role_matters():
    """Documented control: the owner/superuser connection sees every row. This is why the
    app must not connect as the owner; the assertion pins that the owner URL is not the app URL."""
    with psycopg.connect(OWNER_URL) as owner:
        assert len(refs(owner)) >= 8
    assert OWNER_URL != APP_URL


def test_startup_guard_accepts_the_app_role():
    from bepmay_host.postgres_store import PostgresBusinessStore
    store = PostgresBusinessStore(APP_URL, max_size=1)
    try:
        store.assert_least_privilege()
    finally:
        store.close()


def test_startup_guard_refuses_the_owner_role():
    from bepmay_host.postgres_store import PostgresBusinessStore
    store = PostgresBusinessStore(OWNER_URL, max_size=1)
    try:
        with pytest.raises(RuntimeError, match="refusing to start"):
            store.assert_least_privilege()
    finally:
        store.close()

