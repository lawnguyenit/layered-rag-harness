"""Host-owned data model and access rule (docs/DATA-CONTRACT.md section 3).

The host decides who may see a record. The harness never re-implements this rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

KINDS = ("order", "ticket", "invoice")


class Actor(BaseModel):
    subject: str
    role: Literal["visitor", "customer", "support", "finance", "manager"]
    customer_id: str | None = None


@dataclass(frozen=True)
class BusinessRecord:
    doc_id: str
    kind: str
    ref_id: str
    title: str
    body: str
    owner_customer_id: str | None


@dataclass(frozen=True)
class RecordSummary:
    """What a list shows: enough to pick a record, never the body."""
    kind: str
    ref_id: str
    title: str


def is_visible(actor: Actor, allowed_roles, owner_customer_id: str | None) -> bool:
    """A customer sees a customer-owned record only when the owner id equals their own customer id."""
    if actor.role not in allowed_roles:
        return False
    if actor.role == "customer" and owner_customer_id is not None:
        return actor.customer_id is not None and actor.customer_id == owner_customer_id
    return True
