from fastapi import APIRouter, Query, status

from core.dependencies import CategoryServiceDep, CurrentUser
from schemas.category import (
    CategoriesCreateSchema,
    CategoriesSchema,
    CategoriesUpdateSchema,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoriesSchema])
async def read_categories(
    service: CategoryServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
):
    return await service.list_categories(user_id=current_user.id, skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoriesSchema)
async def read_category(
    category_id: str,
    service: CategoryServiceDep,
    current_user: CurrentUser,
):
    return await service.find_category(category_id, current_user.id)


@router.post("", response_model=CategoriesSchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoriesCreateSchema,
    service: CategoryServiceDep,
    current_user: CurrentUser,
):
    return await service.add_category(name=payload.name, user_id=current_user.id)


@router.patch("/{category_id}", response_model=CategoriesSchema)
async def update_category(
    category_id: str,
    payload: CategoriesUpdateSchema,
    service: CategoryServiceDep,
    current_user: CurrentUser,
):
    update_data = payload.model_dump(exclude_unset=True)
    return await service.edit_category(category_id, current_user.id, update_data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    service: CategoryServiceDep,
    current_user: CurrentUser,
):
    await service.remove_category(category_id, current_user.id)
