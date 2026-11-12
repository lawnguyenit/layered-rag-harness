from __future__ import annotations

from types import SimpleNamespace
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from lrh.api import create_app
from lrh.conversation_store import ConversationStore
from lrh.oidc import AuthenticationError, AuthenticationUnavailable, OIDCConfig, OIDCTokenVerifier
from lrh.request_contracts import Actor, ParseResult
from lrh.routing import RouteCatalog


@pytest.fixture
def catalog():
    return RouteCatalog.model_validate(
        {
            "catalog_version": "test-v0",
            "slot_grammars": {"order_id": r"^BM-[0-9]{4}$"},
            "slot_definitions": {
                "order_id": {"type": "string"},
                "order_id_raw": {"type": "string"},
                "requested_field": {"type": "string", "values": ["status", "delivery_status"]},
            },
            "intents": [
                {"intent_id": "order.lookup", "required_slots": ["order_id"], "entity_slots": ["order_id"]},
                {"intent_id": "order.cancel", "supported_for_planning": False, "required_slots": ["order_id"], "entity_slots": ["order_id"]},
            ],
        }
    )


class FakeVerifier:
    def __init__(self, actor):
        self.actor = actor
        self.calls = []

    def actor_for(self, token):
        self.calls.append(token)
        if token != "valid":
            raise AuthenticationError("invalid bearer token")
        return self.actor


class FakeParser:
    def __init__(self, parsed=None):
        self.parsed = parsed or ParseResult.model_validate(
            {
                "decision": "route",
                "tasks": [{"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001"}}}],
            }
        )
        self.calls = []

    def parse(self, question, history):
        self.calls.append((question, history))
        return self.parsed


def make_client(tmp_path, actor=None, parser=None, *, rate=30, body=16384, chars=8000):
    actor = actor or Actor(subject="user-1", role="customer", customer_id="c001")
    verifier = FakeVerifier(actor)
    parser = parser or FakeParser()
    store = ConversationStore(tmp_path / "conversations.sqlite3")
    app = create_app(
        token_verifier=verifier,
        parser=parser,
        catalog=RouteCatalog.model_validate(
            {
                "catalog_version": "test-v0",
                "slot_grammars": {"order_id": r"^BM-[0-9]{4}$"},
                "slot_definitions": {
                    "order_id": {"type": "string"},
                    "order_id_raw": {"type": "string"},
                    "requested_field": {"type": "string", "values": ["status", "delivery_status"]},
                },
                "intents": [
                    {"intent_id": "order.lookup", "required_slots": ["order_id"], "entity_slots": ["order_id"]},
                    {"intent_id": "order.cancel", "supported_for_planning": False, "required_slots": ["order_id"], "entity_slots": ["order_id"]},
                ],
            }
        ),
        conversations=store,
        requests_per_minute=rate,
        max_body_bytes=body,
        max_question_chars=chars,
    )
    return TestClient(app), verifier, parser, store


def test_route_requires_valid_bearer_before_parsing(tmp_path):
    client, verifier, parser, _ = make_client(tmp_path)
    assert client.post("/v1/route", json={"question": "status?"}).status_code == 401
    assert client.post("/v1/route", json={"question": "status?"}, headers={"Authorization": "Bearer bad"}).status_code == 401
    assert verifier.calls == ["bad"]
    assert parser.calls == []


def test_actor_and_access_scope_come_from_verified_claims(tmp_path):
    client, _, _, _ = make_client(tmp_path)
    response = client.post("/v1/route", json={"question": "BM-1001 status?"}, headers={"Authorization": "Bearer valid"})
    assert response.status_code == 200
    plan = response.json()
    assert plan["actor_role"] == "customer"
    assert plan["access_scope"] == {"role": "customer", "owner_customer_id": "c001"}
    assert plan["tasks"][0]["slots"]["order_id"]["value"] == "BM-1001"


def test_caller_cannot_supply_actor_or_scope_fields(tmp_path):
    client, _, parser, _ = make_client(tmp_path)
    response = client.post(
        "/v1/route",
        json={"question": "BM-1001 status?", "role": "manager", "customer_id": "c999", "access_scope": {"role": "manager"}},
        headers={"Authorization": "Bearer valid"},
    )
    assert response.status_code == 422
    assert parser.calls == []


def test_customer_without_customer_identity_is_denied(tmp_path):
    client, _, parser, _ = make_client(tmp_path, Actor(subject="user-2", role="customer"))
    response = client.post("/v1/route", json={"question": "BM-1001 status?"}, headers={"Authorization": "Bearer valid"})
    assert response.status_code == 403
    assert parser.calls == []


