import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.config import settings
from core.dependencies import DbSession
from core.exceptions import AppError
from core.logging import request_id_var, setup_logging
from routers.auth import router as auth_router
from routers.categories import router as categories_router
from routers.tasks import router as tasks_router

setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TaskFlow API",
    description="Personal task tracker: tasks with priorities and due dates, "
                "per-user categories, search, filters and statistics.",
    version="1.0.0",
)

app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(auth_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.get("/health", tags=["Health"])
async def health(db: DbSession):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request_id_var.set(request_id[:64])
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})

    response.headers["X-Request-ID"] = request_id_var.get()
    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response
