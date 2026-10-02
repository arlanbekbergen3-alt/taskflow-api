from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.user import UserCreateSchema, UserSchema, TokenSchema
from services.user import UserService

from fastapi import Depends
from core.auth import get_current_user
from models.user import UserORM


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)

    return await service.register(
        username=payload.username,
        password=payload.password,
    )


@router.post("/login", response_model=TokenSchema)
async def login(
    payload: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)

    return await service.login(
        username=payload.username,
        password=payload.password,
    )


@router.get("/me")
async def get_me(current_user: UserORM = Depends(get_current_user)):
    return current_user