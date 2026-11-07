import jwt
import pytest

from core.config import settings


@pytest.mark.asyncio
async def test_me_does_not_leak_password_hash(client, make_user):
    headers = await make_user("hard_me_user")

    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert set(response.json()) == {"id", "username"}


@pytest.mark.asyncio
async def test_register_validation(client):
    async def register(username, password):
        return await client.post(
            "/auth/register", json={"username": username, "password": password}
        )

    assert (await register("ab", "password123")).status_code == 422
    assert (await register("bad name!", "password123")).status_code == 422
    assert (await register("hard_short_pw", "short")).status_code == 422
    assert (await register("hard_long_pw", "x" * 73)).status_code == 422
    assert (await register("hard_utf8_pw", "я" * 40)).status_code == 422
    assert (await register("hard_ok_user", "password123")).status_code == 201


@pytest.mark.asyncio
async def test_duplicate_username_is_409(client):
    payload = {"username": "hard_dup_user", "password": "password123"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201

    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}


@pytest.mark.asyncio
async def test_login_failures_are_indistinguishable(client, make_user):
    await make_user("hard_login_user")

    wrong_password = await client.post(
        "/auth/login", data={"username": "hard_login_user", "password": "wrong-password"}
    )
    unknown_user = await client.post(
        "/auth/login", data={"username": "hard_nobody", "password": "password123"}
    )
    for response in (wrong_password, unknown_user):
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid username or password"}
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_json_login_is_no_longer_accepted(client):
    response = await client.post("/auth/login", json={"username": "x", "password": "password123"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_bad_tokens_are_rejected(client, make_user):
    headers = await make_user("hard_token_user")
    me = (await client.get("/auth/me", headers=headers)).json()

    garbage = {"Authorization": "Bearer not-a-token"}
    assert (await client.get("/auth/me", headers=garbage)).status_code == 401

    forged = jwt.encode({"sub": me["id"], "exp": 4102444800}, "x" * 40, "HS256")
    assert (
        await client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    ).status_code == 401

    expired = jwt.encode(
        {"sub": me["id"], "exp": 1}, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM
    )
    assert (
        await client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    ).status_code == 401

    no_exp = jwt.encode({"sub": me["id"]}, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM)
    assert (
        await client.get("/auth/me", headers={"Authorization": f"Bearer {no_exp}"})
    ).status_code == 401

    ghost = jwt.encode(
        {"sub": "missing", "exp": 4102444800}, settings.JWT_SECRET_KEY, settings.JWT_ALGORITHM
    )
    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {ghost}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
