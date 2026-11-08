import os

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from core.cache import Cache
from core.cors import configure_cors
from core.rate_limit import RedisLimiter
from main import app


@pytest.mark.asyncio
async def test_unversioned_paths_are_gone(client):
    assert (await client.get("/tasks")).status_code == 404
    assert (await client.post("/auth/login", data={})).status_code == 404


def test_every_route_is_under_v1_except_health():
    paths = app.openapi()["paths"]
    assert "/health" in paths
    assert all(p.startswith("/api/v1/") for p in paths if p != "/health")
    assert (
        app.openapi()["components"]["securitySchemes"]["OAuth2PasswordBearer"]["flows"]["password"][
            "tokenUrl"
        ]
        == "/api/v1/auth/login"
    )


async def preflight(app_, origin):
    async with AsyncClient(transport=ASGITransport(app=app_), base_url="http://test") as c:
        return await c.options(
            "/ping",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )


@pytest.mark.asyncio
async def test_cors_allows_only_listed_origins():
    api = FastAPI()
    configure_cors(api, ["https://app.example.com"])

    allowed = await preflight(api, "https://app.example.com")
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    assert "access-control-allow-credentials" not in allowed.headers

    denied = await preflight(api, "https://evil.example.com")
    assert "access-control-allow-origin" not in denied.headers


def test_cors_is_off_without_origins():
    api = FastAPI()
    configure_cors(api, [])
    assert api.user_middleware == []


@pytest.mark.asyncio
async def test_health_reports_redis_only_when_configured(client, fake_redis):
    assert (await client.get("/health")).json() == {"status": "ok", "redis": "up"}


@pytest.mark.asyncio
async def test_health_without_redis(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_stays_ok_when_redis_is_down(client, fake_redis, monkeypatch):
    async def broken():
        raise RedisConnectionError("down")

    monkeypatch.setattr(fake_redis, "ping", broken)
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "redis": "down"}


@pytest.mark.skipif(not os.getenv("REDIS_TEST_URL"), reason="REDIS_TEST_URL is not set")
@pytest.mark.asyncio
async def test_against_a_real_redis_server():
    redis = Redis.from_url(os.environ["REDIS_TEST_URL"], decode_responses=True)
    try:
        await redis.flushdb()

        limiter = RedisLimiter(redis, limit=2, window_seconds=30)
        assert [await limiter.check("real") for _ in range(2)] == [0, 0]
        assert await limiter.check("real") > 0
        assert 0 < await redis.ttl("ratelimit:real") <= 30

        cache = Cache(redis, ttl_seconds=30)
        assert await cache.get("k") is None
        await cache.set("k", {"a": [1, 2]})
        assert await cache.get("k") == {"a": [1, 2]}
        assert 0 < await redis.ttl("k") <= 30
        await cache.delete("k")
        assert await cache.get("k") is None
    finally:
        await redis.flushdb()
        await redis.aclose()
