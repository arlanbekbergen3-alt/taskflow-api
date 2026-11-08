import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Reminder:
    task_id: str
    user_id: str
    title: str
    due_date: datetime


class Notifier(Protocol):
    async def notify(self, reminder: Reminder) -> None: ...


class LogNotifier:
    async def notify(self, reminder: Reminder) -> None:
        logger.info(
            "Reminder: task %s '%s' for user %s is due at %s",
            reminder.task_id,
            reminder.title,
            reminder.user_id,
            reminder.due_date.isoformat(),
        )
