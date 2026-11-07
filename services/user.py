import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.exceptions import ConflictError, UnauthorizedError
from core.security import create_access_token, hash_password, verify_password
from repositories.refresh_token import RefreshTokenRepository
from repositories.user import UserRepository

INVALID_REFRESH = "Invalid refresh token"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)

    async def register(self, username: str, password: str):
        if await self.user_repo.get_by_username(username):
            raise ConflictError("Username already exists")

        try:
            return await self.user_repo.create(
                username=username,
                password_hash=hash_password(password),
            )
        except IntegrityError:
            await self.db.rollback()
            raise ConflictError("Username already exists") from None

    async def _issue_tokens(self, user_id: str) -> dict:
        refresh = secrets.token_urlsafe(48)
        await self.refresh_repo.create(
            user_id=user_id,
            token_hash=_hash_token(refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        return {
            "access_token": create_access_token(user_id),
            "refresh_token": refresh,
            "token_type": "bearer",
        }

    async def login(self, username: str, password: str):
        user = await self.user_repo.get_by_username(username)

        if not verify_password(password, user.password_hash if user else None):
            raise UnauthorizedError("Invalid username or password")

        return await self._issue_tokens(user.id)

    async def refresh(self, refresh_token: str):
        now = datetime.now(UTC)
        stored = await self.refresh_repo.get_by_hash(_hash_token(refresh_token))

        if stored is None:
            raise UnauthorizedError(INVALID_REFRESH)

        if stored.revoked_at is not None:
            await self.refresh_repo.revoke_all_for_user(stored.user_id, now)
            raise UnauthorizedError(INVALID_REFRESH)

        if stored.expires_at <= now:
            raise UnauthorizedError(INVALID_REFRESH)

        if not await self.refresh_repo.revoke(stored, now):
            raise UnauthorizedError(INVALID_REFRESH)

        return await self._issue_tokens(stored.user_id)

    async def logout(self, refresh_token: str) -> None:
        stored = await self.refresh_repo.get_by_hash(_hash_token(refresh_token))
        if stored is not None and stored.revoked_at is None:
            await self.refresh_repo.revoke(stored, datetime.now(UTC))
