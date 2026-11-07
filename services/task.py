from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError
from repositories.category import CategoryRepository
from repositories.tag import TagRepository
from repositories.task import TaskRepository


class TaskService:
    def __init__(self, db: AsyncSession):
        self.task_repo = TaskRepository(db)
        self.category_repo = CategoryRepository(db)
        self.tag_repo = TagRepository(db)
        self.db = db

    async def list_tasks(self, user_id: str, **filters):
        return await self.task_repo.get_all(user_id=user_id, now=datetime.now(UTC), **filters)

    async def find_task(self, task_id: str, user_id: str):
        task = await self.task_repo.get_by_id(task_id=task_id, user_id=user_id)
        if not task:
            raise NotFoundError("Task not found")
        return task

    async def _ensure_category_owned(self, category_id: str | None, user_id: str):
        if category_id is None:
            return
        category = await self.category_repo.get_by_id(
            category_id=category_id,
            user_id=user_id,
        )
        if not category:
            raise NotFoundError("Category not found")

    async def _resolve_tags(self, user_id: str, names: list[str]):
        return await self.tag_repo.get_or_create_many(user_id, names)

    async def _save(self, operation):
        try:
            return await operation
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("Tag was modified concurrently, retry the request") from None

    async def list_tags(self, user_id: str):
        return [
            {"name": name, "tasks_count": count}
            for name, count in await self.tag_repo.list_with_counts(user_id)
        ]

    async def add_task(self, user_id: str, **fields):
        await self._ensure_category_owned(fields.get("category_id"), user_id)
        fields["tags"] = await self._resolve_tags(user_id, fields.get("tags", []))
        return await self._save(self.task_repo.create(user_id=user_id, **fields))

    async def edit_task(self, task_id: str, user_id: str, update_data: dict):
        task = await self.find_task(task_id=task_id, user_id=user_id)

        if "category_id" in update_data:
            await self._ensure_category_owned(update_data["category_id"], user_id)

        if "completed" in update_data and update_data["completed"] != task.completed:
            update_data["completed_at"] = datetime.now(UTC) if update_data["completed"] else None

        if "tags" in update_data:
            update_data["tags"] = await self._resolve_tags(user_id, update_data["tags"])

        return await self._save(self.task_repo.update(task, update_data))

    async def remove_task(self, task_id: str, user_id: str):
        task = await self.find_task(task_id=task_id, user_id=user_id)
        await self.task_repo.delete(task)

    async def stats(self, user_id: str) -> dict:
        data = await self.task_repo.stats(user_id)
        total, completed = data["total"], data["completed"]
        return {
            **data,
            "active": total - completed,
            "completion_rate": round(completed / total, 2) if total else 0.0,
        }
