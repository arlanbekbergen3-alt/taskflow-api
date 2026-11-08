import logging
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from redis.exceptions import RedisError

from core.config import settings
from core.exceptions import RateLimitError
from core.redis import get_redis

logger = logging.getLogger(__name__)


class SlidingWindowLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.limit = limit
        self.window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> int:
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


class RedisLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int):
        self._redis = redis
        self.limit = limit
        self.window = window_seconds

    async def check(self, key: str) -> int:
        redis_key = f"ratelimit:{key}"
        pipe = self._redis.pipeline()
        pipe.incr(redis_key)
        pipe.ttl(redis_key)
        count, ttl = await pipe.execute()
        if count == 1 or ttl < 0:
            await self._redis.expire(redis_key, self.window)
            ttl = self.window
        if count > self.limit:
            return max(1, ttl)
        return 0


login_limiter = SlidingWindowLimiter(
    settings.LOGIN_RATE_LIMIT_ATTEMPTS, settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS
)

RedisDep = Annotated[Redis | None, Depends(get_redis)]


async def login_rate_limit(request: Request, redis: RedisDep) -> None:
    client = request.client.host if request.client else "unknown"

    retry_after = 0
    if redis is not None:
        limiter = RedisLimiter(redis, login_limiter.limit, login_limiter.window)
        try:
            retry_after = await limiter.check(client)
        except RedisError:
            logger.warning("Redis rate limiter failed, using in-process limiter", exc_info=True)
            retry_after = login_limiter.check(client)
    else:
        retry_after = login_limiter.check(client)

    if retry_after:
        raise RateLimitError(
            "Too many login attempts, try again later",
            headers={"Retry-After": str(retry_after)},
        )
