"""Provider-neutral OIDC bearer-token verification and trusted actor construction."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient

from lrh.request_contracts import Actor


class AuthenticationError(Exception):
    pass


class AuthenticationUnavailable(Exception):
    pass


@dataclass(frozen=True)
class OIDCConfig:
    issuer: str
    audience: str
    jwks_url: str
    role_claim: str = "realm_access.roles"
    customer_id_claim: str = "customer_id"

    def __post_init__(self):
        for name, value in (("issuer", self.issuer), ("jwks_url", self.jwks_url)):
            parsed = urlparse(value)
            if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
                raise ValueError(f"{name} must use HTTPS except for a loopback development issuer")
            if not parsed.hostname:
                raise ValueError(f"{name} must be an absolute URL")

    @classmethod
    def from_env(cls) -> "OIDCConfig":
        values = {
            "issuer": os.getenv("OIDC_ISSUER", "").strip(),
            "audience": os.getenv("OIDC_AUDIENCE", "").strip(),
            "jwks_url": os.getenv("OIDC_JWKS_URL", "").strip(),
        }
        if not all(values.values()):
            raise RuntimeError("OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_URL are required")
        return cls(
            **values,
            role_claim=os.getenv("OIDC_ROLE_CLAIM", "realm_access.roles").strip(),
            customer_id_claim=os.getenv("OIDC_CUSTOMER_ID_CLAIM", "customer_id").strip(),
        )


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
    """Verifies signature, fixed algorithm, issuer, audience and exp before mapping claims."""

    def __init__(self, config: OIDCConfig, jwks_client: Any | None = None):
        self.config = config
        self.jwks = jwks_client or PyJWKClient(config.jwks_url, timeout=3, cache_keys=True)

    def actor_for(self, token: str) -> Actor:
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token).key
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthenticationUnavailable("OIDC signing keys unavailable") from exc
        except Exception as exc:
            raise AuthenticationError("invalid bearer token") from exc
        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=self.config.issuer,
                audience=self.config.audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("invalid bearer token") from exc

        roles = _claim(payload, self.config.role_claim)
        if isinstance(roles, str):
            roles = [roles]
        if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
            raise AuthenticationError("token has malformed application roles")
        allowed_roles = {"visitor", "customer", "support", "finance", "manager"}
        recognized_roles = [role for role in roles if role in allowed_roles]
        if len(recognized_roles) != 1:
            raise AuthenticationError("token must have exactly one recognized application role")
        role = recognized_roles[0]
        customer_id = _claim(payload, self.config.customer_id_claim)
        if customer_id is not None and not isinstance(customer_id, str):
            raise AuthenticationError("invalid customer identity claim")
        try:
            return Actor(subject=payload["sub"], role=role, customer_id=customer_id)
        except Exception as exc:
            raise AuthenticationError("invalid actor claims") from exc
