"""Hợp đồng giữa lõi và các adapter mô hình (docs/PROVIDERS.md mục 7, docs/components/model-adapter.md).
Lõi chỉ biết các kiểu ở đây; không import SDK của nhà cung cấp."""
from __future__ import annotations

import math
from typing import Any, Literal, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ToolSpec(BaseModel):
    """Khai báo công cụ (giai đoạn 2). Chưa dùng trước đó."""
    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class GenerateRequest(BaseModel):
    messages: list[Message] = Field(min_length=1)
    temperature: float = 0.0
    max_output_tokens: Optional[int] = 1024
    tools: Optional[list[ToolSpec]] = None
    response_mime_type: Optional[Literal["application/json"]] = None


class Usage(BaseModel):
    prompt_tokens: int
    output_tokens: int


class GenerateResult(BaseModel):
    text: str
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: Usage
    model_id: str
    provider: str
    latency_ms: float
    # các trường do lớp bọc điền, không phải adapter
    cache_hit: bool = False
    retries: int = 0
    rate_limited: bool = False


class EmbedResult(BaseModel):
    vectors: list[list[float]]
    model_id: str
    dim: int
    prompt_tokens: int


@runtime_checkable
class ModelAdapter(Protocol):
    model_id: str
    provider: str

    def generate(self, req: GenerateRequest) -> GenerateResult: ...


@runtime_checkable
class Embedder(Protocol):
    model_id: str
    provider: str

    def embed(
        self,
        texts: list[str],
        task: Literal["document", "query"] = "document",
        titles: Optional[list[Optional[str]]] = None,
    ) -> EmbedResult: ...


class AdapterError(Exception):
    """Lỗi gốc của mọi lỗi adapter."""


class ProviderError(AdapterError):
    """Nhà cung cấp trả lỗi không thuộc nhóm hạn mức (4xx/5xx khác), hoặc phản hồi không dùng được."""


class EmptyResponse(ProviderError):
    """Phản hồi không có văn bản (bị chặn, hết token cho phần trả lời...). Không được coi là câu trả lời rỗng hợp lệ."""


class TransientError(ProviderError):
    """Lỗi tạm phía nhà cung cấp (HTTP 500/502/503/504): gửi lại nguyên yêu cầu có thể thành công.
    Quan sát thật: gemma-4-31b-it trả 500 INTERNAL ở 2/16 lượt (eval/results/thinking-probe-*.json, 2026-11-08)."""


class RateLimited(AdapterError):
    """Nhà cung cấp báo vượt hạn mức (ví dụ HTTP 429). retry_after tính bằng giây nếu biết."""

    def __init__(self, message: str = "rate limited", retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class DailyQuotaExhausted(AdapterError):
    """Hết lượt trong ngày (RPD). Không ngủ chờ: bộ chạy phải dừng và tiếp tục sau mốc reset_at (epoch giây)."""

    def __init__(self, reset_at: float):
        super().__init__(f"daily quota exhausted; resets at epoch {reset_at:.0f}")
        self.reset_at = reset_at


class RequestTooLarge(AdapterError):
    """Yêu cầu ước lượng vượt hạn mức token mỗi phút: không bao giờ vừa, phải giảm ngữ cảnh."""


class SpendCapExceeded(AdapterError):
    """Chi tiêu vượt SPEND_CAP_USD."""


# Hệ số đổi ký tự sang token, hiệu chỉnh ở bước 0.6 (eval/results/token-profile-2026-11-08.json, countTokens,
# gemma-4-31b-it và gemini-embedding-2, 63 mục: 23 tài liệu + 40 câu). Đo được: gộp VI 2,54, EN 3,48, thấp nhất 1,81
# (hóa đơn nhiều chữ số). 2.0 cố ý ước cao: tổng ước/thật = 1,35; 3/63 mục bị ước thấp, tệ nhất 11%.
# Hệ số cũ 3.0 ước thấp 36/63 mục. Đo lại khi corpus hoặc system prompt đổi nhiều.
CHARS_PER_TOKEN = 2.0


def estimate_tokens(text: str, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    return max(1, math.ceil(len(text) / chars_per_token))


def estimate_request_tokens(req: GenerateRequest, chars_per_token: float = CHARS_PER_TOKEN) -> int:
    return sum(estimate_tokens(m.content, chars_per_token) for m in req.messages)
