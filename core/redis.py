from redis.asyncio import Redis

from core.config import settings

_client: Redis | None = None


def get_redis() -> Redis | None:
    global _client
    if settings.REDIS_URL is None:
        return None
    if _client is None:
        _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
