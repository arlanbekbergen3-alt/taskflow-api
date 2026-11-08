from datetime import datetime
from typing import Any, cast

from sqlalchemy import case, delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from models.tag import TagORM
from models.task import TaskORM

_PRIORITY_RANK = case(
    (TaskORM.priority == "high", 3),
    (TaskORM.priority == "medium", 2),
    else_=1,
)

_SORT_COLUMNS = {
    "created_at": TaskORM.created_at,
    "due_date": TaskORM.due_date,
    "priority": _PRIORITY_RANK,
    "title": TaskORM.title,
}


def _overdue_clause(now):
    return TaskORM.completed.is_(False) & TaskORM.due_date.is_not(None) & (TaskORM.due_date < now)


def _trash_clause(deleted: bool):
    return TaskORM.deleted_at.is_not(None) if deleted else TaskORM.deleted_at.is_(None)


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        completed: bool | None = None,
        category_id: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        tag: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        overdue: bool | None = None,
        sort_by: str = "created_at",
        order: str = "desc",
        now: datetime | None = None,
        deleted: bool = False,
    ) -> list[TaskORM]:
        query = select(TaskORM).where(TaskORM.user_id == user_id, _trash_clause(deleted))

        if completed is not None:
            query = query.where(TaskORM.completed == completed)

        if category_id is not None:
            query = query.where(TaskORM.category_id == category_id)

        if priority is not None:
            query = query.where(TaskORM.priority == priority)

        if search:
            query = query.where(
                TaskORM.title.icontains(search, autoescape=True)
                | TaskORM.description.icontains(search, autoescape=True)
            )

        if tag is not None:
            query = query.where(TaskORM.tags.any(TagORM.name == tag))

        if due_before is not None:
            query = query.where(TaskORM.due_date <= due_before)

        if due_after is not None:
            query = query.where(TaskORM.due_date >= due_after)

        if overdue is not None:
            clause = _overdue_clause(now or func.now())
            query = query.where(clause if overdue else ~clause)

        if deleted:
            ordering = (TaskORM.deleted_at.desc(), TaskORM.id)
        else:
            column = _SORT_COLUMNS[sort_by]
            direction = column.desc() if order == "desc" else column.asc()
            if sort_by == "due_date":
                direction = direction.nulls_last()
            ordering = (direction, TaskORM.id)
        query = query.order_by(*ordering).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        task_id: str,
        user_id: str,
        deleted: bool = False,
    ) -> TaskORM | None:
        query = select(TaskORM).where(
            TaskORM.id == task_id,
            TaskORM.user_id == user_id,
            _trash_clause(deleted),
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def stats(self, user_id: str) -> dict:
        query = select(
            func.count(),
            func.count().filter(TaskORM.completed.is_(True)),
            func.count().filter(_overdue_clause(func.now())),
            func.count().filter(TaskORM.priority == "low"),
            func.count().filter(TaskORM.priority == "medium"),
            func.count().filter(TaskORM.priority == "high"),
        ).where(TaskORM.user_id == user_id, _trash_clause(False))

        total, completed, overdue, low, medium, high = (await self.db.execute(query)).one()
        return {
            "total": total,
            "completed": completed,
            "overdue": overdue,
            "by_priority": {"low": low, "medium": medium, "high": high},
        }

    async def create(self, user_id: str, **fields) -> TaskORM:
        task = TaskORM(user_id=user_id, **fields)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update(self, task: TaskORM, update_data: dict) -> TaskORM:
        for key, value in update_data.items():
            setattr(task, key, value)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete(self, task: TaskORM) -> None:
        await self.db.delete(task)
        await self.db.commit()

    async def claim_due_reminders(self, now: datetime, until: datetime) -> list[TaskORM]:
        result = await self.db.execute(
            update(TaskORM)
            .where(
                _trash_clause(False),
                TaskORM.completed.is_(False),
                TaskORM.reminder_sent_at.is_(None),
                TaskORM.due_date.is_not(None),
                TaskORM.due_date >= now,
                TaskORM.due_date <= until,
            )
            .values(reminder_sent_at=now)
            .returning(TaskORM)
            .execution_options(populate_existing=True)
        )
        tasks = list(result.scalars().all())
        await self.db.commit()
        return tasks

    async def purge_trash(self, deleted_before: datetime) -> int:
        result = await self.db.execute(delete(TaskORM).where(TaskORM.deleted_at < deleted_before))
        await self.db.commit()
        return cast(CursorResult[Any], result).rowcount
