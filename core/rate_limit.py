import math
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request

from core.config import settings
from core.exceptions import RateLimitError


class SlidingWindowLimiter:
    """In-memory sliding-window limiter.

    Per-process state: fine for one worker. With several workers/replicas
    the limit applies per process; move the counters to Redis to share them.
    """

    def __init__(self, limit: int, window_seconds: int,
                 clock: Callable[[], float] = time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> int:
        """Register a hit. Returns 0 if allowed, else seconds until retry."""
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(1, math.ceil(self.window - (now - hits[0])))
        hits.append(now)
        return 0

    def reset(self) -> None:
        self._hits.clear()


login_limiter = SlidingWindowLimiter(
    settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
)


async def login_rate_limit(request: Request) -> None:
    # request.client is the direct peer; behind a reverse proxy configure
    # uvicorn's --proxy-headers so this is the real client address.
    client = request.client.host if request.client else "unknown"
    retry_after = login_limiter.check(client)
    if retry_after:
        raise RateLimitError(
            "Too many login attempts, try again later",
            headers={"Retry-After": str(retry_after)},
        )
