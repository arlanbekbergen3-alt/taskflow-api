from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from core.dependencies import CurrentUser, UserServiceDep
from core.rate_limit import login_rate_limit
from schemas.user import (
    RefreshRequestSchema,
    TokenSchema,
    UserCreateSchema,
    UserSchema,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreateSchema, service: UserServiceDep):
    return await service.register(
        username=payload.username,
        password=payload.password,
    )


@router.post(
    "/login",
    response_model=TokenSchema,
    dependencies=[Depends(login_rate_limit)],
)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
):
    return await service.login(username=form.username, password=form.password)


@router.post("/refresh", response_model=TokenSchema, dependencies=[Depends(login_rate_limit)])
async def refresh(payload: RefreshRequestSchema, service: UserServiceDep):
    return await service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequestSchema, service: UserServiceDep):
    await service.logout(payload.refresh_token)


@router.get("/me", response_model=UserSchema)
async def get_me(current_user: CurrentUser):
    return current_user
