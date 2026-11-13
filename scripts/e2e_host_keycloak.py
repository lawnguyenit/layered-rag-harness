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
import secrets
import sys

import httpx

from lrh.business import HostAuthError, HostHttpBusinessLookup

KC = os.environ["KC_URL"].rstrip("/")
HOST = os.environ["HOST_URL"].rstrip("/")
REALM = "bepmay-e2e"
HOST_AUD = "bepmay-host"
ROLES = ["visitor", "customer", "support", "finance", "manager"]
USERS = {  # username -> (role, customer_id)
    "alice": ("customer", "c001"),
    "bob": ("customer", "c002"),
    "sam": ("support", None),
    "fin": ("finance", None),
    "mia": ("manager", None),
}


def admin_client() -> httpx.Client:
    token = httpx.post(
        f"{KC}/realms/master/protocol/openid-connect/token",
        data={"grant_type": "password", "client_id": "admin-cli", "username": "admin",
              "password": os.environ["KC_ADMIN_PASSWORD"]},
    ).raise_for_status().json()["access_token"]
    return httpx.Client(base_url=f"{KC}/admin/realms", headers={"Authorization": f"Bearer {token}"}, timeout=15)


def ok(response: httpx.Response) -> None:
    if response.status_code not in (200, 201, 204, 409):
        raise SystemExit(f"Keycloak admin call failed: {response.request.method} {response.request.url.path} {response.status_code} {response.text[:200]}")


def provision(admin: httpx.Client, passwords: dict[str, str]) -> None:
    ok(admin.post("", json={"realm": REALM, "enabled": True}))
    profile = admin.get(f"/{REALM}/users/profile").json()
    profile["unmanagedAttributePolicy"] = "ENABLED"  # lets the customer_id attribute reach the token mapper
    ok(admin.put(f"/{REALM}/users/profile", json=profile))
    for role in ROLES:
        ok(admin.post(f"/{REALM}/roles", json={"name": role}))
    # APIs are registered as clients (resource servers) so the IdP will issue tokens addressed to them.
    for api in (HOST_AUD, "lrh-api"):
        ok(admin.post(f"/{REALM}/clients", json={"clientId": api, "bearerOnly": True, "protocol": "openid-connect"}))
    for client_id, audience in (("bepmay-web", HOST_AUD), ("other-web", "lrh-api")):
        ok(admin.post(f"/{REALM}/clients", json={
            "clientId": client_id, "publicClient": True, "directAccessGrantsEnabled": True,
            "standardFlowEnabled": False, "protocol": "openid-connect",
            "protocolMappers": [
                {"name": "aud", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
                 "config": {"included.client.audience": audience, "access.token.claim": "true", "id.token.claim": "false"}},
                {"name": "customer_id", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-attribute-mapper",
                 "config": {"user.attribute": "customer_id", "claim.name": "customer_id", "jsonType.label": "String",
                            "access.token.claim": "true", "id.token.claim": "false", "userinfo.token.claim": "false"}},
            ],
        }))
    for name, (role, cid) in USERS.items():
        user = {"username": name, "enabled": True, "emailVerified": True, "email": f"{name}@example.test",
                "firstName": name, "lastName": "Test", "attributes": {"customer_id": [cid]} if cid else {},
                "credentials": [{"type": "password", "value": passwords[name], "temporary": False}]}
        ok(admin.post(f"/{REALM}/users", json=user))
        uid = admin.get(f"/{REALM}/users", params={"username": name, "exact": "true"}).json()[0]["id"]
        rep = admin.get(f"/{REALM}/roles/{role}").json()
        ok(admin.post(f"/{REALM}/users/{uid}/role-mappings/realm", json=[rep]))


def token_for(client_id: str, username: str, password: str) -> str:
    r = httpx.post(f"{KC}/realms/{REALM}/protocol/openid-connect/token",
                   data={"grant_type": "password", "client_id": client_id, "username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    passwords = {name: secrets.token_urlsafe(18) for name in USERS}
    with admin_client() as admin:
        provision(admin, passwords)
    # Users already exist on a rerun with older random passwords: reset to this run's value.
    with admin_client() as admin:
        for name in USERS:
            uid = admin.get(f"/{REALM}/users", params={"username": name, "exact": "true"}).json()[0]["id"]
            ok(admin.put(f"/{REALM}/users/{uid}/reset-password", json={"type": "password", "value": passwords[name], "temporary": False}))

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

    rejected("token for another API (aud=lrh-api)", token_for("other-web", "alice", passwords["alice"]))
    rejected("tampered signature", tokens["alice"][:-4] + ("AAAA" if not tokens["alice"].endswith("AAAA") else "BBBB"))
    rejected("garbage token", "not-a-jwt")
    print(f"\n{len(cases) + 3 - len(failures)}/{len(cases) + 3} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
