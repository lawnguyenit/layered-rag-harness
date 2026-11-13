"""End-to-end check: real Keycloak token -> harness client -> host API -> Postgres RLS.

Needs a running Keycloak (dev mode), the migrated+seeded host API, and these env vars:
  KC_URL (e.g. http://127.0.0.1:18080)   KC_ADMIN_PASSWORD   HOST_URL (e.g. http://127.0.0.1:8020)
Provisions a throwaway realm `bepmay-e2e` with synthetic users, then asserts what each user can read.
Test-only shortcuts, not production patterns: password grant on the client, random user passwords that
are never printed, an audience mapper that puts the host audience in the same token the harness uses.
Run from the repo root: `uv run python scripts/e2e_host_keycloak.py`.
"""
from __future__ import annotations

import os
import sys

import httpx

from kc_dev_realm import USERS, admin_client, make_passwords, provision, token_for
from lrh.business import HostAuthError, HostHttpBusinessLookup

HOST = os.environ["HOST_URL"].rstrip("/")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Vietnamese queries are printed; Windows consoles default to cp1252
    passwords = make_passwords()
    with admin_client() as admin:
        provision(admin, passwords)  # idempotent; resets every password to this run's value

    tokens = {name: token_for("bepmay-web", name, passwords[name]) for name in USERS}
    lookup = HostHttpBusinessLookup(HOST)
    # (user, kind, ref, expected): True = record returned, False = None (denied and missing look the same)
    cases = [
        ("alice", "order", "BM-1001", True), ("alice", "order", "BM-1002", False),
        ("alice", "invoice", "INV-2026-0451", True), ("alice", "ticket", "T01", True), ("alice", "ticket", "T02", False),
        ("bob", "order", "BM-1001", False), ("bob", "order", "BM-1002", True),
        ("sam", "order", "BM-1001", True), ("sam", "ticket", "T01", True), ("sam", "invoice", "INV-2026-0451", False),
        ("fin", "invoice", "INV-2026-0451", True), ("fin", "ticket", "T01", False),
        ("mia", "invoice", "INV-2026-0451", True), ("mia", "order", "BM-9999", False),
    ]
    failures = []
    for user, kind, ref, expected in cases:
        got = lookup.get(tokens[user], kind, ref) is not None
        flag = "ok " if got == expected else "FAIL"
        print(f"{flag} {user:5} {kind:8} {ref:14} expected={'record' if expected else 'none  '} got={'record' if got else 'none'}")
        if got != expected:
            failures.append((user, kind, ref))

    def rejected(label: str, token: str) -> None:
        try:
            lookup.get(token, "order", "BM-1001")
        except HostAuthError:
            print(f"ok  {label}: host answered 401")
        else:
            print(f"FAIL {label}: host accepted it")
            failures.append((label,))

    def search(user: str, query: str) -> set[str]:
        r = httpx.post(f"{HOST}/v1/search", json={"query": query, "top_k": 10}, headers={"Authorization": f"Bearer {tokens[user]}"}, timeout=15)
        r.raise_for_status()
        return {h["doc_id"] for h in r.json()["results"]}

    # (user, query, doc that must / must not appear)
    search_cases = [
        ("alice", "hóa đơn INV-2026-0451", "invoice-c001-inv01", True),
        ("bob", "hóa đơn INV-2026-0451", "invoice-c001-inv01", False),
        ("bob", "hóa đơn tổng tiền thanh toán", "invoice-c002-inv02", True),
        ("sam", "kế hoạch nhân sự", "mgmt-staffing-plan", False),
        ("mia", "kế hoạch nhân sự", "mgmt-staffing-plan", True),
    ]
    for user, query, doc, expected in search_cases:
        got = doc in search(user, query)
        flag = "ok " if got == expected else "FAIL"
        print(f"{flag} search {user:5} {query[:28]:28} {doc:20} expected={'seen' if expected else 'hidden'} got={'seen' if got else 'hidden'}")
        if got != expected:
            failures.append((user, query, doc))
    anon = httpx.post(f"{HOST}/v1/search", json={"query": "x"})
    print(f"{'ok ' if anon.status_code == 401 else 'FAIL'} search without token: {anon.status_code}")
    if anon.status_code != 401:
        failures.append(("search-anon",))

    rejected("token for another API (aud=lrh-api)", token_for("other-web", "alice", passwords["alice"]))
    rejected("tampered signature", tokens["alice"][:-4] + ("AAAA" if not tokens["alice"].endswith("AAAA") else "BBBB"))
    rejected("garbage token", "not-a-jwt")
    total = len(cases) + len(search_cases) + 4
    print(f"\n{total - len(failures)}/{total} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
