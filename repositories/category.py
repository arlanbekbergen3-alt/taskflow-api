from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.category import CategoryORM


class CategoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
            self,
            user_id: str,
            skip: int = 0,
            limit: int = 100,
    ) -> list[CategoryORM]:
        query = (
            select(CategoryORM)
            .where(CategoryORM.user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(
            self,
            category_id: str,
            user_id: str,
    ) -> CategoryORM | None:
        query = select(CategoryORM).where(
            CategoryORM.id == category_id,
            CategoryORM.user_id == user_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, name: str, user_id: str) -> CategoryORM:
        category = CategoryORM(name=name, user_id=user_id)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def update(self, category: CategoryORM, update_data: dict) -> CategoryORM:
        for key, value in update_data.items():
            setattr(category, key, value)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete(self, category: CategoryORM) -> None:
        await self.db.delete(category)
        await self.db.commit()
