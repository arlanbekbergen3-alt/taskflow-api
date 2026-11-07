from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.task import TaskORM
    from models.user import UserORM


class CategoryORM(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_categories_user_id_name"),)

    name: Mapped[str]

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["UserORM"] = relationship()

    tasks: Mapped[list["TaskORM"]] = relationship(back_populates="category")
