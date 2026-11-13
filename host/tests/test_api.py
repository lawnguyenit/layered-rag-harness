from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from bepmay_host.access import Actor
from bepmay_host.api import create_app
from bepmay_host.auth import AuthConfig, AuthenticationError, OIDCTokenVerifier
from bepmay_host.corpus import load_corpus
from bepmay_host.memory_store import MemoryBusinessStore

CORPUS = Path(__file__).resolve().parents[2] / "data" / "corpus"


class FakeVerifier:
    def actor_for(self, token):
        if token == "bad":
            raise AuthenticationError("bad")
        role, _, cid = token.partition(":")
        return Actor(subject=token, role=role, customer_id=cid or None)


@pytest.fixture
def client():
    return TestClient(create_app(token_verifier=FakeVerifier(), store=MemoryBusinessStore(load_corpus(CORPUS))))


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_requires_bearer(client):
    assert client.get("/v1/orders/BM-1001").status_code == 401
    assert client.get("/v1/orders/BM-1001", headers=auth("bad")).status_code == 401


def test_owner_reads_and_other_customer_gets_same_404_as_missing(client):
    assert client.get("/v1/orders/BM-1001", headers=auth("customer:c001")).status_code == 200
    denied = client.get("/v1/orders/BM-1002", headers=auth("customer:c001"))
    missing = client.get("/v1/orders/BM-9999", headers=auth("customer:c001"))
    assert (denied.status_code, denied.json()) == (missing.status_code, missing.json()) == (404, {"detail": "not_found"})


def test_malformed_reference_is_not_found(client):
    assert client.get("/v1/orders/BM-1001%27%20OR%201=1", headers=auth("manager:")).status_code == 404


def test_role_matrix_over_http(client):
    assert client.get("/v1/invoices/INV-2026-0451", headers=auth("support:")).status_code == 404
    assert client.get("/v1/invoices/INV-2026-0451", headers=auth("finance:")).status_code == 200
    assert client.get("/v1/tickets/T01", headers=auth("finance:")).status_code == 404


def test_oidc_verifier_checks_audience_and_role():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Jwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": private.public_key()})()

    cfg = AuthConfig(issuer="https://idp.test/realms/x", audience="bepmay-host", jwks_url="https://idp.test/jwks")
    verifier = OIDCTokenVerifier(cfg, Jwks())

    def token(**over):
        claims = {"iss": cfg.issuer, "aud": cfg.audience, "sub": "u1", "iat": 1, "exp": 4_000_000_000,
                  "realm_access": {"roles": ["customer"]}, "customer_id": "c001"}
        claims.update(over)
        return jwt.encode(claims, private, algorithm="RS256")

    actor = verifier.actor_for(token())
    assert (actor.role, actor.customer_id) == ("customer", "c001")
    with pytest.raises(AuthenticationError):
        verifier.actor_for(token(aud="lrh-api"))  # token issued for another API
    with pytest.raises(AuthenticationError):
        verifier.actor_for(token(realm_access={"roles": ["customer", "manager"]}))
