"""Giới hạn tốc độ theo RPM, TPM và RPD cho từng mô hình (số liệu: Brain/Accounts/Gemini-API.md, docs/PROVIDERS.md 2b).
Đồng hồ và hàm ngủ được tiêm vào để test không phải chờ thật.
RPD reset lúc 00:00 giờ Thái Bình Dương (America/Los_Angeles)."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import Optional, Protocol
from zoneinfo import ZoneInfo

from lrh.contracts import DailyQuotaExhausted, RateLimited, RequestTooLarge, SpendCapExceeded
from lrh.contracts import GenerateRequest, GenerateResult, ModelAdapter, estimate_request_tokens

LA = ZoneInfo("America/Los_Angeles")


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


@dataclass(frozen=True)
class Limits:
    rpm: Optional[int] = None
    tpm: Optional[int] = None
    rpd: Optional[int] = None


class Reservation:
    def __init__(self, entry: list):
        self.entry = entry


class RateLimiter:
    def __init__(self, limits: Limits, clock: Optional[Clock] = None, window: float = 60.0):
        self.limits = limits
        self.clock = clock or SystemClock()
        self.window = window
        self._events: deque[list] = deque()  # [timestamp, tokens], theo thứ tự thời gian
        self._day = None
        self._day_count = 0

    def _roll_day(self, now: float) -> None:
        day = datetime.fromtimestamp(now, LA).date()
        if day != self._day:
            self._day = day
            self._day_count = 0

    def next_reset(self, now: float) -> float:
        day = datetime.fromtimestamp(now, LA).date()
        nxt = datetime.combine(day + timedelta(days=1), dtime.min, tzinfo=LA)
        return nxt.timestamp()

    def acquire(self, est_tokens: int) -> Reservation:
        lim = self.limits
        if lim.tpm is not None and est_tokens > lim.tpm:
            raise RequestTooLarge(f"ước lượng {est_tokens} token vượt hạn mức {lim.tpm} token/phút: giảm ngữ cảnh")
        while True:
            now = self.clock.now()
            self._roll_day(now)
            if lim.rpd is not None and self._day_count >= lim.rpd:
                raise DailyQuotaExhausted(self.next_reset(now))
            while self._events and self._events[0][0] + self.window <= now:
                self._events.popleft()
            wait = 0.0
            if lim.rpm is not None and len(self._events) >= lim.rpm:
                anchor = self._events[len(self._events) - lim.rpm][0]
                wait = max(wait, anchor + self.window - now)
            if lim.tpm is not None:
                used = sum(e[1] for e in self._events)
                if used + est_tokens > lim.tpm:
                    need = used + est_tokens - lim.tpm
                    acc = 0
                    for ts, tok in self._events:
                        acc += tok
                        if acc >= need:
                            wait = max(wait, ts + self.window - now)
                            break
            if wait <= 0:
                break
            self.clock.sleep(wait)
        entry = [now, est_tokens]
        self._events.append(entry)
        self._day_count += 1
        return Reservation(entry)

    def settle(self, res: Reservation, actual_tokens: int) -> None:
        res.entry[1] = actual_tokens


class SpendGuard:
    """Trần chi tiêu trong mã (SPEND_CAP_USD). Giá theo triệu token (vào, ra); tầng miễn phí = (0, 0).
    Kiểm TRƯỚC lượt gọi bằng chi phí tối đa dự kiến, nên cap = 0 vẫn cho chạy khi giá bằng 0."""

    def __init__(self, cap_usd: float, prices: dict[str, tuple[float, float]]):
        self.cap_usd = cap_usd
        self.prices = prices
        self.spent = 0.0

    def _price(self, model_id: str) -> tuple[float, float]:
        if model_id not in self.prices:
            raise SpendCapExceeded(f"chưa có bảng giá cho mô hình {model_id}: khai báo giá (kể cả 0) trước khi chạy")
        return self.prices[model_id]

    def before(self, model_id: str, prompt_tokens: int, max_output_tokens: int) -> None:
        pin, pout = self._price(model_id)
        projected = prompt_tokens / 1e6 * pin + max_output_tokens / 1e6 * pout
        if self.spent + projected > self.cap_usd:
            raise SpendCapExceeded(
                f"đã chi {self.spent:.6f} USD, lượt này tối đa {projected:.6f} USD, trần {self.cap_usd:.6f} USD"
            )

    def add(self, result: GenerateResult) -> None:
        pin, pout = self._price(result.model_id)
        self.spent += result.usage.prompt_tokens / 1e6 * pin + result.usage.output_tokens / 1e6 * pout


class ThrottledModel:
    """Bọc adapter: giới hạn RPM/TPM/RPD, thử lại khi nhà cung cấp báo RateLimited, kiểm trần chi tiêu."""

    def __init__(
        self,
        inner: ModelAdapter,
        limiter: RateLimiter,
        *,
        max_retries: int = 3,
        backoff_base: float = 2.0,
        backoff_cap: float = 60.0,
        spend: Optional[SpendGuard] = None,
    ):
        self.inner = inner
        self.limiter = limiter
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_cap = backoff_cap
        self.spend = spend
        self.model_id = inner.model_id
        self.provider = inner.provider

    def generate(self, req: GenerateRequest) -> GenerateResult:
        est_prompt = estimate_request_tokens(req)
        est = est_prompt + (req.max_output_tokens or 0)
        if self.spend:
            self.spend.before(self.inner.model_id, est_prompt, req.max_output_tokens or 0)
        retries = 0
        limited = False
        while True:
            res = self.limiter.acquire(est)  # mỗi lần thử, kể cả thử lại, tính là một lượt (thận trọng)
            try:
                out = self.inner.generate(req)
            except RateLimited as e:
                limited = True
                if retries >= self.max_retries:
                    raise
                delay = e.retry_after if e.retry_after is not None else min(self.backoff_cap, self.backoff_base * 2 ** retries)
                self.limiter.clock.sleep(delay)
                retries += 1
                continue
            self.limiter.settle(res, out.usage.prompt_tokens + out.usage.output_tokens)
            if self.spend:
                self.spend.add(out)
            return out.model_copy(update={"retries": retries, "rate_limited": limited})
