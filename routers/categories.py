from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.category import (CategoriesCreateSchema, CategoriesSchema, CategoriesUpdateSchema)
from services.category import CategoryService

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoriesSchema])
async def read_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    return await service.list_categories(skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoriesSchema)
async def read_category(category_id: str, db: AsyncSession = Depends(get_db)):
    service = CategoryService(db)
    return await service.find_category(category_id)


@router.post("", response_model=CategoriesSchema, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoriesCreateSchema, db: AsyncSession = Depends(get_db)
):
    service = CategoryService(db)
    return await service.add_category(name=payload.name)


@router.patch("/{category_id}", response_model=CategoriesSchema)
async def update_category(
    category_id: str,
    payload: CategoriesUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    service = CategoryService(db)
    update_data = payload.model_dump(exclude_unset=True)
    return await service.edit_category(category_id, update_data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    service = CategoryService(db)
    await service.remove_category(category_id)