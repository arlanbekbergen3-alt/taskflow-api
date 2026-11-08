import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from repositories.refresh_token import RefreshTokenRepository
from repositories.task import TaskRepository
from services.notifier import LogNotifier, Notifier, Reminder

logger = logging.getLogger(__name__)


class MaintenanceService:
    def __init__(self, db: AsyncSession, notifier: Notifier | None = None):
        self.task_repo = TaskRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.notifier = notifier or LogNotifier()

    async def purge(self, now: datetime | None = None) -> dict[str, int]:
        now = now or datetime.now(UTC)
        tokens = await self.refresh_repo.delete_expired(now)
        tasks = await self.task_repo.purge_trash(
            now - timedelta(days=settings.TRASH_RETENTION_DAYS)
        )
        return {"refresh_tokens": tokens, "trashed_tasks": tasks}

    async def send_due_reminders(
        self, now: datetime | None = None, window: timedelta | None = None
    ) -> int:
        now = now or datetime.now(UTC)
        window = window or timedelta(hours=settings.REMINDER_WINDOW_HOURS)
        tasks = await self.task_repo.claim_due_reminders(now, now + window)
        for task in tasks:
            if task.due_date is None:
                continue
            try:
                await self.notifier.notify(
                    Reminder(
                        task_id=task.id,
                        user_id=task.user_id,
                        title=task.title,
                        due_date=task.due_date,
                    )
                )
            except Exception:
                logger.exception("Failed to send reminder for task %s", task.id)
        return len(tasks)
