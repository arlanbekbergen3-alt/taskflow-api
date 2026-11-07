from datetime import UTC, datetime, timedelta

import pytest


def iso(dt: datetime) -> str:
    return dt.isoformat()


def in_days(n: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=n)


async def create(client, headers, **payload):
    response = await client.post("/tasks", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_task_defaults_and_new_fields(client, make_user):
    headers = await make_user("feat_defaults")

    task = await create(client, headers, title="Plain")
    assert task["priority"] == "medium"
    assert task["description"] is None
    assert task["due_date"] is None
    assert task["completed_at"] is None
    assert task["is_overdue"] is False
    assert task["created_at"] and task["updated_at"]

    due = in_days(3)
    task = await create(
        client, headers,
        title="Full", description="details", priority="high", due_date=iso(due),
    )
    assert task["priority"] == "high"
    assert task["description"] == "details"
    assert datetime.fromisoformat(task["due_date"]) == due


@pytest.mark.asyncio
async def test_invalid_priority_and_naive_due_date_rejected(client, make_user):
    headers = await make_user("feat_invalid")

    response = await client.post(
        "/tasks", headers=headers, json={"title": "t", "priority": "urgent"}
    )
    assert response.status_code == 422

    response = await client.post(
        "/tasks", headers=headers, json={"title": "t", "due_date": "2030-01-01T10:00:00"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_completed_at_follows_completed_flag(client, make_user):
    headers = await make_user("feat_completed_at")
    task = await create(client, headers, title="t")

    done = await client.patch(
        f"/tasks/{task['id']}", headers=headers, json={"completed": True}
    )
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None

    reopened = await client.patch(
        f"/tasks/{task['id']}", headers=headers, json={"completed": False}
    )
    assert reopened.json()["completed_at"] is None


@pytest.mark.asyncio
async def test_patch_null_for_required_fields_is_422_not_500(client, make_user):
    headers = await make_user("feat_null_patch")
    task = await create(client, headers, title="t")

    for field in ("title", "completed", "priority"):
        response = await client.patch(
            f"/tasks/{task['id']}", headers=headers, json={field: None}
        )
        assert response.status_code == 422, field

    await client.patch(
        f"/tasks/{task['id']}", headers=headers,
        json={"description": "x", "due_date": iso(in_days(1))},
    )
    response = await client.patch(
        f"/tasks/{task['id']}", headers=headers,
        json={"description": None, "due_date": None},
    )
    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["due_date"] is None


@pytest.mark.asyncio
async def test_filters(client, make_user):
    headers = await make_user("feat_filters")
    await create(client, headers, title="Buy milk", priority="low")
    await create(client, headers, title="Write report", description="quarterly MILK-run",
                 priority="high", due_date=iso(in_days(5)))
    late = await create(client, headers, title="Late one", priority="high",
                        due_date=iso(in_days(-2)))
    done_late = await create(client, headers, title="Done late",
                             due_date=iso(in_days(-3)))
    await client.patch(f"/tasks/{done_late['id']}", headers=headers,
                       json={"completed": True})

    def titles(response):
        assert response.status_code == 200, response.text
        return {t["title"] for t in response.json()}

    assert titles(await client.get("/tasks?priority=high", headers=headers)) == {
        "Write report", "Late one"}

    assert titles(await client.get("/tasks?q=milk", headers=headers)) == {
        "Buy milk", "Write report"}
    assert titles(await client.get("/tasks?q=%25", headers=headers)) == set()

    assert titles(await client.get("/tasks?overdue=true", headers=headers)) == {"Late one"}
    assert "Late one" not in titles(await client.get("/tasks?overdue=false", headers=headers))

    response = await client.get(f"/tasks/{late['id']}", headers=headers)
    assert response.json()["is_overdue"] is True

    assert titles(await client.get(
        "/tasks", headers=headers, params={"due_before": iso(in_days(1))})
    ) == {"Late one", "Done late"}
    assert titles(await client.get(
        "/tasks", headers=headers, params={"due_after": iso(in_days(1))})
    ) == {"Write report"}


@pytest.mark.asyncio
async def test_sorting_and_stable_pagination(client, make_user):
    headers = await make_user("feat_sorting")
    for title, priority in [("b", "medium"), ("a", "high"), ("c", "low")]:
        await create(client, headers, title=title, priority=priority)

    async def order(**params):
        response = await client.get("/tasks", headers=headers, params=params)
        assert response.status_code == 200, response.text
        return [t["title"] for t in response.json()]

    assert await order(sort_by="title", order="asc") == ["a", "b", "c"]
    assert await order(sort_by="title", order="desc") == ["c", "b", "a"]
    assert await order(sort_by="priority", order="desc") == ["a", "b", "c"]
    assert await order(sort_by="priority", order="asc") == ["c", "b", "a"]

    pages = (
        await order(sort_by="title", order="asc", skip=0, limit=2)
        + await order(sort_by="title", order="asc", skip=2, limit=2)
    )
    assert pages == ["a", "b", "c"]

    response = await client.get("/tasks?sort_by=password", headers=headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_due_date_sort_puts_tasks_without_date_last(client, make_user):
    headers = await make_user("feat_due_sort")
    await create(client, headers, title="none")
    await create(client, headers, title="soon", due_date=iso(in_days(1)))
    await create(client, headers, title="later", due_date=iso(in_days(9)))

    for order_ in ("asc", "desc"):
        response = await client.get(
            "/tasks", headers=headers, params={"sort_by": "due_date", "order": order_}
        )
        assert response.json()[-1]["title"] == "none"


@pytest.mark.asyncio
async def test_stats(client, make_user):
    headers = await make_user("feat_stats")

    response = await client.get("/tasks/stats", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "total": 0, "completed": 0, "active": 0, "overdue": 0,
        "completion_rate": 0.0,
        "by_priority": {"low": 0, "medium": 0, "high": 0},
    }

    first = await create(client, headers, title="1", priority="high")
    await create(client, headers, title="2", due_date=iso(in_days(-1)))
    await create(client, headers, title="3", priority="low")
    await create(client, headers, title="4")
    await client.patch(f"/tasks/{first['id']}", headers=headers, json={"completed": True})

    response = await client.get("/tasks/stats", headers=headers)
    assert response.json() == {
        "total": 4, "completed": 1, "active": 3, "overdue": 1,
        "completion_rate": 0.25,
        "by_priority": {"low": 1, "medium": 2, "high": 1},
    }


@pytest.mark.asyncio
async def test_stats_are_per_user_and_need_auth(client, make_user):
    owner = await make_user("feat_stats_owner")
    stranger = await make_user("feat_stats_stranger")
    await create(client, owner, title="mine")

    assert (await client.get("/tasks/stats")).status_code == 401
    assert (await client.get("/tasks/stats", headers=stranger)).json()["total"] == 0
