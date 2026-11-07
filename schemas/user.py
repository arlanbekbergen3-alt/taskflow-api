from pydantic import BaseModel, Field, field_validator

from schemas.base import AppBaseModel


class UserCreateSchema(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, value: str) -> str:
        # bcrypt silently ignores (or rejects) anything past 72 bytes.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes in UTF-8")
        return value


class UserSchema(AppBaseModel):
    id: str
    username: str


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=256)
