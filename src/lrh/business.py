"""Port to the host system's business records (route branch C1: exact-ID lookup).

The harness does not own this data and does not decide access: it forwards the caller's bearer
token and the host answers. A record the caller may not see and one that does not exist both
come back as None, exactly as the host reports them.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

import httpx

_PATH = {"order": "orders", "ticket": "tickets", "invoice": "invoices"}


class HostUnavailable(Exception):
    """Host timed out, was unreachable, or returned a server error."""


class HostAuthError(Exception):
    """Host rejected the bearer token (expired, wrong audience, malformed)."""


@dataclass(frozen=True)
class BusinessRecord:
    kind: str
    ref_id: str
    title: str
    body: str


class BusinessLookup(Protocol):
    def get(self, bearer_token: str, kind: str, ref_id: str) -> BusinessRecord | None: ...


class HostHttpBusinessLookup:
    def __init__(self, base_url: str, *, client: httpx.Client | None = None, timeout: float = 3.0):
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def get(self, bearer_token: str, kind: str, ref_id: str) -> BusinessRecord | None:
        if kind not in _PATH:
            raise ValueError(f"unknown record kind: {kind}")
        try:
            response = self._client.get(
                f"/v1/{_PATH[kind]}/{quote(ref_id, safe='')}",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise HostUnavailable(type(exc).__name__) from exc
        if response.status_code == 404:
            return None
        if response.status_code == 401:
            raise HostAuthError("host rejected the bearer token")
        if response.status_code != 200:
            raise HostUnavailable(f"host returned {response.status_code}")
        data = response.json()
        return BusinessRecord(data["kind"], data["ref_id"], data["title"], data["body"])
