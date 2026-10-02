from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.user import UserRepository
from core.security import hash_password, verify_password, create_access_token


class UserService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)

    async def register(self, username: str, password: str):
        existing_user = await self.user_repo.get_by_username(username)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )

        password_hash = hash_password(password)

        return await self.user_repo.create(
            username=username,
            password_hash=password_hash,
        )

    async def login(self, username: str, password: str):
        user = await self.user_repo.get_by_username(username)

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        token = create_access_token(user.id)

        return {
            "access_token": token,
            "token_type": "bearer",
        }