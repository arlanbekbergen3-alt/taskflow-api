from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import ConflictError, NotFoundError
from repositories.category import CategoryRepository

DUPLICATE_NAME = "Category with this name already exists"


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.category_repo = CategoryRepository(db)
        self.db = db

    async def list_categories(self, user_id: str, skip: int = 0, limit: int = 100):
        return await self.category_repo.get_all(user_id=user_id, skip=skip, limit=limit)

    async def find_category(self, category_id: str, user_id: str):
        category = await self.category_repo.get_by_id(
            category_id=category_id,
            user_id=user_id,
        )
        if not category:
            raise NotFoundError("Category not found")
        return category

    async def _ensure_name_free(self, name: str, user_id: str, except_id: str | None = None):
        existing = await self.category_repo.get_by_name(name, user_id)
        if existing and existing.id != except_id:
            raise ConflictError(DUPLICATE_NAME)

    async def add_category(self, name: str, user_id: str):
        await self._ensure_name_free(name, user_id)
        try:
            return await self.category_repo.create(name=name, user_id=user_id)
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError(DUPLICATE_NAME) from None

    async def edit_category(self, category_id: str, user_id: str, update_data: dict):
        category = await self.find_category(category_id, user_id)
        if "name" in update_data:
            await self._ensure_name_free(update_data["name"], user_id, except_id=category.id)
        try:
            return await self.category_repo.update(category, update_data)
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError(DUPLICATE_NAME) from None

    async def remove_category(self, category_id: str, user_id: str):
        category = await self.find_category(category_id, user_id)
        await self.category_repo.delete(category)
