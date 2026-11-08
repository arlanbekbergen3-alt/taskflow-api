import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text

from core.config import settings
from core.cors import configure_cors
from core.dependencies import DbSession
from core.exceptions import AppError
from core.logging import request_id_var, setup_logging
from core.rate_limit import RedisDep
from core.redis import close_redis
from routers.auth import router as auth_router
from routers.categories import router as categories_router
from routers.tasks import router as tasks_router

setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

API_V1_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="TaskFlow API",
    description="Personal task tracker: tasks with priorities and due dates, "
    "per-user categories, search, filters and statistics.",
    version="1.1.0",
    lifespan=lifespan,
)

app.include_router(categories_router, prefix=API_V1_PREFIX)
app.include_router(tasks_router, prefix=API_V1_PREFIX)
app.include_router(auth_router, prefix=API_V1_PREFIX)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.get("/health", tags=["Health"])
async def health(db: DbSession, redis: RedisDep):
    await db.execute(text("SELECT 1"))
    if redis is None:
        return {"status": "ok"}
    try:
        await redis.ping()
        return {"status": "ok", "redis": "up"}
    except RedisError:
        return {"status": "ok", "redis": "down"}


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


configure_cors(app, settings.CORS_ORIGINS)
