"""Adapter giả, xác định, không gọi mạng. Dùng cho test đường ống và test hợp đồng; không tốn lượt API."""
from __future__ import annotations

import hashlib
import math
from typing import Callable, Literal, Optional

from lrh.contracts import (
    EmbedResult,
    GenerateRequest,
    GenerateResult,
    Usage,
    estimate_request_tokens,
    estimate_tokens,
)


class StubModel:
    provider = "stub"

    def __init__(
        self,
        model_id: str = "stub-1",
        respond: Optional[Callable[[GenerateRequest], str]] = None,
        failures: Optional[list[Exception]] = None,
        embed_dim: int = 8,
    ):
        self.model_id = model_id
        self._respond = respond
        self._failures = list(failures or [])
        self.embed_dim = embed_dim
        self.calls: list[GenerateRequest] = []

    def generate(self, req: GenerateRequest) -> GenerateResult:
        self.calls.append(req.model_copy(deep=True))
        if self._failures:
            raise self._failures.pop(0)
        if self._respond is not None:
            text = self._respond(req)
        else:
            last_user = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
            text = f"[stub] {last_user}"
        return GenerateResult(
            text=text,
            usage=Usage(prompt_tokens=estimate_request_tokens(req), output_tokens=estimate_tokens(text)),
            model_id=self.model_id,
            provider=self.provider,
            latency_ms=0.0,
        )

    def embed(self, texts: list[str], task: Literal["document", "query"] = "document") -> EmbedResult:
        vectors = [self._vec(t) for t in texts]
        return EmbedResult(
            vectors=vectors,
            model_id=self.model_id + "-embed",
            dim=self.embed_dim,
            prompt_tokens=sum(estimate_tokens(t) for t in texts),
        )

    def _vec(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [(digest[i % len(digest)] / 255.0) - 0.5 for i in range(self.embed_dim)]
        norm = math.sqrt(sum(x * x for x in raw)) or 1.0
        return [x / norm for x in raw]
