"""soft delete and due-date reminders for tasks

Revision ID: e5f7c9a1b3d4
Revises: d4e6b8a0c2f3
Create Date: 2026-11-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5f7c9a1b3d4"
down_revision: str | Sequence[str] | None = "d4e6b8a0c2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tasks", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    op.drop_column("tasks", "reminder_sent_at")
    op.drop_column("tasks", "deleted_at")
