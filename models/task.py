from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base
from models.tag import TagORM, task_tags

if TYPE_CHECKING:
    from models.category import CategoryORM
    from models.user import UserORM


class TaskORM(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_user_id_completed", "user_id", "completed"),
        Index("ix_tasks_category_id", "category_id"),
        Index("ix_tasks_deleted_at", "deleted_at"),
    )

    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text, default=None)
    completed: Mapped[bool] = mapped_column(default=False)
    priority: Mapped[str] = mapped_column(String(10), default="medium", server_default="medium")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), default=None
    )

    category: Mapped["CategoryORM | None"] = relationship(back_populates="tasks")

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserORM"] = relationship()

    tags: Mapped[list[TagORM]] = relationship(
        secondary=task_tags, lazy="selectin", order_by=TagORM.name
    )
