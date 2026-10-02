from pydantic import BaseModel, Field
from schemas.base import AppBaseModel


class CategoriesCreateSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoriesUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class CategoriesSchema(AppBaseModel):
    id: str
    name: str