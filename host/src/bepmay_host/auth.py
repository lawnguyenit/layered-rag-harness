"""The host verifies bearer tokens itself; it does not trust the harness to vouch for the user.

Own copy of the RS256/issuer/audience/role verification (the harness has a similar one for its
own audience). Audience here is the host's, so a token must be issued for this API.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from bepmay_host.access import Actor

ROLES = {"visitor", "customer", "support", "finance", "manager"}


class AuthenticationError(Exception):
    pass


class AuthenticationUnavailable(Exception):
    pass


@dataclass(frozen=True)
class AuthConfig:
    issuer: str
    audience: str
    jwks_url: str
    role_claim: str = "realm_access.roles"
    customer_id_claim: str = "customer_id"

    def __post_init__(self):
        for name, value in (("issuer", self.issuer), ("jwks_url", self.jwks_url)):
            p = urlparse(value)
            if not p.hostname or (p.scheme != "https" and not (p.scheme == "http" and p.hostname in {"localhost", "127.0.0.1", "::1"})):
                raise ValueError(f"{name} must be an absolute HTTPS URL (HTTP only on loopback)")

    @classmethod
    def from_env(cls) -> "AuthConfig":
        vals = {k: os.getenv(f"HOST_OIDC_{k.upper()}", "").strip() for k in ("issuer", "audience", "jwks_url")}
        if not all(vals.values()):
            raise RuntimeError("HOST_OIDC_ISSUER, HOST_OIDC_AUDIENCE and HOST_OIDC_JWKS_URL are required")
        return cls(**vals)


class TokenVerifier(Protocol):
    def actor_for(self, token: str) -> Actor: ...


def _claim(payload: dict[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


class OIDCTokenVerifier:
    def __init__(self, config: AuthConfig, jwks_client: Any | None = None):
        self.config = config
        self.jwks = jwks_client or PyJWKClient(config.jwks_url, timeout=3, cache_keys=True)

    def actor_for(self, token: str) -> Actor:
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthenticationUnavailable("signing keys unavailable") from exc
        except Exception as exc:
            raise AuthenticationError("invalid bearer token") from exc
        try:
            payload = jwt.decode(
                token, key, algorithms=["RS256"], issuer=self.config.issuer, audience=self.config.audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("invalid bearer token") from exc
        roles = _claim(payload, self.config.role_claim)
        if isinstance(roles, str):
            roles = [roles]
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise AuthenticationError("malformed roles")
        known = [r for r in roles if r in ROLES]
        if len(known) != 1:
            raise AuthenticationError("exactly one recognized role required")
        cid = _claim(payload, self.config.customer_id_claim)
        if cid is not None and not isinstance(cid, str):
            raise AuthenticationError("invalid customer claim")
        return Actor(subject=payload["sub"], role=known[0], customer_id=cid)
