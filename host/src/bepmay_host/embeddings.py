"""Embedding adapters. The host owns both the index and the query embedding, so the harness never has to
match an embedding model: it sends text and the host embeds it with the model the index was built with.

- HashEmbedder: deterministic bag-of-words hashing. Test/dev only (no key, no network); not semantic.
- GeminiRestEmbedder: one request per text (a multi-string request to gemini-embedding-2 returns ONE pooled
  vector, which silently breaks retrieval). The request shape follows the Gemini API docs as remembered by
  the author and counts as verified only after a live call: see docs/components/host-search.md.
"""
from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Protocol

import httpx


class EmbeddingUnavailable(Exception):
    """Provider unreachable, rate limited, or returned something unusable."""


class Embedder(Protocol):
    model_id: str

    def embed_documents(self, items: list[tuple[str, str]]) -> list[list[float]]:
        """items are (title, text)."""

    def embed_query(self, text: str) -> list[float]: ...


_TOKEN = re.compile(r"\w+", re.UNICODE)


class HashEmbedder:
    def __init__(self, dim: int = 256):
        self.dim = dim
        self.model_id = f"hash-bow-{dim}"

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for tok in _TOKEN.findall(text.lower()):
            h = int.from_bytes(hashlib.blake2b(tok.encode(), digest_size=8).digest(), "big")
            v[h % self.dim] += 1.0
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norm for x in v]

    def embed_documents(self, items):
        return [self._vec(f"{title} {text}") for title, text in items]

    def embed_query(self, text):
        return self._vec(text)


class GeminiRestEmbedder:
    def __init__(self, api_key: str, *, model: str = "gemini-embedding-2", dim: int = 768,
                 client: httpx.Client | None = None, timeout: float = 20.0):
        if not api_key:
            raise ValueError("an embedding API key is required")
        self.model_id = f"{model}@{dim}"
        self._model, self._dim = model, dim
        self._client = client or httpx.Client(base_url="https://generativelanguage.googleapis.com", timeout=timeout)
        self._headers = {"x-goog-api-key": api_key}

    def _embed(self, text: str) -> list[float]:
        body = {"model": f"models/{self._model}", "content": {"parts": [{"text": text}]}, "outputDimensionality": self._dim}
        try:
            r = self._client.post(f"/v1beta/models/{self._model}:embedContent", json=body, headers=self._headers)
        except httpx.HTTPError as exc:
            raise EmbeddingUnavailable(type(exc).__name__) from exc
        if r.status_code != 200:
            raise EmbeddingUnavailable(f"provider returned {r.status_code}")  # body not surfaced: it may echo the input
        try:
            values = r.json()["embedding"]["values"]
        except (KeyError, ValueError) as exc:
            raise EmbeddingUnavailable("unexpected provider response") from exc
        if len(values) != self._dim:
            raise EmbeddingUnavailable(f"expected {self._dim} dims, got {len(values)}")
        return [float(x) for x in values]

    def embed_documents(self, items):
        return [self._embed(f"title: {title or 'none'} | text: {text}") for title, text in items]

    def embed_query(self, text):
        return self._embed(f"task: search result | query: {text}")


def embedder_from_env() -> Embedder:
    kind = os.getenv("HOST_EMBEDDER", "hash").strip().lower()
    if kind == "hash":
        return HashEmbedder()
    if kind == "gemini":
        return GeminiRestEmbedder(
            os.getenv("HOST_EMBEDDING_API_KEY", "").strip(),
            model=os.getenv("HOST_EMBEDDING_MODEL", "gemini-embedding-2"),
            dim=int(os.getenv("HOST_EMBEDDING_DIM", "768")),
        )
    raise RuntimeError("HOST_EMBEDDER must be 'hash' or 'gemini'")
