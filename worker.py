import logging

from arq import cron
from arq.connections import RedisSettings

from core.config import settings
from core.logging import setup_logging
from db.database import AsyncSessionLocal
from services.maintenance import MaintenanceService

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
    if settings.REDIS_URL is None:
        raise RuntimeError("REDIS_URL is required to run the worker")


async def purge_job(ctx: dict) -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        result = await MaintenanceService(db).purge()
    logger.info("Purge finished: %s", result)
    return result


async def reminders_job(ctx: dict) -> int:
    async with AsyncSessionLocal() as db:
        sent = await MaintenanceService(db).send_due_reminders()
    logger.info("Reminders sent: %d", sent)
    return sent


class WorkerSettings:
    functions = [purge_job, reminders_job]
    cron_jobs = [
        cron(purge_job, hour=3, minute=0, run_at_startup=True),
        cron(reminders_job, minute={0, 15, 30, 45}),
    ]
    on_startup = startup
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL or "redis://localhost:6379")
