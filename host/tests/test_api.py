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


def test_oidc_verifier_tolerates_small_clock_skew_but_not_large_or_expired():
    """A fresh token whose iat is a moment in the future (IdP clock ahead) must work; real expiry must not."""
    import time

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Jwks:
        def get_signing_key_from_jwt(self, token):
            return type("K", (), {"key": private.public_key()})()

    cfg = AuthConfig(issuer="https://idp.test/realms/x", audience="bepmay-host", jwks_url="https://idp.test/jwks", leeway_seconds=30)
    verifier = OIDCTokenVerifier(cfg, Jwks())
    now = int(time.time())

    def token(iat, exp):
        claims = {"iss": cfg.issuer, "aud": cfg.audience, "sub": "u1", "iat": iat, "exp": exp,
                  "realm_access": {"roles": ["manager"]}}
        return jwt.encode(claims, private, algorithm="RS256")

    assert verifier.actor_for(token(now + 5, now + 300)).role == "manager"  # IdP clock 5 s ahead
    with pytest.raises(AuthenticationError):
        verifier.actor_for(token(now + 120, now + 400))  # far in the future: not skew
    with pytest.raises(AuthenticationError):
        verifier.actor_for(token(now - 600, now - 120))  # genuinely expired
    with pytest.raises(ValueError):
        AuthConfig(issuer=cfg.issuer, audience="a", jwks_url=cfg.jwks_url, leeway_seconds=3600)


def test_auth_config_http_rules():
    ok = dict(issuer="https://idp.test/r", audience="a", jwks_url="https://idp.test/jwks")
    AuthConfig(**ok)
    AuthConfig(issuer="http://localhost:8080/r", audience="a", jwks_url="http://127.0.0.1:8080/jwks")  # loopback HTTP is fine
    with pytest.raises(ValueError):  # a Docker-style service name over HTTP is refused by default
        AuthConfig(issuer="https://idp.test/r", audience="a", jwks_url="http://keycloak:8080/jwks")
    AuthConfig(issuer="https://idp.test/r", audience="a", jwks_url="http://keycloak:8080/jwks", allow_insecure_http=True)
    with pytest.raises(ValueError):  # the flag never allows non-HTTP schemes or a missing host
        AuthConfig(issuer="ftp://idp.test/r", audience="a", jwks_url="https://idp.test/jwks", allow_insecure_http=True)


def test_insecure_http_flag_comes_from_the_environment_only_when_exactly_one(monkeypatch):
    base = {"HOST_OIDC_ISSUER": "https://idp.test/r", "HOST_OIDC_AUDIENCE": "a", "HOST_OIDC_JWKS_URL": "http://keycloak:8080/jwks"}
    for k, v in base.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("HOST_OIDC_ALLOW_INSECURE_HTTP", "true")  # not "1": stays off
    with pytest.raises(ValueError):
        AuthConfig.from_env()
    monkeypatch.setenv("HOST_OIDC_ALLOW_INSECURE_HTTP", "1")
    assert AuthConfig.from_env().allow_insecure_http is True

