import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class Cache:
    def __init__(self, redis: Redis | None, ttl_seconds: int):
        self._redis = redis
        self._ttl = ttl_seconds

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    async def get(self, key: str) -> Any | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(key)
        except RedisError:
            logger.warning("Cache read failed for %s", key, exc_info=True)
            return None
        return None if raw is None else json.loads(raw)

    async def set(self, key: str, value: Any) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(key, json.dumps(value), ex=self._ttl)
        except RedisError:
            logger.warning("Cache write failed for %s", key, exc_info=True)

    async def delete(self, key: str) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(key)
        except RedisError:
            logger.warning("Cache invalidation failed for %s", key, exc_info=True)
