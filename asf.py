from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import select, ForeignKey
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin@localhost:15432/postgres"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))


class CategoryORM(Base):
    __tablename__ = "categories"

    name: Mapped[str]
    tasks: Mapped[list["TaskORM"]] = relationship(back_populates="category")


class TaskORM(Base):
    __tablename__ = "tasks"

    title: Mapped[str]
    completed: Mapped[bool] = mapped_column(default=False)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), default=None)
    category: Mapped["CategoryORM | None"] = relationship(back_populates="tasks")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CategoriesCreateSchema(BaseModel):
    name: str


class CategoriesUpdateSchema(BaseModel):
    name: str | None = None


class CategoriesSchema(AppBaseModel):
    id: str
    name: str


class TaskCreateSchema(BaseModel):
    title: str
    category_id: str | None = None


class TaskUpdateSchema(BaseModel):
    title: str | None = None
    completed: bool | None = None
    category_id: str | None = None


class TaskSchema(AppBaseModel):
    id: str
    title: str
    completed: bool
    category_id: str | None



async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        except Exception:
            await db.rollback()
            raise


@app.get("/categories", response_model=list[CategoriesSchema])
async def read_categories(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CategoryORM).offset(skip).limit(limit))
    return result.scalars().all()


@app.post("/categories", response_model=CategoriesSchema, status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoriesCreateSchema, db: AsyncSession = Depends(get_db)):
    new_category = CategoryORM(name=payload.name)
    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)
    return new_category


@app.patch("/categories/{category_id}", response_model=CategoriesSchema)
async def update_category(category_id: str, payload: CategoriesUpdateSchema, db: AsyncSession = Depends(get_db)):
    category = await db.get(CategoryORM, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    await db.commit()
    await db.refresh(category)
    return category


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    category = await db.get(CategoryORM, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    await db.delete(category)
    await db.commit()


@app.get("/tasks", response_model=list[TaskSchema])
async def read_tasks(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(TaskORM).offset(skip).limit(limit))
    return result.scalars().all()


@app.post("/tasks", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateSchema, db: AsyncSession = Depends(get_db)):
    if payload.category_id:
        category = await db.get(CategoryORM, payload.category_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    new_task = TaskORM(**payload.model_dump())
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@app.patch("/tasks/{task_id}", response_model=TaskSchema)
async def update_task(payload: TaskUpdateSchema, task_id: str, db: AsyncSession = Depends(get_db)):
    task_for_update = await db.get(TaskORM, task_id)
    if not task_for_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if payload.category_id:
        category = await db.get(CategoryORM, payload.category_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task_for_update, key, value)

    await db.commit()
    await db.refresh(task_for_update)
    return task_for_update


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await db.get(TaskORM, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    await db.delete(task)
    await db.commit()