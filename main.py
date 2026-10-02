from fastapi import FastAPI
from routers.categories import router as categories_router
from routers.tasks import router as tasks_router
from fastapi import Request
from fastapi.responses import JSONResponse
from routers.auth import router as auth_router

app = FastAPI()

app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(auth_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
