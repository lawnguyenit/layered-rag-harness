"""HTTP ingress for runtime Tiers 1–2. It returns a route plan, never an answer."""
from __future__ import annotations

import json
import logging
import uuid

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.concurrency import run_in_threadpool

from lrh.conversation_store import ConversationStore
from lrh.ingress import IngressGate, IngressRejected
from lrh.oidc import AuthenticationError, AuthenticationUnavailable, TokenVerifier
from lrh.request_contracts import Actor, RoutePlan, UserRequest
from lrh.routing import IntentParser, RouteCatalog, RoutePlanner


class RequestSizeMiddleware:
    def __init__(self, app, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid.uuid4())
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length.decode("ascii")) > self.max_body_bytes:
                    await _send_error(send, 413, "request_too_large", request_id)
                    return
            except (ValueError, UnicodeDecodeError):
                await _send_error(send, 400, "invalid_content_length", request_id)
                return
        messages = []
        received = 0
        while True:
            message = await receive()
            messages.append(message)
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    await _send_error(send, 413, "request_too_large", request_id)
                    return
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                return

        scope.setdefault("state", {})["request_id"] = request_id
        replay = iter(messages)

        async def replay_receive():
            try:
                return next(replay)
            except StopIteration:
                return await receive()

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                response_headers = list(message.get("headers", []))
                response_headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = response_headers
            await send(message)

        await self.app(scope, replay_receive, send_with_request_id)


async def _send_error(send, status: int, code: str, request_id: str):
    body = json.dumps({"error": code, "request_id": request_id}).encode("utf-8")
    await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii")), (b"x-request-id", request_id.encode("ascii"))]})
    await send({"type": "http.response.body", "body": body})


def create_app(
    *,
    token_verifier: TokenVerifier,
    parser: IntentParser,
    catalog: RouteCatalog,
    conversations: ConversationStore,
    max_body_bytes: int = 16_384,
    max_question_chars: int = 8_000,
    requests_per_minute: int = 30,
    input_gate: IngressGate | None = None,
) -> FastAPI:
    app = FastAPI(title="Layered RAG Harness", version="0.0.1")
    app.add_middleware(RequestSizeMiddleware, max_body_bytes=max_body_bytes)
    gate = input_gate or IngressGate(max_chars=max_question_chars, per_minute=requests_per_minute)
    planner = RoutePlanner(catalog)
    bearer = HTTPBearer(auto_error=False)

    def authenticated_actor(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> Actor:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(401, "authentication_required", headers={"WWW-Authenticate": "Bearer"})
        try:
            actor = token_verifier.actor_for(credentials.credentials)
        except AuthenticationUnavailable as exc:
            raise HTTPException(503, "identity_provider_unavailable") from exc
        except AuthenticationError as exc:
            raise HTTPException(401, "invalid_bearer_token", headers={"WWW-Authenticate": "Bearer"}) from exc
        if actor.role == "customer" and not actor.customer_id:
            raise HTTPException(403, "customer_identity_required")
        return actor

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.post("/v1/route", response_model=RoutePlan)
    async def route_request(payload: UserRequest, request: Request, actor: Actor = Depends(authenticated_actor)):
        request_id = request.state.request_id
        try:
            gate.check(actor.subject, payload.question)
        except IngressRejected as exc:
            headers = {"Retry-After": str(exc.retry_after)} if exc.retry_after else None
            raise HTTPException(exc.status_code, exc.code, headers=headers) from exc

        conversation_id = payload.conversation_id or str(uuid.uuid4())
        if payload.conversation_id and conversations.exists_for_other_actor(conversation_id, actor.subject):
            # Same response as a nonexistent conversation; do not disclose another actor's history.
            raise HTTPException(404, "conversation_not_found")
        history = conversations.history(conversation_id, actor.subject)
        try:
            parsed = await run_in_threadpool(parser.parse, payload.question, history)
        except Exception as exc:
            # Do not expose provider output or user text through an HTTP error.
            logging.getLogger(__name__).warning("intent_parse_failed request_id=%s error_type=%s", request_id, type(exc).__name__)
            raise HTTPException(503, "intent_parser_unavailable") from exc

        plan = planner.plan(
            parsed,
            question=payload.question,
            history=history,
            actor=actor,
            request_id=request_id,
            conversation_id=conversation_id,
        )
        conversations.append(conversation_id, actor.subject, payload.question)
        return plan

    return app