def test_request_body_limit_and_question_limit(tmp_path):
    client, _, parser, _ = make_client(tmp_path, body=40, chars=20)
    huge = client.post("/v1/route", content=b"x" * 100, headers={"Authorization": "Bearer valid", "content-type": "application/json"})
    assert huge.status_code == 413
    # A short JSON body that contains a question over the configured cap is rejected by the gate.
    client2, _, parser2, _ = make_client(tmp_path / "second", body=1024, chars=5)
    long_question = client2.post("/v1/route", json={"question": "123456"}, headers={"Authorization": "Bearer valid"})
    assert long_question.status_code == 413
    assert parser.calls == [] and parser2.calls == []


def test_rate_limit_is_keyed_by_authenticated_subject(tmp_path):
    client, _, parser, _ = make_client(tmp_path, rate=1)
    headers = {"Authorization": "Bearer valid"}
    assert client.post("/v1/route", json={"question": "BM-1001 status?"}, headers=headers).status_code == 200
    limited = client.post("/v1/route", json={"question": "BM-1002 status?"}, headers=headers)
    assert limited.status_code == 429
    assert limited.headers["retry-after"]
    assert len(parser.calls) == 1


def test_conversation_history_is_owner_scoped_and_server_loaded(tmp_path):
    client, verifier, parser, _ = make_client(tmp_path)
    headers = {"Authorization": "Bearer valid"}
    first = client.post("/v1/route", json={"question": "BM-1001 order"}, headers=headers)
    conversation_id = first.json()["conversation_id"]
    second = client.post("/v1/route", json={"question": "Đơn đó tới đâu rồi?", "conversation_id": conversation_id}, headers=headers)
    assert second.status_code == 200
    assert parser.calls[-1][1] == [{"turn": 1, "utterance": "BM-1001 order"}]
    verifier.actor = Actor(subject="user-2", role="customer", customer_id="c002")
    other_actor = client.post("/v1/route", json={"question": "Đơn đó tới đâu rồi?", "conversation_id": conversation_id}, headers=headers)
    assert other_actor.status_code == 404
    assert len(parser.calls) == 2


def test_route_planner_missing_invalid_unsupported_multi_and_negative(catalog):
    from lrh.request_contracts import Actor
    from lrh.routing import RoutePlanner

    planner = RoutePlanner(catalog)
    actor = Actor(subject="u1", role="customer", customer_id="c001")
    args = dict(question="", history=[], actor=actor, request_id="r1", conversation_id="c1")
    missing = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [{"intent_id": "order.lookup"}]}), **args)
    assert missing.decision == "clarify" and missing.missing_slots == ["order_id"]
    invalid = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {"order_id_raw": {"value": "BM-1O01"}}}]}), **args)
    assert invalid.decision == "clarify" and invalid.missing_slots == ["order_id"]
    unsupported = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [{"intent_id": "order.cancel", "slots": {"order_id": {"value": "BM-1001"}}}]}), **{**args, "question": "Hủy BM-1001"})
    assert unsupported.decision == "unsupported" and unsupported.tasks == []
    missing_unsupported = planner.plan(ParseResult.model_validate({"decision": "unsupported", "tasks": [{"intent_id": "order.cancel"}]}), **args)
    assert missing_unsupported.decision == "clarify" and missing_unsupported.missing_slots == ["order_id"]
    negative = planner.plan(ParseResult.model_validate({"decision": "no_action", "tasks": [{"intent_id": "order.cancel", "polarity": "negative"}]}), **args)
    assert negative.decision == "no_action" and negative.tasks == []
    mixed = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [
        {"intent_id": "order.cancel", "polarity": "negative", "slots": {"order_id": {"value": "BM-1001"}}},
        {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1002"}}},
    ]}), **{**args, "question": "Không hủy BM-1001, chỉ xem BM-1002"})
    assert mixed.decision == "route" and [task.intent_id for task in mixed.tasks] == ["order.lookup"]
    multiple = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [
        {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001"}}},
        {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1002"}}},
    ]}), **{**args, "question": "Tra cứu BM-1001 và BM-1002"})
    assert multiple.decision == "route" and len(multiple.tasks) == 2
    invalid_value = planner.plan(ParseResult.model_validate({"decision": "route", "tasks": [
        {"intent_id": "order.lookup", "slots": {"order_id": {"value": "BM-1001"}, "requested_field": {"value": "cancel"}}},
    ]}), **{**args, "question": "BM-1001 trạng thái?"})
    assert invalid_value.decision == "clarify" and "requested_field" in invalid_value.missing_slots


