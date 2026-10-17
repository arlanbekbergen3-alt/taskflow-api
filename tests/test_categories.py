import pytest


MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.asyncio
async def test_categories_require_auth(client):
    assert (await client.get("/categories")).status_code == 401
    assert (await client.get(f"/categories/{MISSING_ID}")).status_code == 401
    assert (await client.post("/categories", json={"name": "x"})).status_code == 401
    assert (
        await client.patch(f"/categories/{MISSING_ID}", json={"name": "x"})
    ).status_code == 401
    assert (await client.delete(f"/categories/{MISSING_ID}")).status_code == 401


@pytest.mark.asyncio
async def test_category_crud(client, make_user):
    headers = await make_user("cat_crud_user")

    response = await client.post("/categories", headers=headers, json={"name": "Work"})
    assert response.status_code == 201
    category = response.json()
    assert category["name"] == "Work"
    category_id = category["id"]

    response = await client.get("/categories", headers=headers)
    assert response.status_code == 200
    assert response.json() == [{"id": category_id, "name": "Work"}]

    response = await client.get(f"/categories/{category_id}", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"id": category_id, "name": "Work"}

    response = await client.patch(
        f"/categories/{category_id}", headers=headers, json={"name": "Home"}
    )
    assert response.status_code == 200
    assert response.json() == {"id": category_id, "name": "Home"}

    response = await client.delete(f"/categories/{category_id}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""

    response = await client.get(f"/categories/{category_id}", headers=headers)
    assert response.status_code == 404

    response = await client.get("/categories", headers=headers)
    assert response.json() == []


@pytest.mark.asyncio
async def test_category_validation(client, make_user):
    headers = await make_user("cat_valid_user")

    response = await client.post("/categories", headers=headers, json={"name": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_categories_are_per_user(client, make_user):
    owner = await make_user("cat_iso_owner")
    stranger = await make_user("cat_iso_stranger")

    response = await client.post("/categories", headers=owner, json={"name": "Secret"})
    category_id = response.json()["id"]

    response = await client.get("/categories", headers=stranger)
    assert response.status_code == 200
    assert response.json() == []

    response = await client.get(f"/categories/{category_id}", headers=stranger)
    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}

    response = await client.patch(
        f"/categories/{category_id}", headers=stranger, json={"name": "Hacked"}
    )
    assert response.status_code == 404

    response = await client.delete(f"/categories/{category_id}", headers=stranger)
    assert response.status_code == 404

    response = await client.get(f"/categories/{category_id}", headers=owner)
    assert response.status_code == 200
    assert response.json()["name"] == "Secret"


@pytest.mark.asyncio
async def test_nonexistent_category_returns_404(client, make_user):
    headers = await make_user("cat_404_user")

    response = await client.get(f"/categories/{MISSING_ID}", headers=headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Category not found"}

    response = await client.patch(
        f"/categories/{MISSING_ID}", headers=headers, json={"name": "x"}
    )
    assert response.status_code == 404

    response = await client.delete(f"/categories/{MISSING_ID}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_category_unlinks_tasks(client, make_user):
    headers = await make_user("cat_unlink_user")

    category = await client.post("/categories", headers=headers, json={"name": "Tmp"})
    category_id = category.json()["id"]

    task = await client.post(
        "/tasks", headers=headers, json={"title": "t", "category_id": category_id}
    )
    task_id = task.json()["id"]

    response = await client.delete(f"/categories/{category_id}", headers=headers)
    assert response.status_code == 204

    response = await client.get(f"/tasks/{task_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["category_id"] is None
