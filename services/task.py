from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.category import CategoryRepository
from repositories.task import TaskRepository


class TaskService:
    def __init__(self, db: AsyncSession):
        self.task_repo = TaskRepository(db)
        self.category_repo = CategoryRepository(db)

    async def list_tasks(
            self,
            skip: int = 0,
            limit: int = 100,
            completed: bool | None = None,
            category_id: str | None = None,
    ):
        return await self.task_repo.get_all(
            skip=skip,
            limit=limit,
            completed=completed,
            category_id=category_id,
        )

    async def find_task(self, task_id: str):
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return task

    async def add_task(
            self,
            title: str,
            user_id: str,
            category_id: str | None = None,
    ):
        if category_id:
            category = await self.category_repo.get_by_id(category_id)

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        return await self.task_repo.create(
            title=title,
            user_id=user_id,
            category_id=category_id,
        )

    async def edit_task(self, task_id: str, update_data: dict):
        task = await self.find_task(task_id)

        if "category_id" in update_data and update_data["category_id"] is not None:
            category = await self.category_repo.get_by_id(update_data["category_id"])
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found",
                )

        return await self.task_repo.update(task, update_data)

    async def remove_task(self, task_id: str):
        task = await self.find_task(task_id)
        await self.task_repo.delete(task)
