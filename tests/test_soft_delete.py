import pytest

TASKS = "/api/v1/tasks"


async def create(client, headers, **payload):
    response = await client.post(TASKS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_delete_moves_task_to_trash(client, make_user):
    headers = await make_user("trash_basic")
    task = await create(client, headers, title="to trash", tags=["x"])

    assert (await client.delete(f"{TASKS}/{task['id']}", headers=headers)).status_code == 204

    assert (await client.get(f"{TASKS}/{task['id']}", headers=headers)).status_code == 404
    assert (await client.get(TASKS, headers=headers)).json() == []
    assert (
        await client.patch(f"{TASKS}/{task['id']}", headers=headers, json={"title": "x"})
    ).status_code == 404

    trash = (await client.get(f"{TASKS}/trash", headers=headers)).json()
    assert [t["id"] for t in trash] == [task["id"]]
    assert trash[0]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_restore_brings_the_task_back_intact(client, make_user):
    headers = await make_user("trash_restore")
    task = await create(client, headers, title="keep me", priority="high", tags=["a", "b"])
    await client.delete(f"{TASKS}/{task['id']}", headers=headers)

    response = await client.post(f"{TASKS}/{task['id']}/restore", headers=headers)
    assert response.status_code == 200
    restored = response.json()
    assert restored["deleted_at"] is None
    assert (restored["title"], restored["priority"], restored["tags"]) == (
        "keep me",
        "high",
        ["a", "b"],
    )

    assert (await client.get(f"{TASKS}/{task['id']}", headers=headers)).status_code == 200
    assert (await client.get(f"{TASKS}/trash", headers=headers)).json() == []


@pytest.mark.asyncio
async def test_restore_only_works_for_trashed_tasks_of_the_owner(client, make_user):
    owner = await make_user("trash_owner")
    stranger = await make_user("trash_stranger")
    task = await create(client, owner, title="t")

    assert (await client.post(f"{TASKS}/{task['id']}/restore", headers=owner)).status_code == 404

    await client.delete(f"{TASKS}/{task['id']}", headers=owner)
    assert (await client.post(f"{TASKS}/{task['id']}/restore", headers=stranger)).status_code == 404
    assert (await client.get(f"{TASKS}/trash", headers=stranger)).json() == []
    assert (await client.post(f"{TASKS}/{task['id']}/restore")).status_code == 401


@pytest.mark.asyncio
async def test_trashed_tasks_do_not_count_anywhere(client, make_user):
    headers = await make_user("trash_counts")
    keep = await create(client, headers, title="keep", tags=["shared"])
    gone = await create(client, headers, title="gone", tags=["shared"])
    await client.delete(f"{TASKS}/{gone['id']}", headers=headers)

    stats = (await client.get(f"{TASKS}/stats", headers=headers)).json()
    assert stats["total"] == 1

    assert (await client.get(f"{TASKS}/tags", headers=headers)).json() == [
        {"name": "shared", "tasks_count": 1}
    ]
    assert [t["id"] for t in (await client.get(f"{TASKS}?tag=shared", headers=headers)).json()] == [
        keep["id"]
    ]
