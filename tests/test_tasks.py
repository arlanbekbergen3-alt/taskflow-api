import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_create_task_requires_auth():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:

        response = await client.post(
            "/tasks",
            json={
                "title": "Test task"
            }
        )

        assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_task_with_auth():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as client:

        await client.post(
            "/auth/register",
            json={
                "username": "task_user_001",
                "password": "password123"
            }
        )

        login_response = await client.post(
            "/auth/login",
            json={
                "username": "task_user_001",
                "password": "password123"
            }
        )

        token = login_response.json()["access_token"]

        response = await client.post(
            "/tasks",
            headers={
                "Authorization": f"Bearer {token}"
            },
            json={
                "title": "My test task"
            }
        )

        assert response.status_code == 201

        data = response.json()

        assert data["title"] == "My test task"
        assert "id" in data