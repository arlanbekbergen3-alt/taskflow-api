from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db
from schemas.task import TaskCreateSchema, TaskUpdateSchema, TaskSchema
from services.task import list_tasks, find_task, add_task, edit_task, remove_task


router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskSchema])
async def read_tasks(db: AsyncSession = Depends(get_db)):
    return await list_tasks(db)


@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(task_id: str, db: AsyncSession = Depends(get_db)):
    return await find_task(db, task_id)


@router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateSchema, db: AsyncSession = Depends(get_db)):
    return await add_task(db, payload)


@router.patch("/{task_id}", response_model=TaskSchema)
async def update_task(task_id: str, payload: TaskUpdateSchema, db: AsyncSession = Depends(get_db)):
    return await edit_task(db, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    await remove_task(db, task_id)