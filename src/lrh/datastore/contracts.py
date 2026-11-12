"""Business-record store contract (route branch C1: exact-ID lookup).

Contract is at the level of the job ("get one record this actor may see"), not of database
commands. A record the actor may not see is indistinguishable from one that does not exist:
both return None (docs/DATA-CONTRACT.md section 6, tier 1).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from lrh.request_contracts import Actor

KINDS = ("order", "ticket", "invoice")


@dataclass(frozen=True)
class BusinessRecord:
    doc_id: str
    kind: str
    ref_id: str
    title: str
    body: str
    owner_customer_id: str | None


class BusinessStore(Protocol):
    def get(self, actor: Actor, kind: str, ref_id: str) -> BusinessRecord | None: ...


def is_visible(actor: Actor, allowed_roles: list[str] | tuple[str, ...], owner_customer_id: str | None) -> bool:
    """Single statement of the access rule from DATA-CONTRACT section 3.

    A customer sees a customer-owned record only when the owner id equals their own customer id.
    """
    if actor.role not in allowed_roles:
        return False
    if actor.role == "customer" and owner_customer_id is not None:
        return actor.customer_id is not None and actor.customer_id == owner_customer_id
    return True
