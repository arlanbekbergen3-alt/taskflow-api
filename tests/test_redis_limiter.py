import asyncio

import fakeredis.aioredis
import pytest
import pytest_asyncio
from redis.exceptions import ConnectionError as RedisConnectionError

from core.rate_limit import RedisLimiter, login_limiter

LOGIN = "/api/v1/auth/login"


@pytest_asyncio.fixture
async def redis():
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.mark.asyncio
async def test_blocks_after_limit_and_reports_retry_after(redis):
    limiter = RedisLimiter(redis, limit=3, window_seconds=60)

    assert [await limiter.check("a") for _ in range(3)] == [0, 0, 0]
    retry_after = await limiter.check("a")
    assert 1 <= retry_after <= 60


@pytest.mark.asyncio
async def test_keys_are_independent(redis):
    limiter = RedisLimiter(redis, limit=1, window_seconds=60)

    assert await limiter.check("a") == 0
    assert await limiter.check("a") > 0
    assert await limiter.check("b") == 0


@pytest.mark.asyncio
async def test_limit_is_shared_between_instances(redis):
    first = RedisLimiter(redis, limit=2, window_seconds=60)
    second = RedisLimiter(redis, limit=2, window_seconds=60)

    assert await first.check("ip") == 0
    assert await second.check("ip") == 0
    assert await first.check("ip") > 0
    assert await second.check("ip") > 0


@pytest.mark.asyncio
async def test_window_expires(redis):
    limiter = RedisLimiter(redis, limit=1, window_seconds=1)

    assert await limiter.check("a") == 0
    assert await limiter.check("a") > 0
    await asyncio.sleep(1.2)
    assert await limiter.check("a") == 0


@pytest.mark.asyncio
async def test_key_without_expiry_is_healed(redis):
    await redis.set("ratelimit:stuck", 100)
    limiter = RedisLimiter(redis, limit=5, window_seconds=30)

    assert await limiter.check("stuck") > 0
    assert 0 < await redis.ttl("ratelimit:stuck") <= 30


@pytest.mark.asyncio
async def test_login_endpoint_uses_redis_when_available(client, fake_redis):
    login_limiter.limit = 2
    try:
        for _ in range(2):
            response = await client.post(LOGIN, data={"username": "nobody", "password": "x" * 8})
            assert response.status_code == 401

        response = await client.post(LOGIN, data={"username": "nobody", "password": "x" * 8})
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1
        assert await fake_redis.keys("ratelimit:*")
        assert not login_limiter._hits
    finally:
        login_limiter.limit = 10


@pytest.mark.asyncio
async def test_login_falls_back_to_in_process_limiter_when_redis_fails(
    client, fake_redis, monkeypatch
):
    def broken_pipeline(*args, **kwargs):
        raise RedisConnectionError("redis is down")

    monkeypatch.setattr(fake_redis, "pipeline", broken_pipeline)
    login_limiter.limit = 2
    try:
        codes = [
            (await client.post(LOGIN, data={"username": "nobody", "password": "x" * 8})).status_code
            for _ in range(3)
        ]
        assert codes == [401, 401, 429]
    finally:
        login_limiter.limit = 10
