import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_register():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/register", json={"username": "test_user_001", "password": "password123"}
        )

        assert response.status_code == 201
        data = response.json()

        assert data["username"] == "test_user_001"
        assert "id" in data


@pytest.mark.asyncio
async def test_login():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/auth/register", json={"username": "test_user_002", "password": "password123"}
        )

        response = await client.post(
            "/api/v1/auth/login", data={"username": "test_user_002", "password": "password123"}
        )

        assert response.status_code == 200

        data = response.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
