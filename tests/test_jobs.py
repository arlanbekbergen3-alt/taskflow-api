from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from models.refresh_token import RefreshTokenORM
from models.task import TaskORM
from services.maintenance import MaintenanceService

TASKS = "/api/v1/tasks"


def in_hours(n: float) -> str:
    return (datetime.now(UTC) + timedelta(hours=n)).isoformat()


class Recorder:
    def __init__(self):
        self.sent = []

    async def notify(self, reminder):
        self.sent.append(reminder)

    def titles_for(self, user_id):
        return sorted(r.title for r in self.sent if r.user_id == user_id)


async def create(client, headers, **payload):
    response = await client.post(TASKS, headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def user_id(client, headers):
    return (await client.get("/api/v1/auth/me", headers=headers)).json()["id"]


@pytest.mark.asyncio
async def test_reminders_cover_only_open_tasks_due_soon(client, make_user, db_session):
    headers = await make_user("job_remind")
    uid = await user_id(client, headers)

    await create(client, headers, title="soon", due_date=in_hours(2))
    await create(client, headers, title="far away", due_date=in_hours(24 * 3))
    await create(client, headers, title="already late", due_date=in_hours(-1))
    await create(client, headers, title="no deadline")
    done = await create(client, headers, title="done", due_date=in_hours(1))
    await client.patch(f"{TASKS}/{done['id']}", headers=headers, json={"completed": True})
    trashed = await create(client, headers, title="trashed", due_date=in_hours(1))
    await client.delete(f"{TASKS}/{trashed['id']}", headers=headers)

    recorder = Recorder()
    await MaintenanceService(db_session, recorder).send_due_reminders()

    assert recorder.titles_for(uid) == ["soon"]


@pytest.mark.asyncio
async def test_reminder_is_sent_once_and_rearmed_by_a_new_deadline(client, make_user, db_session):
    headers = await make_user("job_rearm")
    uid = await user_id(client, headers)
    task = await create(client, headers, title="once", due_date=in_hours(2))

    first = Recorder()
    await MaintenanceService(db_session, first).send_due_reminders()
    assert first.titles_for(uid) == ["once"]

    again = Recorder()
    await MaintenanceService(db_session, again).send_due_reminders()
    assert again.titles_for(uid) == []

    await client.patch(f"{TASKS}/{task['id']}", headers=headers, json={"due_date": in_hours(5)})
    rearmed = Recorder()
    await MaintenanceService(db_session, rearmed).send_due_reminders()
    assert rearmed.titles_for(uid) == ["once"]


@pytest.mark.asyncio
async def test_failing_notifier_does_not_abort_the_job(client, make_user, db_session):
    headers = await make_user("job_notifier_fail")
    await create(client, headers, title="a", due_date=in_hours(1))
    await create(client, headers, title="b", due_date=in_hours(1))

    class Broken:
        async def notify(self, reminder):
            raise RuntimeError("smtp is down")

    sent = await MaintenanceService(db_session, Broken()).send_due_reminders()
    assert sent >= 2


@pytest.mark.asyncio
async def test_purge_removes_expired_tokens_but_keeps_revoked_ones(client, make_user, db_session):
    await make_user("job_tokens")
    expired = (
        await client.post(
            "/api/v1/auth/login", data={"username": "job_tokens", "password": "password123"}
        )
    ).json()
    revoked = (
        await client.post(
            "/api/v1/auth/login", data={"username": "job_tokens", "password": "password123"}
        )
    ).json()
    await client.post("/api/v1/auth/logout", json={"refresh_token": revoked["refresh_token"]})

    from services.user import _hash_token

    await db_session.execute(
        update(RefreshTokenORM)
        .where(RefreshTokenORM.token_hash == _hash_token(expired["refresh_token"]))
        .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
    )
    await db_session.commit()

    result = await MaintenanceService(db_session).purge()
    assert result["refresh_tokens"] >= 1

    remaining = set(
        (
            await db_session.execute(
                select(RefreshTokenORM.token_hash).where(
                    RefreshTokenORM.token_hash.in_(
                        [
                            _hash_token(expired["refresh_token"]),
                            _hash_token(revoked["refresh_token"]),
                        ]
                    )
                )
            )
        ).scalars()
    )
    assert remaining == {_hash_token(revoked["refresh_token"])}

    replay = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": revoked["refresh_token"]}
    )
    assert replay.status_code == 401


@pytest.mark.asyncio
async def test_purge_removes_only_old_trash(client, make_user, db_session):
    headers = await make_user("job_trash")
    old = await create(client, headers, title="old trash")
    recent = await create(client, headers, title="recent trash")
    live = await create(client, headers, title="live")
    for task in (old, recent):
        await client.delete(f"{TASKS}/{task['id']}", headers=headers)

    await db_session.execute(
        update(TaskORM)
        .where(TaskORM.id == old["id"])
        .values(deleted_at=datetime.now(UTC) - timedelta(days=40))
    )
    await db_session.commit()

    result = await MaintenanceService(db_session).purge()
    assert result["trashed_tasks"] >= 1

    ids = set(
        (
            await db_session.execute(
                select(TaskORM.id).where(TaskORM.id.in_([old["id"], recent["id"], live["id"]]))
            )
        ).scalars()
    )
    assert ids == {recent["id"], live["id"]}


def test_worker_registers_both_jobs():
    import worker

    names = {fn.__name__ for fn in worker.WorkerSettings.functions}
    assert names == {"purge_job", "reminders_job"}
    assert len(worker.WorkerSettings.cron_jobs) == 2


def test_worker_process_can_configure_all_mappers():
    import subprocess
    import sys
    from pathlib import Path

    code = "import worker\nfrom sqlalchemy.orm import configure_mappers\nconfigure_mappers()\n"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
