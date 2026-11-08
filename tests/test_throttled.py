import pytest

from lrh.adapters.stub import StubModel
from lrh.cache import CachedModel, ResponseCache
from lrh.contracts import (
    DailyQuotaExhausted,
    GenerateRequest,
    Message,
    RateLimited,
    RequestTooLarge,
    SpendCapExceeded,
)
from lrh.limiter import Limits, RateLimiter, SpendGuard, ThrottledModel


def r(text="hỏi"):
    return GenerateRequest(messages=[Message(role="user", content=text)], max_output_tokens=10)


def test_passes_through_result(clock):
    m = ThrottledModel(StubModel(), RateLimiter(Limits(), clock))
    out = m.generate(r())
    assert out.text.startswith("[stub]") and out.retries == 0 and out.rate_limited is False


def test_retries_with_retry_after(clock):
    inner = StubModel(failures=[RateLimited(retry_after=5)])
    m = ThrottledModel(inner, RateLimiter(Limits(), clock))
    out = m.generate(r())
    assert out.retries == 1 and out.rate_limited is True
    assert clock.sleeps == [5]
    assert len(inner.calls) == 2


def test_exponential_backoff_when_no_retry_after(clock):
    inner = StubModel(failures=[RateLimited(), RateLimited()])
    m = ThrottledModel(inner, RateLimiter(Limits(), clock), backoff_base=2.0)
    out = m.generate(r())
    assert clock.sleeps == [2.0, 4.0] and out.retries == 2


def test_gives_up_after_max_retries(clock):
    inner = StubModel(failures=[RateLimited() for _ in range(4)])
    m = ThrottledModel(inner, RateLimiter(Limits(), clock), max_retries=3)
    with pytest.raises(RateLimited):
        m.generate(r())
    assert len(inner.calls) == 4


def test_each_attempt_consumes_daily_quota(clock):
    inner = StubModel(failures=[RateLimited(retry_after=0)])
    m = ThrottledModel(inner, RateLimiter(Limits(rpd=2), clock))
    m.generate(r())  # lần thất bại + lần thử lại = 2 lượt
    with pytest.raises(DailyQuotaExhausted):
        m.generate(r("khác"))


def test_request_too_large_propagates(clock):
    m = ThrottledModel(StubModel(), RateLimiter(Limits(tpm=20), clock))
    with pytest.raises(RequestTooLarge):
        m.generate(r("x" * 500))


def test_cache_hit_does_not_touch_limiter(clock):
    limiter = RateLimiter(Limits(rpd=1), clock)
    m = CachedModel(ThrottledModel(StubModel(), limiter), ResponseCache())
    a = m.generate(r())
    b = m.generate(r())  # nếu đi qua bộ giới hạn thì hết lượt
    assert b.cache_hit and a.text == b.text


def test_spend_guard_requires_price_entry(clock):
    m = ThrottledModel(StubModel(), RateLimiter(Limits(), clock), spend=SpendGuard(1.0, {}))
    with pytest.raises(SpendCapExceeded):
        m.generate(r())


def test_spend_guard_free_tier_never_blocks(clock):
    spend = SpendGuard(0.0, {"stub-1": (0.0, 0.0)})
    m = ThrottledModel(StubModel(), RateLimiter(Limits(), clock), spend=spend)
    for _ in range(5):
        m.generate(r())
    assert spend.spent == 0.0


def test_spend_guard_cap_zero_blocks_paid_call_before_calling(clock):
    inner = StubModel()
    spend = SpendGuard(0.0, {"stub-1": (1000.0, 1000.0)})
    m = ThrottledModel(inner, RateLimiter(Limits(), clock), spend=spend)
    with pytest.raises(SpendCapExceeded):
        m.generate(r())
    assert inner.calls == []  # chặn trước khi gọi, không phải sau khi đã tốn tiền


def test_spend_guard_stops_when_projection_exceeds_cap(clock):
    spend = SpendGuard(0.1, {"stub-1": (1000.0, 1000.0)})  # 1000 USD/triệu token = 0,001 USD/token; trần 0,1 USD
    m = ThrottledModel(StubModel(), RateLimiter(Limits(), clock), spend=spend)
    big = r("một câu hỏi khá dài để tốn token " * 5)
    m.generate(big)  # dự kiến ~0,065 USD: vừa
    with pytest.raises(SpendCapExceeded):
        m.generate(big)  # tổng dự kiến vượt trần
