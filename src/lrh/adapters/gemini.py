"""Adapter Gemini API (cùng khóa gọi được Gemma 4 và Gemini; chỉ đổi tên mô hình).
Tên lớp và trường SDK được kiểm trên google-genai 2.33.0 (đọc mã SDK, 2026-11-08); lời gọi mạng thật chưa chạy ở bước này:
dùng `uv run pytest -m live` trên máy chủ repo để kiểm."""
from __future__ import annotations

import time
from typing import Any, Literal, Optional

from google import genai
from google.genai import errors, types

from lrh.contracts import (
    DailyQuotaExhausted,
    EmbedResult,
    EmptyResponse,
    GenerateRequest,
    GenerateResult,
    ProviderError,
    RateLimited,
    TransientError,
    Usage,
    estimate_tokens,
)
from lrh.limiter import next_pacific_midnight


def _make_client(api_key: Optional[str], timeout_s: float) -> Any:
    # attempts=1: SDK không tự thử lại, để ThrottledModel đếm đúng từng lượt và quyết định chờ bao lâu
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_s * 1000), retry_options=types.HttpRetryOptions(attempts=1)),
    )


def _details_list(e: Any) -> list[dict]:
    d = getattr(e, "details", None)
    if isinstance(d, dict):
        d = d.get("error", {}).get("details", [])
    return [x for x in d if isinstance(x, dict)] if isinstance(d, list) else []


def _parse_seconds(v: Any) -> Optional[float]:
    if not isinstance(v, str):
        return None
    try:
        if v.endswith("ms"):
            return float(v[:-2]) / 1000
        if v.endswith("s"):
            return float(v[:-1])
    except ValueError:
        return None
    return None


def map_error(e: Any) -> Exception:
    code = getattr(e, "code", None)
    msg = f"{code} {getattr(e, 'status', '')}: {getattr(e, 'message', '')}".strip()
    if code == 429:
        details = _details_list(e)
        quota_ids = [str(v.get("quotaId", "")) for d in details for v in d.get("violations", []) if isinstance(v, dict)]
        # Suy đoán theo tên quotaId (chưa quan sát lỗi thật): nếu nhắc "PerDay" thì coi là hết lượt ngày
        if any("perday" in q.replace("_", "").lower() for q in quota_ids):
            return DailyQuotaExhausted(next_pacific_midnight(time.time()))
        retry = next((_parse_seconds(d.get("retryDelay")) for d in details if str(d.get("@type", "")).endswith("RetryInfo")), None)
        return RateLimited(msg, retry_after=retry)
    if code in (500, 502, 503, 504):
        return TransientError(msg)
    return ProviderError(msg)


class GeminiModel:
    provider = "gemini"

    def __init__(
        self,
        model_id: str,
        *,
        client: Any = None,
        api_key: Optional[str] = None,
        thinking_level: Optional[str] = None,
        timeout_s: float = 120.0,
    ):
        self.model_id = model_id
        self._client = client or _make_client(api_key, timeout_s)
        self._thinking_level = thinking_level

    def generate(self, req: GenerateRequest) -> GenerateResult:
        if req.tools:
            raise ProviderError("công cụ chưa được hỗ trợ ở giai đoạn 0 (giai đoạn 2)")
        system = "\n\n".join(m.content for m in req.messages if m.role == "system")
        contents = [
            types.Content(role="model" if m.role == "assistant" else "user", parts=[types.Part(text=m.content)])
            for m in req.messages
            if m.role != "system"
        ]
        if not contents:
            raise ProviderError("cần ít nhất một tin nhắn user hoặc assistant")
        cfg: dict[str, Any] = {"temperature": req.temperature, "max_output_tokens": req.max_output_tokens}
        if system:
            cfg["system_instruction"] = system
        if self._thinking_level:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_level=self._thinking_level)
        t0 = time.perf_counter()
        try:
            resp = self._client.models.generate_content(
                model=self.model_id, contents=contents, config=types.GenerateContentConfig(**cfg)
            )
        except errors.APIError as e:
            raise map_error(e) from e
        latency_ms = (time.perf_counter() - t0) * 1000
        text = resp.text or ""
        if not text.strip():
            reason = None
            cands = getattr(resp, "candidates", None) or []
            if cands:
                reason = getattr(cands[0], "finish_reason", None)
            raise EmptyResponse(f"phản hồi không có văn bản (finish_reason={reason})")
        um = resp.usage_metadata
        prompt = (um.prompt_token_count or 0) if um else 0
        out = ((um.candidates_token_count or 0) + (um.thoughts_token_count or 0)) if um else 0
        return GenerateResult(
            text=text,
            usage=Usage(prompt_tokens=prompt, output_tokens=out),
            model_id=self.model_id,
            provider=self.provider,
            latency_ms=latency_ms,
        )


class GeminiEmbedder:
    provider = "gemini"

    def __init__(
        self,
        model_id: str = "gemini-embedding-2",
        *,
        dim: int = 768,
        client: Any = None,
        api_key: Optional[str] = None,
        timeout_s: float = 120.0,
    ):
        self.model_id = model_id
        self.dim = dim
        self._client = client or _make_client(api_key, timeout_s)

    def embed(
        self,
        texts: list[str],
        task: Literal["document", "query"] = "document",
        titles: Optional[list[Optional[str]]] = None,
    ) -> EmbedResult:
        if not texts:
            raise ProviderError("embed cần ít nhất một văn bản")
        if self.model_id.startswith("gemini-embedding-2"):
            # Bản 2 không dùng task_type: tiền tố trong văn bản (tài liệu Gemini API, đọc 2026-11-08)
            if task == "query":
                inputs = [f"task: search result | query: {t}" for t in texts]
            else:
                inputs = [f"title: {(titles[i] if titles and titles[i] else 'none')} | text: {t}" for i, t in enumerate(texts)]
            cfg = types.EmbedContentConfig(output_dimensionality=self.dim)
        else:
            inputs = list(texts)
            cfg = types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY" if task == "query" else "RETRIEVAL_DOCUMENT", output_dimensionality=self.dim
            )
        # BẪY: truyền nhiều chuỗi trong `contents` của gemini-embedding-2 trả về MỘT vector gộp (tài liệu nói rõ).
        # Muốn mỗi văn bản một vector phải bọc từng văn bản trong một Content riêng.
        contents = [types.Content(parts=[types.Part(text=s)]) for s in inputs]
        try:
            resp = self._client.models.embed_content(model=self.model_id, contents=contents, config=cfg)
        except errors.APIError as e:
            raise map_error(e) from e
        vectors = [list(e.values) for e in (resp.embeddings or [])]
        if len(vectors) != len(texts):
            raise ProviderError(f"nhận {len(vectors)} vector cho {len(texts)} văn bản (có thể là vector gộp)")
        return EmbedResult(
            vectors=vectors,
            model_id=self.model_id,
            dim=len(vectors[0]),
            prompt_tokens=sum(estimate_tokens(s) for s in inputs),  # ƯỚC LƯỢNG: chưa đọc số token từ phản hồi
        )
