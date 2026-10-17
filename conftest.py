import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from core.config import settings
from db.base import Base
from db.database import get_db
from main import app


# Same server, credentials and options as the app (DATABASE_URL from .env),
# only a separate database, so tests never touch the app's data.
APP_DATABASE_URL = make_url(settings.DATABASE_URL)
TEST_DATABASE_URL = APP_DATABASE_URL.set(database="taskflow_test")

assert TEST_DATABASE_URL.database != APP_DATABASE_URL.database, (
    "Test database must differ from the app database"
)

# NullPool: pytest-asyncio runs session fixtures and tests in different
# event loops, and asyncpg connections must not be shared between loops.
engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def override_get_db():
    async with TestingSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


async def create_test_database_if_missing():
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_async_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    await create_test_database_if_missing()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def make_user(client):
    async def _make_user(username: str, password: str = "password123") -> dict:
        response = await client.post(
            "/auth/register",
            json={"username": username, "password": password},
        )
        assert response.status_code == 201

        response = await client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200

        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make_user
