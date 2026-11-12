"""Cheap, deterministic ingress limits. Semantic moderation belongs to a separate measured layer."""
from __future__ import annotations

import threading
import time
from collections import deque


class IngressRejected(Exception):
    def __init__(self, code: str, status_code: int, retry_after: int | None = None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.retry_after = retry_after


class IngressGate:
    """Per-process sliding-window limiter plus deterministic question constraints."""

    def __init__(self, *, max_chars: int = 8000, per_minute: int = 30, max_subjects: int = 10000, clock=time.monotonic):
        if max_chars < 1 or per_minute < 1 or max_subjects < 1:
            raise ValueError("ingress limits must be positive")
        self.max_chars = max_chars
        self.per_minute = per_minute
        self.max_subjects = max_subjects
        self.clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, subject: str, question: str) -> None:
        normalized = question.strip()
        if not normalized:
            raise IngressRejected("empty_question", 422)
        if len(normalized) > self.max_chars:
            raise IngressRejected("question_too_long", 413)
        now = self.clock()
        with self._lock:
            events = self._events.get(subject)
            if events is None:
                if len(self._events) >= self.max_subjects:
                    stale = [key for key, queue in self._events.items() if not queue or now - queue[-1] >= 60]
                    for key in stale:
                        self._events.pop(key, None)
                if len(self._events) >= self.max_subjects:
                    raise IngressRejected("rate_limit_capacity", 503)
                events = deque()
                self._events[subject] = events
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= self.per_minute:
                retry_after = max(1, int(60 - (now - events[0])))
                raise IngressRejected("rate_limited", 429, retry_after)
            events.append(now)
