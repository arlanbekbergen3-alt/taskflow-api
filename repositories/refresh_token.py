from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshTokenORM


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
            self, user_id: str, token_hash: str, expires_at: datetime
    ) -> RefreshTokenORM:
        token = RefreshTokenORM(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(token)
        await self.db.commit()
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshTokenORM | None:
        result = await self.db.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(self, token: RefreshTokenORM, when: datetime) -> bool:
        result = await self.db.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.id == token.id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=when)
        )
        await self.db.commit()
        return result.rowcount == 1

    async def revoke_all_for_user(self, user_id: str, when: datetime) -> None:
        await self.db.execute(
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=when)
        )
        await self.db.commit()
