"""task details (description, priority, due date, timestamps), unique categories

Revision ID: c3d5a7e9f1b2
Revises: b7c41e9a2d13
Create Date: 2026-11-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d5a7e9f1b2'
down_revision: Union[str, Sequence[str], None] = 'b7c41e9a2d13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tasks', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('tasks', sa.Column(
        'priority', sa.String(length=10), nullable=False, server_default='medium'))
    op.add_column('tasks', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column(
        'created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('tasks', sa.Column(
        'updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index('ix_tasks_user_id_completed', 'tasks', ['user_id', 'completed'])
    op.create_index('ix_tasks_category_id', 'tasks', ['category_id'])

    # Existing duplicates (same user, same name) would block the unique
    # constraint: keep the first one as is, number the rest.
    op.execute("""
        UPDATE categories c
        SET name = c.name || ' (' || d.rn || ')'
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id, name ORDER BY id) AS rn
            FROM categories
        ) d
        WHERE c.id = d.id AND d.rn > 1
    """)
    op.create_unique_constraint(
        'uq_categories_user_id_name', 'categories', ['user_id', 'name'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_categories_user_id_name', 'categories', type_='unique')
    op.drop_index('ix_tasks_category_id', table_name='tasks')
    op.drop_index('ix_tasks_user_id_completed', table_name='tasks')
    op.drop_column('tasks', 'updated_at')
    op.drop_column('tasks', 'created_at')
    op.drop_column('tasks', 'completed_at')
    op.drop_column('tasks', 'due_date')
    op.drop_column('tasks', 'priority')
    op.drop_column('tasks', 'description')
