"""Bộ nhớ đệm phản hồi theo (model_id, yêu cầu). Chạy lại bộ đo không gọi lại API.
Chỉ đệm yêu cầu có temperature = 0; yêu cầu ngẫu nhiên đi thẳng xuống adapter."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from typing import Optional

from lrh.contracts import GenerateRequest, GenerateResult, ModelAdapter


def cache_key(model_id: str, req: GenerateRequest) -> str:
    payload = json.dumps({"model": model_id, "req": req.model_dump(mode="json")}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, model_id TEXT NOT NULL, created REAL NOT NULL, result TEXT NOT NULL)"
        )
        self._db.commit()

    def get(self, key: str) -> Optional[dict]:
        row = self._db.execute("SELECT result FROM cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, model_id: str, result: GenerateResult) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO cache (key, model_id, created, result) VALUES (?, ?, ?, ?)",
            (key, model_id, time.time(), json.dumps(result.model_dump(mode="json"), ensure_ascii=False)),
        )
        self._db.commit()

    def __len__(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM cache").fetchone()[0]

    def close(self) -> None:
        self._db.close()


class CachedModel:
    def __init__(self, inner: ModelAdapter, cache: ResponseCache):
        self.inner = inner
        self.cache = cache
        self.model_id = inner.model_id
        self.provider = inner.provider

    def generate(self, req: GenerateRequest) -> GenerateResult:
        if req.temperature != 0:
            return self.inner.generate(req)
        key = cache_key(self.inner.model_id, req)
        hit = self.cache.get(key)
        if hit is not None:
            return GenerateResult(**hit).model_copy(update={"cache_hit": True, "retries": 0, "rate_limited": False})
        out = self.inner.generate(req)
        self.cache.put(key, self.inner.model_id, out)
        return out
