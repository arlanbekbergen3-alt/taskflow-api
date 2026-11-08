from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache import Cache
from core.exceptions import ConflictError, NotFoundError
from repositories.category import CategoryRepository
from repositories.tag import TagRepository
from repositories.task import TaskRepository


def _stats_key(user_id: str) -> str:
    return f"stats:{user_id}"


class TaskService:
    def __init__(self, db: AsyncSession, cache: Cache | None = None):
        self.cache = cache or Cache(None, 0)
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
        task = await self._save(self.task_repo.create(user_id=user_id, **fields))
        await self.cache.delete(_stats_key(user_id))
        return task

    async def edit_task(self, task_id: str, user_id: str, update_data: dict):
        task = await self.find_task(task_id=task_id, user_id=user_id)

        if "category_id" in update_data:
            await self._ensure_category_owned(update_data["category_id"], user_id)

        if "completed" in update_data and update_data["completed"] != task.completed:
            update_data["completed_at"] = datetime.now(UTC) if update_data["completed"] else None

        if "tags" in update_data:
            update_data["tags"] = await self._resolve_tags(user_id, update_data["tags"])

        if "due_date" in update_data:
            update_data["reminder_sent_at"] = None

        task = await self._save(self.task_repo.update(task, update_data))
        await self.cache.delete(_stats_key(user_id))
        return task

    async def remove_task(self, task_id: str, user_id: str):
        task = await self.find_task(task_id=task_id, user_id=user_id)
        await self.task_repo.update(task, {"deleted_at": datetime.now(UTC)})
        await self.cache.delete(_stats_key(user_id))

    async def list_trash(self, user_id: str, skip: int = 0, limit: int = 100):
        return await self.task_repo.get_all(user_id=user_id, skip=skip, limit=limit, deleted=True)

    async def restore_task(self, task_id: str, user_id: str):
        task = await self.task_repo.get_by_id(task_id=task_id, user_id=user_id, deleted=True)
        if not task:
            raise NotFoundError("Task not found in trash")
        task = await self.task_repo.update(task, {"deleted_at": None})
        await self.cache.delete(_stats_key(user_id))
        return task

    async def stats(self, user_id: str) -> tuple[dict, str]:
        if not self.cache.enabled:
            return await self._compute_stats(user_id), "BYPASS"

        cached = await self.cache.get(_stats_key(user_id))
        if cached is not None:
            return cached, "HIT"

        data = await self._compute_stats(user_id)
        await self.cache.set(_stats_key(user_id), data)
        return data, "MISS"

    async def _compute_stats(self, user_id: str) -> dict:
        data = await self.task_repo.stats(user_id)
        total, completed = data["total"], data["completed"]
        return {
            **data,
            "active": total - completed,
            "completion_rate": round(completed / total, 2) if total else 0.0,
        }
