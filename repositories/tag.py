from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.tag import TagORM, task_tags


class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_many(self, user_id: str, names: list[str]) -> list[TagORM]:
        if not names:
            return []
        result = await self.db.execute(
            select(TagORM).where(TagORM.user_id == user_id, TagORM.name.in_(names))
        )
        by_name = {tag.name: tag for tag in result.scalars()}
        for name in names:
            if name not in by_name:
                tag = TagORM(name=name, user_id=user_id)
                self.db.add(tag)
                by_name[name] = tag
        await self.db.flush()
        return [by_name[name] for name in names]

    async def list_with_counts(self, user_id: str) -> list[tuple[str, int]]:
        query = (
            select(TagORM.name, func.count(task_tags.c.task_id))
            .outerjoin(task_tags, task_tags.c.tag_id == TagORM.id)
            .where(TagORM.user_id == user_id)
            .group_by(TagORM.id, TagORM.name)
            .order_by(TagORM.name)
        )
        return [(name, count) for name, count in (await self.db.execute(query)).all()]
