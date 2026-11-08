from datetime import datetime

import pytest

from lrh.contracts import DailyQuotaExhausted, RequestTooLarge
from lrh.limiter import LA, Limits, RateLimiter
from tests.conftest import FakeClock


def test_rpm_blocks_sixth_request_until_window_passes(clock):
    lim = RateLimiter(Limits(rpm=5), clock)
    t0 = clock.now()
    for _ in range(5):
        lim.acquire(1)
    assert clock.sleeps == []
    lim.acquire(1)
    assert clock.now() == pytest.approx(t0 + 60)
    assert len(clock.sleeps) == 1


def test_old_events_are_pruned(clock):
    lim = RateLimiter(Limits(rpm=1), clock)
    lim.acquire(1)
    clock.t += 61
    lim.acquire(1)
    assert clock.sleeps == []


def test_tpm_waits_for_tokens_to_expire(clock):
    lim = RateLimiter(Limits(tpm=1000), clock)
    t0 = clock.now()
    lim.acquire(600)
    lim.acquire(600)
    assert clock.now() == pytest.approx(t0 + 60)


def test_request_larger_than_tpm_raises(clock):
    lim = RateLimiter(Limits(tpm=1000), clock)
    with pytest.raises(RequestTooLarge):
        lim.acquire(1001)
    assert clock.sleeps == []


def test_settle_frees_overestimated_tokens(clock):
    lim = RateLimiter(Limits(tpm=1000), clock)
    res = lim.acquire(1000)
    lim.settle(res, 100)
    lim.acquire(900)
    assert clock.sleeps == []


def test_rpd_exhaustion_raises_with_reset_at_pacific_midnight():
    start = datetime(2026, 11, 8, 23, 59, 0, tzinfo=LA).timestamp()
    clock = FakeClock(start)
    lim = RateLimiter(Limits(rpd=3), clock)
    for _ in range(3):
        lim.acquire(1)
    with pytest.raises(DailyQuotaExhausted) as e:
        lim.acquire(1)
    assert e.value.reset_at == pytest.approx(start + 60)
    reset = datetime.fromtimestamp(e.value.reset_at, LA)
    assert (reset.hour, reset.minute) == (0, 0)
    assert clock.sleeps == []  # không ngủ chờ cả ngày


def test_rpd_resets_after_pacific_midnight():
    start = datetime(2026, 11, 8, 23, 59, 0, tzinfo=LA).timestamp()
    clock = FakeClock(start)
    lim = RateLimiter(Limits(rpd=1), clock)
    lim.acquire(1)
    clock.t = start + 61
    lim.acquire(1)  # ngày mới


def test_no_limits_never_blocks(clock):
    lim = RateLimiter(Limits(), clock)
    for _ in range(1000):
        lim.acquire(10**6)
    assert clock.sleeps == []
