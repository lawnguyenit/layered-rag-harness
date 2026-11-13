"""Throwaway Keycloak realm for local end-to-end work: synthetic users, the host API registered as a resource
server, a direct-grant client for scripts and a public PKCE client for the browser UI.

Test-only shortcuts, not production patterns: direct access grants on `bepmay-web`, a shared dev password when
DEV_USER_PASSWORD is set (so a person or a browser test can log in), an audience mapper that puts the host audience
in the same token the harness uses. Never printed: the passwords.
"""
from __future__ import annotations

import os
import secrets

import httpx

KC = os.environ.get("KC_URL", "").rstrip("/")
REALM = "bepmay-e2e"
HOST_AUD = "bepmay-host"
HARNESS_CLIENT = "lrh-api"  # audience of tokens meant for the harness; also the client that exchanges them
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
        raise SystemExit(f"Keycloak admin call failed: {response.request.method} {response.request.url.path} "
                         f"{response.status_code} {response.text[:200]}")


def _mappers(audience: str) -> list[dict]:
    return [
        {"name": "aud", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
         "config": {"included.client.audience": audience, "access.token.claim": "true", "id.token.claim": "false"}},
        {"name": "customer_id", "protocol": "openid-connect", "protocolMapper": "oidc-usermodel-attribute-mapper",
         "config": {"user.attribute": "customer_id", "claim.name": "customer_id", "jsonType.label": "String",
                    "access.token.claim": "true", "id.token.claim": "false", "userinfo.token.claim": "false"}},
    ]


def provision(admin: httpx.Client, passwords: dict[str, str], spa_origin: str = "http://localhost:5173") -> None:
    """Idempotent: 409 (already exists) is accepted everywhere. Passwords are (re)set on every run."""
    ok(admin.post("", json={"realm": REALM, "enabled": True}))
    profile = admin.get(f"/{REALM}/users/profile").json()
    profile["unmanagedAttributePolicy"] = "ENABLED"  # lets the customer_id attribute reach the token mapper
    ok(admin.put(f"/{REALM}/users/profile", json=profile))
    for role in ROLES:
        ok(admin.post(f"/{REALM}/roles", json={"name": role}))
    # APIs are registered as clients (resource servers): Keycloak only issues a custom audience for a known client.
    ok(admin.post(f"/{REALM}/clients", json={"clientId": HOST_AUD, "bearerOnly": True, "protocol": "openid-connect"}))
    # The harness API is a confidential client allowed to exchange a user token addressed to it for one addressed to
    # the host (RFC 8693 standard token exchange). It needs the same claim mapper so the exchanged token keeps customer_id.
    ok(admin.post(f"/{REALM}/clients", json={
        "clientId": HARNESS_CLIENT, "publicClient": False, "standardFlowEnabled": False, "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False, "protocol": "openid-connect",
        "attributes": {"standard.token.exchange.enabled": "true"},
        "protocolMappers": _mappers(HOST_AUD)}))  # the aud mapper declares the host audience as available to this client
    ok(admin.post(f"/{REALM}/clients", json={
        "clientId": "bepmay-web", "publicClient": True, "directAccessGrantsEnabled": True, "standardFlowEnabled": False,
        "protocol": "openid-connect", "protocolMappers": _mappers(HOST_AUD)}))
    ok(admin.post(f"/{REALM}/clients", json={
        "clientId": "other-web", "publicClient": True, "directAccessGrantsEnabled": True, "standardFlowEnabled": False,
        "protocol": "openid-connect", "protocolMappers": _mappers("lrh-api")}))
    ok(admin.post(f"/{REALM}/clients", json={
        "clientId": "bepmay-spa", "publicClient": True, "standardFlowEnabled": True, "directAccessGrantsEnabled": False,
        "protocol": "openid-connect", "redirectUris": [f"{spa_origin}/*"], "webOrigins": [spa_origin],
        "attributes": {"pkce.code.challenge.method": "S256", "post.logout.redirect.uris": f"{spa_origin}/*"},
        "protocolMappers": _mappers(HOST_AUD)}))
    for name, (role, cid) in USERS.items():
        user = {"username": name, "enabled": True, "emailVerified": True, "email": f"{name}@example.test",
                "firstName": name, "lastName": "Test", "attributes": {"customer_id": [cid]} if cid else {},
                "credentials": [{"type": "password", "value": passwords[name], "temporary": False}]}
        ok(admin.post(f"/{REALM}/users", json=user))
        uid = admin.get(f"/{REALM}/users", params={"username": name, "exact": "true"}).json()[0]["id"]
        ok(admin.put(f"/{REALM}/users/{uid}/reset-password", json={"type": "password", "value": passwords[name], "temporary": False}))
        rep = admin.get(f"/{REALM}/roles/{role}").json()
        ok(admin.post(f"/{REALM}/users/{uid}/role-mappings/realm", json=[rep]))


def harness_client_secret(admin: httpx.Client) -> str:
    cid = admin.get(f"/{REALM}/clients", params={"clientId": HARNESS_CLIENT}).json()[0]["id"]
    return admin.get(f"/{REALM}/clients/{cid}/client-secret").json()["value"]


def exchange_for_host(user_token: str, secret: str) -> httpx.Response:
    """What the harness would do before calling the host: trade the user's token for one addressed to the host."""
    return httpx.post(f"{KC}/realms/{REALM}/protocol/openid-connect/token", data={
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange", "client_id": HARNESS_CLIENT, "client_secret": secret,
        "subject_token": user_token, "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
        "requested_token_type": "urn:ietf:params:oauth:token-type:access_token", "audience": HOST_AUD})


def make_passwords() -> dict[str, str]:
    shared = os.environ.get("DEV_USER_PASSWORD", "")
    return {name: shared or secrets.token_urlsafe(18) for name in USERS}


def token_for(client_id: str, username: str, password: str) -> str:
    r = httpx.post(f"{KC}/realms/{REALM}/protocol/openid-connect/token",
                   data={"grant_type": "password", "client_id": client_id, "username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


if __name__ == "__main__":  # python scripts/kc_dev_realm.py : provision the realm for the UI (needs KC_URL, KC_ADMIN_PASSWORD, DEV_USER_PASSWORD)
    if not os.environ.get("DEV_USER_PASSWORD"):
        raise SystemExit("set DEV_USER_PASSWORD (a throwaway value for the synthetic users) so you can log in")
    with admin_client() as admin:
        provision(admin, make_passwords(), os.environ.get("SPA_ORIGIN", "http://localhost:5173"))
    print(f"realm {REALM} ready: users {', '.join(USERS)}; SPA client bepmay-spa")
