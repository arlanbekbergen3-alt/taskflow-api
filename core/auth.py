import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import oauth2_scheme
from db.database import get_db
from repositories.user import UserRepository

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid token",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError:
        raise _CREDENTIALS_ERROR from None

    user = await UserRepository(db).get_by_id(payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
