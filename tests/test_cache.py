from lrh.adapters.stub import StubModel
from lrh.cache import CachedModel, ResponseCache, cache_key
from lrh.contracts import GenerateRequest, Message


def r(text="hỏi", temperature=0.0, system=None):
    msgs = ([Message(role="system", content=system)] if system else []) + [Message(role="user", content=text)]
    return GenerateRequest(messages=msgs, temperature=temperature)


def test_miss_then_hit_does_not_call_inner():
    inner = StubModel()
    m = CachedModel(inner, ResponseCache())
    a = m.generate(r())
    b = m.generate(r())
    assert len(inner.calls) == 1
    assert a.cache_hit is False and b.cache_hit is True
    assert a.text == b.text and a.usage == b.usage


def test_key_depends_on_model_messages_and_params():
    base = cache_key("m1", r())
    assert cache_key("m2", r()) != base
    assert cache_key("m1", r("khác")) != base
    assert cache_key("m1", r(system="s")) != base
    assert cache_key("m1", GenerateRequest(messages=r().messages, max_output_tokens=5)) != base


def test_different_models_share_cache_without_collision():
    cache = ResponseCache()
    a, b = StubModel(model_id="A"), StubModel(model_id="B")
    CachedModel(a, cache).generate(r())
    out = CachedModel(b, cache).generate(r())
    assert out.cache_hit is False and out.model_id == "B"
    assert len(cache) == 2


def test_nonzero_temperature_bypasses_cache():
    inner = StubModel()
    cache = ResponseCache()
    m = CachedModel(inner, cache)
    m.generate(r(temperature=0.7))
    m.generate(r(temperature=0.7))
    assert len(inner.calls) == 2 and len(cache) == 0


def test_persists_across_instances(tmp_path):
    path = str(tmp_path / "c.sqlite")
    c1 = ResponseCache(path)
    CachedModel(StubModel(), c1).generate(r())
    c1.close()
    inner = StubModel()
    out = CachedModel(inner, ResponseCache(path)).generate(r())
    assert out.cache_hit is True and inner.calls == []


def test_hit_resets_wrapper_flags():
    inner = StubModel()
    m = CachedModel(inner, ResponseCache())
    first = m.generate(r())
    m.cache.put(cache_key("stub-1", r("x")), "stub-1", first.model_copy(update={"retries": 3, "rate_limited": True}))
    hit = m.generate(r("x"))
    assert hit.cache_hit and hit.retries == 0 and hit.rate_limited is False
