from pydantic import BaseModel, Field
from schemas.base import AppBaseModel


class TaskCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category_id: str | None = None


class TaskUpdateSchema(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None
    category_id: str | None = None


class TaskSchema(AppBaseModel):
    id: str
    title: str
    completed: bool
    category_id: str | None