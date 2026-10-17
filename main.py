import logging
from fastapi import FastAPI
from routers.categories import router as categories_router
from routers.tasks import router as tasks_router
from fastapi import Request
from fastapi.responses import JSONResponse
from routers.auth import router as auth_router

logger = logging.getLogger(__name__)

app = FastAPI()

app.include_router(categories_router)
app.include_router(tasks_router)
app.include_router(auth_router)


# A middleware rather than @app.exception_handler(Exception): Starlette
# re-raises after running a 500 handler, so uvicorn would log the same
# traceback a second time. Here the exception stops at this layer.
@app.middleware("http")
async def global_exception_handler(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
