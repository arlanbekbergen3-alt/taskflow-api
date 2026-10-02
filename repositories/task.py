from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.task import TaskORM


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            completed: bool | None = None,
            category_id: str | None = None,
    ) -> list[TaskORM]:
        query = select(TaskORM)

        if completed is not None:
            query = query.where(TaskORM.completed == completed)

        if category_id is not None:
            query = query.where(TaskORM.category_id == category_id)

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, task_id: str) -> TaskORM | None:
        query = select(TaskORM).where(TaskORM.id == task_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(
            self,
            title: str,
            user_id: str,
            category_id: str | None = None,
    ) -> TaskORM:

        task = TaskORM(
            title=title,
            user_id=user_id,
            category_id=category_id,
        )

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
