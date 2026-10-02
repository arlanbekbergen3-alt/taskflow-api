from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base

if TYPE_CHECKING:
    from models.category import CategoryORM
    from models.user import UserORM


class TaskORM(Base):
    __tablename__ = "tasks"

    title: Mapped[str]
    completed: Mapped[bool] = mapped_column(
        default=False
    )

    category_id: Mapped[str | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        default=None
    )

    category: Mapped["CategoryORM | None"] = relationship(
        back_populates="tasks"
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    user: Mapped["UserORM"] = relationship()
