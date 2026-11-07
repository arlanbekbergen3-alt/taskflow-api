import pytest


async def create(client, headers, **payload):
    response = await client.post("/tasks", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_tags_are_normalized_and_deduplicated(client, make_user):
    headers = await make_user("tag_norm")
    task = await create(client, headers, title="t", tags=["  Work ", "work", "Urgent"])
    assert task["tags"] == ["urgent", "work"]


@pytest.mark.asyncio
async def test_tag_validation(client, make_user):
    headers = await make_user("tag_valid")

    for tags in ([""], ["   "], ["x" * 31], [f"t{i}" for i in range(11)]):
        response = await client.post("/tasks", headers=headers, json={"title": "t", "tags": tags})
        assert response.status_code == 422, tags


@pytest.mark.asyncio
async def test_replace_and_clear_tags(client, make_user):
    headers = await make_user("tag_replace")
    task = await create(client, headers, title="t", tags=["a", "b"])

    response = await client.patch(
        f"/tasks/{task['id']}", headers=headers, json={"tags": ["b", "c"]}
    )
    assert response.json()["tags"] == ["b", "c"]

    response = await client.patch(f"/tasks/{task['id']}", headers=headers, json={"tags": []})
    assert response.json()["tags"] == []

    response = await client.patch(f"/tasks/{task['id']}", headers=headers, json={"tags": None})
    assert response.status_code == 422

    await client.patch(f"/tasks/{task['id']}", headers=headers, json={"tags": ["keep"]})
    response = await client.patch(f"/tasks/{task['id']}", headers=headers, json={"title": "new"})
    assert response.json()["tags"] == ["keep"]


@pytest.mark.asyncio
async def test_filter_by_tag_and_tag_listing(client, make_user):
    headers = await make_user("tag_filter")
    await create(client, headers, title="one", tags=["home", "chore"])
    await create(client, headers, title="two", tags=["home"])
    await create(client, headers, title="three")

    response = await client.get("/tasks?tag=HOME", headers=headers)
    assert {t["title"] for t in response.json()} == {"one", "two"}

    response = await client.get("/tasks?tag=chore", headers=headers)
    assert [t["title"] for t in response.json()] == ["one"]

    response = await client.get("/tasks?tag=missing", headers=headers)
    assert response.json() == []

    response = await client.get("/tasks/tags", headers=headers)
    assert response.json() == [
        {"name": "chore", "tasks_count": 1},
        {"name": "home", "tasks_count": 2},
    ]


@pytest.mark.asyncio
async def test_tags_are_per_user(client, make_user):
    owner = await make_user("tag_owner")
    other = await make_user("tag_other")

    await create(client, owner, title="mine", tags=["shared-name"])
    task = await create(client, other, title="theirs", tags=["shared-name"])
    assert task["tags"] == ["shared-name"]

    assert (await client.get("/tasks/tags", headers=other)).json() == [
        {"name": "shared-name", "tasks_count": 1}
    ]
    assert len((await client.get("/tasks?tag=shared-name", headers=owner)).json()) == 1
    assert (await client.get("/tasks/tags")).status_code == 401


@pytest.mark.asyncio
async def test_deleting_task_keeps_tag_but_drops_the_link(client, make_user):
    headers = await make_user("tag_delete")
    task = await create(client, headers, title="t", tags=["x"])

    await client.delete(f"/tasks/{task['id']}", headers=headers)
    assert (await client.get("/tasks/tags", headers=headers)).json() == [
        {"name": "x", "tasks_count": 0}
    ]
