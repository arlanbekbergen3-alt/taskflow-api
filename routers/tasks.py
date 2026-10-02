from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.task import TaskCreateSchema, TaskSchema, TaskUpdateSchema
from services.task import TaskService
from core.auth import get_current_user
from models.user import UserORM

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskSchema])
async def read_tasks(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        completed: bool | None = Query(None),
        category_id: str | None = Query(None),
        db: AsyncSession = Depends(get_db),
):
    service = TaskService(db)
    return await service.list_tasks(
        skip=skip,
        limit=limit,
        completed=completed,
        category_id=category_id,
    )


@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    return await service.find_task(task_id)


@router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateSchema, db: AsyncSession = Depends(get_db), current_user: UserORM = Depends(get_current_user)):
    service = TaskService(db)
    return await service.add_task(
        title=payload.title,
        user_id=current_user.id,
        category_id=payload.category_id,
    )


@router.patch("/{task_id}", response_model=TaskSchema)
async def update_task(
        task_id: str, payload: TaskUpdateSchema, db: AsyncSession = Depends(get_db)
):
    service = TaskService(db)
    update_data = payload.model_dump(exclude_unset=True)
    return await service.edit_task(task_id, update_data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    await service.remove_task(task_id)
