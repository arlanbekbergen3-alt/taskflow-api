from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.category import CategoryRepository


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.category_repo = CategoryRepository(db)
        self.db = db

    async def list_categories(self, skip: int = 0, limit: int = 100):
        return await self.category_repo.get_all(skip=skip, limit=limit)

    async def find_category(self, category_id: str):
        category = await self.category_repo.get_by_id(category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        return category

    async def add_category(self, name: str):
        return await self.category_repo.create(name=name)

    async def edit_category(self, category_id: str, update_data: dict):
        category = await self.find_category(category_id)
        return await self.category_repo.update(category, update_data)

    async def remove_category(self, category_id: str):
        category = await self.find_category(category_id)
        await self.category_repo.delete(category)