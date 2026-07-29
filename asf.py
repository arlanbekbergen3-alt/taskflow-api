from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase, Mapped, mapped_column

DATABASE_URL = "postgresql+psycopg://postgres:admin@localhost:15432/postgres"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid4()))


class TaskORM(Base):
    __tablename__ = "tasks"

    title: Mapped[str]
    completed: Mapped[bool] = mapped_column(default=False)


class CategoryORM(Base):
    __tablename__ = "categories"

    name: Mapped[str]


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AppBaseModel(BaseModel):
    class Config:
        from_attributes = True


class CategoriesSchema(AppBaseModel):
    id: str
    name: str


class CategoriesCreateSchema(BaseModel):
    name: str


class CategoriesUpdateSchema(BaseModel):
    name: str | None = None


class TaskSchema(AppBaseModel):
    id: str
    title: str
    completed: bool


class TaskCreateSchema(BaseModel):
    title: str


class TaskUpdateSchema(BaseModel):
    title: str | None = None
    completed: bool | None = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/categories", response_model=list[CategoriesSchema])
def read_categories(db: Session = Depends(get_db)):
    return db.scalars(select(CategoryORM)).all()


@app.post("/categories", response_model=CategoriesSchema, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoriesCreateSchema, db: Session = Depends(get_db)):
    new_category = CategoryORM(name=payload.name)
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@app.patch("/categories/{category_id}", response_model=CategoriesSchema)
def update_category(category_id: str, payload: CategoriesUpdateSchema, db: Session = Depends(get_db)):
    category = db.get(CategoryORM, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)

    db.commit()
    db.refresh(category)
    return category


@app.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, db: Session = Depends(get_db)):
    category = db.get(CategoryORM, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    db.delete(category)
    db.commit()


@app.get("/tasks", response_model=list[TaskSchema])
def read_tasks(db: Session = Depends(get_db)):
    return db.scalars(select(TaskORM)).all()


@app.post("/tasks", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreateSchema, db: Session = Depends(get_db)):
    new_task = TaskORM(title=payload.title, completed=False)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.patch("/tasks/{task_id}", response_model=TaskSchema)
def update_task(payload: TaskUpdateSchema, task_id: str, db: Session = Depends(get_db)):
    task_for_update = db.get(TaskORM, task_id)
    if not task_for_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task_for_update, key, value)

    db.commit()
    db.refresh(task_for_update)
    return task_for_update


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    task = db.get(TaskORM, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    db.delete(task)
    db.commit()