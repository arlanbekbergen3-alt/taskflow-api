from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, computed_field, field_validator

from schemas.base import AppBaseModel, PatchModel

MAX_TAGS = 10


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


def _normalize_tags(tags: list[str]) -> list[str]:
    if len(tags) > MAX_TAGS:
        raise ValueError(f"at most {MAX_TAGS} tags per task")
    result: list[str] = []
    for tag in tags:
        tag = tag.strip().lower()
        if not 1 <= len(tag) <= 30:
            raise ValueError("tag must be 1-30 characters")
        if tag not in result:
            result.append(tag)
    return result


class TaskCreateSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    priority: Priority = Priority.medium
    due_date: AwareDatetime | None = None
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list)

    _clean_tags = field_validator("tags")(_normalize_tags)


class TaskUpdateSchema(PatchModel):
    non_nullable = ("title", "completed", "priority", "tags")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    completed: bool | None = None
    priority: Priority | None = None
    due_date: AwareDatetime | None = None
    category_id: str | None = None
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value):
        return None if value is None else _normalize_tags(value)


class TaskSchema(AppBaseModel):
    id: str
    title: str
    description: str | None
    completed: bool
    priority: Priority
    due_date: datetime | None
    completed_at: datetime | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    category_id: str | None
    tags: list[str]

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, value):
        return [getattr(tag, "name", tag) for tag in value]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_overdue(self) -> bool:
        return (
            not self.completed and self.due_date is not None and self.due_date < datetime.now(UTC)
        )


class TagSchema(BaseModel):
    name: str
    tasks_count: int


class TaskStatsSchema(BaseModel):
    total: int
    completed: int
    active: int
    overdue: int
    completion_rate: float
    by_priority: dict[Priority, int]


TaskSortField = Literal["created_at", "due_date", "priority", "title"]
SortOrder = Literal["asc", "desc"]
