from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from core.rate_limit import SlidingWindowLimiter, login_limiter
from models.refresh_token import RefreshTokenORM


async def login(client, username, password="password123"):
    response = await client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


async def register(client, username):
    response = await client.post(
        "/auth/register", json={"username": username, "password": "password123"}
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_login_returns_token_pair(client):
    await register(client, "sess_pair")
    tokens = await login(client, "sess_pair")
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"] and tokens["refresh_token"]
    assert tokens["access_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client):
    await register(client, "sess_rotate")
    first = await login(client, "sess_rotate")

    response = await client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]

    me = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {second['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["username"] == "sess_rotate"


@pytest.mark.asyncio
async def test_reusing_a_refresh_token_revokes_all_sessions(client):
    await register(client, "sess_reuse")
    first = await login(client, "sess_reuse")
    second = (await client.post(
        "/auth/refresh", json={"refresh_token": first["refresh_token"]})).json()

    # Replaying the already-used token looks like theft...
    replay = await client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert replay.status_code == 401
    assert replay.json() == {"detail": "Invalid refresh token"}

    # ...so the legitimate descendant is revoked too.
    response = await client.post("/auth/refresh", json={"refresh_token": second["refresh_token"]})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_unknown_and_expired_tokens(client, db_session):
    await register(client, "sess_expired")
    tokens = await login(client, "sess_expired")

    unknown = await client.post("/auth/refresh", json={"refresh_token": "nope"})
    assert unknown.status_code == 401

    await db_session.execute(
        update(RefreshTokenORM).values(
            expires_at=datetime.now(UTC) - timedelta(seconds=1)
        )
    )
    await db_session.commit()
    expired = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert expired.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token_and_is_idempotent(client):
    await register(client, "sess_logout")
    tokens = await login(client, "sess_logout")
    body = {"refresh_token": tokens["refresh_token"]}

    assert (await client.post("/auth/logout", json=body)).status_code == 204
    assert (await client.post("/auth/logout", json=body)).status_code == 204
    assert (await client.post("/auth/logout", json={"refresh_token": "unknown"})).status_code == 204

    assert (await client.post("/auth/refresh", json=body)).status_code == 401


@pytest.mark.asyncio
async def test_login_is_rate_limited(client):
    await register(client, "sess_limit")
    login_limiter.limit = 3
    try:
        for _ in range(3):
            response = await client.post(
                "/auth/login", data={"username": "sess_limit", "password": "wrong-password"}
            )
            assert response.status_code == 401

        response = await client.post(
            "/auth/login", data={"username": "sess_limit", "password": "password123"}
        )
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) >= 1
    finally:
        login_limiter.limit = 10


def test_sliding_window_limiter_forgets_old_hits():
    now = [0.0]
    limiter = SlidingWindowLimiter(2, 60, clock=lambda: now[0])

    assert limiter.check("a") == 0
    assert limiter.check("a") == 0
    assert limiter.check("a") == 60          # blocked, 60s until the oldest hit expires
    assert limiter.check("b") == 0           # keys are independent

    now[0] = 59
    assert limiter.check("a") == 1
    now[0] = 60
    assert limiter.check("a") == 0           # first hit left the window


@pytest.mark.asyncio
async def test_request_id_is_generated_and_propagated(client):
    response = await client.get("/health")
    assert len(response.headers["x-request-id"]) == 32

    response = await client.get("/health", headers={"X-Request-ID": "trace-abc"})
    assert response.headers["x-request-id"] == "trace-abc"
