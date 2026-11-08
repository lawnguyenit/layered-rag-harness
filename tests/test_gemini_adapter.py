"""Kiểm adapter Gemini bằng client giả dùng đúng kiểu dữ liệu của SDK thật (không gọi mạng)."""
import pytest
from google.genai import errors, types

from lrh.adapters.gemini import GeminiEmbedder, GeminiModel, map_error
from lrh.contracts import (
    DailyQuotaExhausted, EmptyResponse, GenerateRequest, Message, ProviderError, RateLimited, ToolSpec,
)


class FakeModels:
    def __init__(self, gen=None, emb=None, exc=None):
        self.gen, self.emb, self.exc, self.calls = gen, emb, exc, []

    def generate_content(self, **kw):
        self.calls.append(("gen", kw))
        if self.exc:
            raise self.exc
        return self.gen

    def embed_content(self, **kw):
        self.calls.append(("emb", kw))
        if self.exc:
            raise self.exc
        return self.emb


class FakeClient:
    def __init__(self, **kw):
        self.models = FakeModels(**kw)


def resp(text="xin chào", prompt=10, cand=3, thoughts=2, finish="STOP"):
    parts = [types.Part(text=text)] if text is not None else []
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts), finish_reason=finish)],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt, candidates_token_count=cand, thoughts_token_count=thoughts),
    )


def req(*pairs):
    return GenerateRequest(messages=[Message(role=r, content=c) for r, c in pairs])


def test_generate_maps_text_usage_and_roles():
    c = FakeClient(gen=resp())
    out = GeminiModel("gemma-4-31b-it", client=c).generate(req(("system", "S"), ("user", "hỏi"), ("assistant", "đáp"), ("user", "tiếp")))
    assert out.text == "xin chào" and out.usage.prompt_tokens == 10 and out.usage.output_tokens == 5
    kw = c.models.calls[0][1]
    assert kw["model"] == "gemma-4-31b-it"
    assert [x.role for x in kw["contents"]] == ["user", "model", "user"]
    assert kw["config"].system_instruction == "S"


def test_usage_none_fields_are_zero():
    r = resp()
    r.usage_metadata = types.GenerateContentResponseUsageMetadata(prompt_token_count=4)
    out = GeminiModel("m", client=FakeClient(gen=r)).generate(req(("user", "a")))
    assert out.usage.prompt_tokens == 4 and out.usage.output_tokens == 0


def test_empty_response_raises_not_silent():
    with pytest.raises(EmptyResponse):
        GeminiModel("m", client=FakeClient(gen=resp(text=None, finish="SAFETY"))).generate(req(("user", "a")))


def test_tools_not_supported_yet():
    r = GenerateRequest(messages=[Message(role="user", content="a")],
                        tools=[ToolSpec(name="t", description="d", input_schema={})])
    with pytest.raises(ProviderError):
        GeminiModel("m", client=FakeClient(gen=resp())).generate(r)


def test_429_retryinfo_becomes_rate_limited():
    e = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota", "details": [
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"}]}})
    with pytest.raises(RateLimited) as ei:
        GeminiModel("m", client=FakeClient(exc=e)).generate(req(("user", "a")))
    assert ei.value.retry_after == 7.0


def test_429_perday_becomes_daily_exhausted():
    e = errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "message": "quota", "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}})
    assert isinstance(map_error(e), DailyQuotaExhausted)


def test_other_errors_become_provider_error():
    assert isinstance(map_error(errors.ServerError(503, {"error": {"message": "x", "status": "UNAVAILABLE"}})), ProviderError)
    assert not isinstance(map_error(errors.ClientError(400, {"error": {"message": "bad"}})), RateLimited)


def emb_resp(n, d=4):
    return types.EmbedContentResponse(embeddings=[types.ContentEmbedding(values=[0.1] * d) for _ in range(n)])


def test_embedding2_wraps_each_text_in_own_content_and_prefixes():
    c = FakeClient(emb=emb_resp(2))
    out = GeminiEmbedder("gemini-embedding-2", dim=4, client=c).embed(["a", "b"], titles=["T", None])
    kw = c.models.calls[0][1]
    assert len(kw["contents"]) == 2 and all(isinstance(x, types.Content) for x in kw["contents"])
    assert kw["contents"][0].parts[0].text == "title: T | text: a"
    assert kw["contents"][1].parts[0].text == "title: none | text: b"
    assert kw["config"].output_dimensionality == 4 and kw["config"].task_type is None
    assert len(out.vectors) == 2 and out.dim == 4


def test_embedding2_query_prefix():
    c = FakeClient(emb=emb_resp(1))
    GeminiEmbedder("gemini-embedding-2", dim=4, client=c).embed(["câu hỏi"], task="query")
    assert c.models.calls[0][1]["contents"][0].parts[0].text == "task: search result | query: câu hỏi"


def test_embedding001_uses_task_type():
    c = FakeClient(emb=emb_resp(1))
    GeminiEmbedder("gemini-embedding-001", dim=4, client=c).embed(["x"], task="query")
    assert c.models.calls[0][1]["config"].task_type == "RETRIEVAL_QUERY"


def test_embedding_aggregated_vector_is_rejected():
    with pytest.raises(ProviderError):
        GeminiEmbedder("gemini-embedding-2", dim=4, client=FakeClient(emb=emb_resp(1))).embed(["a", "b"])
