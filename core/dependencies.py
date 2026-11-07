"""Dependency providers: routers ask for a ready service instead of
building it by hand in every endpoint."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth import get_current_user
from db.database import get_db
from models.user import UserORM
from services.category import CategoryService
from services.task import TaskService
from services.user import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[UserORM, Depends(get_current_user)]


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_category_service(db: DbSession) -> CategoryService:
    return CategoryService(db)


def get_task_service(db: DbSession) -> TaskService:
    return TaskService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
