"""Test hợp đồng: mọi adapter mô hình phải qua các test này. Thêm adapter mới = thêm vào ADAPTERS.
(Ca "người không có quyền" thuộc hợp đồng của adapter kho tìm kiếm, giai đoạn 1, không phải adapter mô hình.)"""
import math

import pytest
from pydantic import ValidationError

from lrh.adapters.stub import StubModel
from lrh.contracts import Embedder, GenerateRequest, GenerateResult, Message, ModelAdapter

ADAPTERS = [pytest.param(lambda: StubModel(), id="stub")]


@pytest.fixture(params=ADAPTERS)
def adapter(request):
    return request.param()


def req(*pairs):
    return GenerateRequest(messages=[Message(role=r, content=c) for r, c in pairs])


def test_implements_protocols(adapter):
    assert isinstance(adapter, ModelAdapter)
    assert isinstance(adapter, Embedder)


def test_generate_result_shape(adapter):
    out = adapter.generate(req(("user", "Xin chào")))
    assert isinstance(out, GenerateResult)
    assert out.text
    assert out.model_id and out.provider
    assert out.usage.prompt_tokens > 0 and out.usage.output_tokens > 0
    assert out.latency_ms >= 0
    assert out.cache_hit is False and out.retries == 0 and out.rate_limited is False


def test_accepts_system_and_user(adapter):
    out = adapter.generate(req(("system", "Bạn là trợ lý."), ("user", "Hỏi gì đó")))
    assert out.text


def test_does_not_mutate_request(adapter):
    r = req(("system", "s"), ("user", "u"))
    before = r.model_dump()
    adapter.generate(r)
    assert r.model_dump() == before


def test_empty_messages_rejected():
    with pytest.raises(ValidationError):
        GenerateRequest(messages=[])


def test_embed_shape_and_determinism(adapter):
    out = adapter.embed(["a", "b", "a"])
    assert len(out.vectors) == 3
    assert all(len(v) == out.dim for v in out.vectors)
    assert out.vectors[0] == out.vectors[2]
    assert out.vectors[0] != out.vectors[1]
    assert out.model_id and out.prompt_tokens > 0
    assert all(math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, rel_tol=1e-6) for v in out.vectors)


def test_embed_query_and_document_same_dimension(adapter):
    d = adapter.embed(["x"], task="document")
    q = adapter.embed(["x"], task="query")
    assert d.dim == q.dim
