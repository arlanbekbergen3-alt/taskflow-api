from fastapi import FastAPI, status, HTTPException
from pydantic import BaseModel
from uuid import uuid4

app = FastAPI()

categories: list["CategoriesSchema"] = []


class CategoriesSchema(BaseModel):
    id: str
    name: str


class CategoriesCreateSchema(BaseModel):
    name: str


class CategoriesUpdateSchema(BaseModel):
    name: str | None = None


@app.get("/categories")
def read_categories():
    return categories


@app.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoriesCreateSchema):
    new_category = CategoriesSchema(
        id=str(uuid4()),
        name=payload.name
    )

    categories.append(new_category)

    return new_category


@app.patch("/categories/{category_id}")
def update_category(category_id: str,
                    payload: CategoriesUpdateSchema):
    for category in categories:

        if category.id == category_id:

            if payload.name is not None:
                category.name = payload.name

            return category

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Category not found"
    )


@app.delete("/categories/{category_id}",
            status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str):
    for category in categories:
        if category.id == category_id:
            categories.remove(category)
            return

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Category not found"
    )
