import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

STATS = "/api/v1/tasks/stats"


async def current_user_id(client, headers):
    return (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]


async def create(client, headers, **payload):
    response = await client.post("/api/v1/tasks", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_stats_without_redis_bypasses_cache(client, make_user):
    headers = await make_user("cache_bypass")
    response = await client.get(STATS, headers=headers)
    assert response.status_code == 200
    assert response.headers["x-cache"] == "BYPASS"


@pytest.mark.asyncio
async def test_stats_miss_then_hit_with_ttl(client, make_user, fake_redis):
    headers = await make_user("cache_hit")
    user_id = await current_user_id(client, headers)
    await create(client, headers, title="one", priority="high")

    first = await client.get(STATS, headers=headers)
    assert first.headers["x-cache"] == "MISS"

    second = await client.get(STATS, headers=headers)
    assert second.headers["x-cache"] == "HIT"
    assert second.json() == first.json()

    ttl = await fake_redis.ttl(f"stats:{user_id}")
    assert 0 < ttl <= 60


@pytest.mark.asyncio
async def test_every_task_change_invalidates_the_cache(client, make_user, fake_redis):
    headers = await make_user("cache_invalidate")

    async def stats():
        response = await client.get(STATS, headers=headers)
        return response.headers["x-cache"], response.json()

    assert (await stats())[0] == "MISS"
    assert (await stats())[0] == "HIT"

    task = await create(client, headers, title="t")
    state, data = await stats()
    assert (state, data["total"]) == ("MISS", 1)

    await client.patch(f"/api/v1/tasks/{task['id']}", headers=headers, json={"completed": True})
    state, data = await stats()
    assert (state, data["completed"]) == ("MISS", 1)

    await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    state, data = await stats()
    assert (state, data["total"]) == ("MISS", 0)

    await client.post(f"/api/v1/tasks/{task['id']}/restore", headers=headers)
    state, data = await stats()
    assert (state, data["total"]) == ("MISS", 1)


@pytest.mark.asyncio
async def test_cache_is_per_user(client, make_user, fake_redis):
    first = await make_user("cache_user_a")
    second = await make_user("cache_user_b")
    await create(client, first, title="mine")

    await client.get(STATS, headers=first)
    await client.get(STATS, headers=second)

    assert (await client.get(STATS, headers=first)).json()["total"] == 1
    assert (await client.get(STATS, headers=second)).json()["total"] == 0


@pytest.mark.asyncio
async def test_redis_failure_never_breaks_requests(client, make_user, fake_redis, monkeypatch):
    headers = await make_user("cache_outage")

    async def broken(*args, **kwargs):
        raise RedisConnectionError("redis is down")

    for method in ("get", "set", "delete"):
        monkeypatch.setattr(fake_redis, method, broken)

    response = await client.get(STATS, headers=headers)
    assert response.status_code == 200
    assert response.headers["x-cache"] == "MISS"

    created = await client.post("/api/v1/tasks", headers=headers, json={"title": "still works"})
    assert created.status_code == 201
    assert (await client.get(STATS, headers=headers)).json()["total"] == 1
