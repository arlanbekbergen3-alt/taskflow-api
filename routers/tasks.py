from datetime import datetime

from fastapi import APIRouter, Query, status

from core.dependencies import CurrentUser, TaskServiceDep
from schemas.task import (
    Priority,
    SortOrder,
    TagSchema,
    TaskCreateSchema,
    TaskSchema,
    TaskSortField,
    TaskStatsSchema,
    TaskUpdateSchema,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskSchema])
async def read_tasks(
    service: TaskServiceDep,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    completed: bool | None = Query(None),
    category_id: str | None = Query(None),
    tag: str | None = Query(None, min_length=1, max_length=30),
    priority: Priority | None = Query(None),
    q: str | None = Query(
        None,
        min_length=1,
        max_length=100,
        description="Case-insensitive search in title and description",
    ),
    due_before: datetime | None = Query(None),
    due_after: datetime | None = Query(None),
    overdue: bool | None = Query(None, description="Not completed and past its due date"),
    sort_by: TaskSortField = Query("created_at"),
    order: SortOrder = Query("desc"),
):
    return await service.list_tasks(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        completed=completed,
        category_id=category_id,
        tag=tag.strip().lower() if tag else None,
        priority=priority.value if priority else None,
        search=q,
        due_before=due_before,
        due_after=due_after,
        overdue=overdue,
        sort_by=sort_by,
        order=order,
    )


@router.get("/tags", response_model=list[TagSchema], tags=["Tags"])
async def read_tags(service: TaskServiceDep, current_user: CurrentUser):
    return await service.list_tags(user_id=current_user.id)


@router.get("/stats", response_model=TaskStatsSchema)
async def read_task_stats(service: TaskServiceDep, current_user: CurrentUser):
    return await service.stats(user_id=current_user.id)


@router.get("/{task_id}", response_model=TaskSchema)
async def read_task(task_id: str, service: TaskServiceDep, current_user: CurrentUser):
    return await service.find_task(task_id=task_id, user_id=current_user.id)


@router.post("", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateSchema,
    service: TaskServiceDep,
    current_user: CurrentUser,
):
    fields = payload.model_dump()
    fields["priority"] = payload.priority.value
    return await service.add_task(user_id=current_user.id, **fields)


@router.patch("/{task_id}", response_model=TaskSchema)
async def update_task(
    task_id: str,
    payload: TaskUpdateSchema,
    service: TaskServiceDep,
    current_user: CurrentUser,
):
    update_data = payload.model_dump(exclude_unset=True)
    if "priority" in update_data:
        update_data["priority"] = update_data["priority"].value
    return await service.edit_task(
        task_id=task_id,
        user_id=current_user.id,
        update_data=update_data,
    )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, service: TaskServiceDep, current_user: CurrentUser):
    await service.remove_task(task_id=task_id, user_id=current_user.id)
