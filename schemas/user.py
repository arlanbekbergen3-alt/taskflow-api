from pydantic import BaseModel
from schemas.base import AppBaseModel


class UserCreateSchema(BaseModel):
    username: str
    password: str


class UserSchema(AppBaseModel):
    id: str
    username: str


class TokenSchema(BaseModel):
    access_token: str
    token_type: str