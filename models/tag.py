from sqlalchemy import Column, ForeignKey, Index, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base

task_tags = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

Index("ix_task_tags_tag_id", task_tags.c.tag_id)


class TagORM(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tags_user_id_name"),)

    name: Mapped[str] = mapped_column(String(30))
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