def test_reference_resolves_to_latest_compatible_entity(catalog):
    from lrh.request_contracts import Actor
    from lrh.routing import RoutePlanner

    parsed = ParseResult.model_validate({"decision": "route", "tasks": [{"intent_id": "order.lookup", "slots": {"requested_field": {"value": "delivery_status"}}}]})
    plan = RoutePlanner(catalog).plan(
        parsed,
        question="Đơn đó giao chưa?",
        history=[{"turn": 1, "utterance": "Đơn BM-1001 đang giao."}, {"turn": 2, "utterance": "Đơn BM-1002 đã nhận."}],
        actor=Actor(subject="u1", role="customer", customer_id="c001"),
        request_id="r1",
        conversation_id="c1",
    )
    assert plan.decision == "route"
    assert plan.tasks[0].slots["order_id"].value == "BM-1002"
    assert plan.tasks[0].slots["order_id"].source == "prior_turn_2"


def test_same_turn_reference_resolves_to_latest_mentioned_entity(catalog):
    from lrh.request_contracts import Actor
    from lrh.routing import RoutePlanner

    parsed = ParseResult.model_validate({"decision": "route", "tasks": [{"intent_id": "order.lookup"}]})
    plan = RoutePlanner(catalog).plan(
        parsed,
        question="Đừng hủy BM-1001; chỉ kiểm tra trạng thái đơn đó.",
        history=[{"turn": 1, "utterance": "Đơn BM-1002 đang giao."}],
        actor=Actor(subject="u1", role="customer", customer_id="c001"),
        request_id="r1",
        conversation_id="c1",
    )
    assert plan.decision == "route"
    assert plan.tasks[0].slots["order_id"].value == "BM-1001"
    assert plan.tasks[0].slots["order_id"].source == "current_turn"
    assert plan.references == {}


def test_oidc_verifies_signature_issuer_audience_expiry_and_role_claim():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key()

    class FakeJwks:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public)

    config = OIDCConfig(issuer="https://issuer.test/realm", audience="lrh-api", jwks_url="https://issuer.test/keys")
    verifier = OIDCTokenVerifier(config, jwks_client=FakeJwks())
    now = int(time.time())
    token = jwt.encode(
        {"iss": config.issuer, "aud": config.audience, "sub": "user-1", "iat": now, "exp": now + 300,
         "realm_access": {"roles": ["customer"]}, "customer_id": "c001"},
        private,
        algorithm="RS256",
    )
    actor = verifier.actor_for(token)
    assert (actor.subject, actor.role, actor.customer_id) == ("user-1", "customer", "c001")
    wrong_issuer = jwt.encode(
        {"iss": "https://wrong.test", "aud": config.audience, "sub": "user-1", "iat": now, "exp": now + 300,
         "realm_access": {"roles": ["customer"]}, "customer_id": "c001"},
        private,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.actor_for(wrong_issuer)
    wrong_audience = jwt.encode(
        {"iss": config.issuer, "aud": "another-api", "sub": "user-1", "iat": now, "exp": now + 300,
         "realm_access": {"roles": ["customer"]}, "customer_id": "c001"},
        private,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.actor_for(wrong_audience)
    expired = jwt.encode(
        {"iss": config.issuer, "aud": config.audience, "sub": "user-1", "iat": 1, "exp": 2,
         "realm_access": {"roles": ["customer"]}, "customer_id": "c001"},
        private,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.actor_for(expired)
    no_role = jwt.encode(
        {"iss": config.issuer, "aud": config.audience, "sub": "user-1", "iat": now, "exp": now + 300,
         "realm_access": {"roles": ["offline_access"]}},
        private,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.actor_for(no_role)
    multiple_roles = jwt.encode(
        {"iss": config.issuer, "aud": config.audience, "sub": "user-1", "iat": now, "exp": now + 300,
         "realm_access": {"roles": ["customer", "manager"]}, "customer_id": "c001"},
        private,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationError):
        verifier.actor_for(multiple_roles)

    class OfflineJwks:
        def get_signing_key_from_jwt(self, token):
            raise jwt.PyJWKClientConnectionError("offline")

    with pytest.raises(AuthenticationUnavailable):
        OIDCTokenVerifier(config, jwks_client=OfflineJwks()).actor_for(token)


def test_oidc_rejects_plain_http_outside_loopback():
    with pytest.raises(ValueError):
        OIDCConfig(issuer="http://issuer.example/realm", audience="lrh-api", jwks_url="http://issuer.example/keys")
