"""Per-client rate limiting for starting runs.

Each run costs real API money, so a public deployment needs a brake. A
sliding window per client IP, kept in memory, matches the single-process
design; behind a load balancer this would move to Redis.
"""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 3600.0, clock=time.monotonic) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> float | None:
        """Record a hit and return None if allowed, else seconds until the next slot frees."""
        if self._limit <= 0:
            return None
        now = self._clock()
        hits = self._hits[key]
        while hits and hits[0] <= now - self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return round(hits[0] + self._window - now, 1)
        hits.append(now)
        return None
