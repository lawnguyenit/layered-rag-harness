"""HTTP-facing request, identity, and routing contracts; separate from provider GenerateRequest."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=8000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must contain non-whitespace characters")
        return value


class Actor(BaseModel):
    subject: str = Field(min_length=1)
    role: Literal["visitor", "customer", "support", "finance", "manager"]
    customer_id: str | None = None


class SlotValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Any
    source: str = "current_turn"


class ParseTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str = Field(min_length=1, max_length=120)
    slots: dict[str, SlotValue] = Field(default_factory=dict)
    polarity: Literal["positive", "negative"] = "positive"
    negated_intents: list[str] = Field(default_factory=list)


class ParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["route", "clarify", "unsupported", "no_action"]
    tasks: list[ParseTask] = Field(default_factory=list, max_length=8)
    missing_slots: list[str] = Field(default_factory=list)
    ambiguity_type: str | None = None
    references: dict[str, str] = Field(default_factory=dict)
    negated_intents: list[str] = Field(default_factory=list)


class RouteTask(BaseModel):
    intent_id: str
    slots: dict[str, SlotValue]


class TaskOutcome(BaseModel):
    """Per-intent/target planning result; only `route` outcomes are dispatchable."""

    intent_id: str
    slots: dict[str, SlotValue] = Field(default_factory=dict)
    decision: Literal["route", "clarify", "unsupported", "no_action"]
    missing_slots: list[str] = Field(default_factory=list)
    ambiguity_type: str | None = None


class RoutePlan(BaseModel):
    request_id: str
    conversation_id: str
    decision: Literal["route", "partial", "clarify", "unsupported", "no_action"]
    tasks: list[RouteTask] = Field(default_factory=list)
    task_outcomes: list[TaskOutcome] = Field(default_factory=list)
    intent_candidates: list[str] = Field(default_factory=list)
    polarity: Literal["positive", "negative"] = "positive"
    negated_intents: list[str] = Field(default_factory=list)
    references: dict[str, str] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    ambiguity_type: str | None = None
    actor_role: str
    access_scope: dict[str, Any]
    parser_error: str | None = None
