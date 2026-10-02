from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, relationship
from db.base import Base

if TYPE_CHECKING:
    from models.task import TaskORM


class CategoryORM(Base):
    __tablename__ = "categories"

    name: Mapped[str]

    tasks: Mapped[list["TaskORM"]] = relationship(
        back_populates="category"
    )