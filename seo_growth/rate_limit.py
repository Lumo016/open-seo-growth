from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable


class InMemoryRateLimiter:
    def __init__(self, now: Callable[[], float] | None = None):
        self._now = now or time.monotonic
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> dict[str, int | bool]:
        if limit <= 0:
            return {
                "allowed": True,
                "limit": limit,
                "remaining": 0,
                "retry_after_seconds": 0,
                "reset_seconds": 0,
            }
        now = self._now()
        events = self._events[key]
        cutoff = now - window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            retry_after = max(1, math.ceil(events[0] + window_seconds - now))
            return {
                "allowed": False,
                "limit": limit,
                "remaining": 0,
                "retry_after_seconds": retry_after,
                "reset_seconds": retry_after,
            }
        events.append(now)
        reset_seconds = max(1, math.ceil(events[0] + window_seconds - now))
        return {
            "allowed": True,
            "limit": limit,
            "remaining": max(0, limit - len(events)),
            "retry_after_seconds": 0,
            "reset_seconds": reset_seconds,
        }
