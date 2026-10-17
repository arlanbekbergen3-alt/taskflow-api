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
                "title": "Test task",
                "completed": False
            }
        )

        assert response.status_code == 401


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

        assert login_response.status_code == 200

        token = login_response.json()["access_token"]

        response = await client.post(
            "/tasks",
            headers={
                "Authorization": f"Bearer {token}"
            },
            json={
                "title": "My test task",
                "completed": False
            }
        )

        assert response.status_code == 201

        data = response.json()

        assert data["title"] == "My test task"
        assert data["completed"] is False
        assert "id" in data


MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_delete_task(client, make_user):
    headers = await make_user("task_del_owner")

    created = await client.post("/tasks", headers=headers, json={"title": "To delete"})
    assert created.status_code == 201
    task_id = created.json()["id"]

    response = await client.delete(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    response = await client.get(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 404

    response = await client.delete(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_task_requires_auth(client):
    response = await client.delete(f"/tasks/{MISSING_ID}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cannot_touch_other_users_task(client, make_user):
    owner = await make_user("task_iso_owner")
    stranger = await make_user("task_iso_stranger")

    created = await client.post("/tasks", headers=owner, json={"title": "Private"})
    task_id = created.json()["id"]

    response = await client.get(f"/tasks/{task_id}", headers=stranger)
    assert response.status_code == 404

    response = await client.patch(
        f"/tasks/{task_id}", headers=stranger, json={"title": "Hacked"}
    )
    assert response.status_code == 404

    response = await client.delete(f"/tasks/{task_id}", headers=stranger)
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}

    response = await client.get("/tasks", headers=stranger)
    assert response.json() == []

    response = await client.get(f"/tasks/{task_id}", headers=owner)
    assert response.status_code == 200
    assert response.json()["title"] == "Private"


@pytest.mark.asyncio
async def test_nonexistent_task_returns_404(client, make_user):
    headers = await make_user("task_404_user")

    response = await client.get(f"/tasks/{MISSING_ID}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}

    response = await client.patch(
        f"/tasks/{MISSING_ID}", headers=headers, json={"title": "x"}
    )
    assert response.status_code == 404

    response = await client.delete(f"/tasks/{MISSING_ID}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_use_other_users_category_in_task(client, make_user):
    owner = await make_user("task_cat_owner")
    stranger = await make_user("task_cat_stranger")

    category = await client.post("/categories", headers=owner, json={"name": "Owned"})
    category_id = category.json()["id"]

    response = await client.post(
        "/tasks", headers=stranger, json={"title": "t", "category_id": category_id}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}

    task = await client.post("/tasks", headers=stranger, json={"title": "t"})
    task_id = task.json()["id"]

    response = await client.patch(
        f"/tasks/{task_id}", headers=stranger, json={"category_id": category_id}
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}

    response = await client.post(
        "/tasks", headers=owner, json={"title": "t", "category_id": category_id}
    )
    assert response.status_code == 201
    assert response.json()["category_id"] == category_id