"""add user_id to categories

Revision ID: b7c41e9a2d13
Revises: f92e3cead050
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7c41e9a2d13'
down_revision: Union[str, Sequence[str], None] = 'f92e3cead050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('categories', sa.Column('user_id', sa.String(), nullable=True))

    op.execute("""
        UPDATE categories c
        SET user_id = owners.user_id
        FROM (
            SELECT category_id, MIN(user_id) AS user_id
            FROM tasks
            WHERE category_id IS NOT NULL
            GROUP BY category_id
        ) owners
        WHERE c.id = owners.category_id
    """)

    op.execute("""
        CREATE TEMPORARY TABLE category_copies ON COMMIT DROP AS
        SELECT pairs.old_id, pairs.user_id, gen_random_uuid()::text AS new_id
        FROM (
            SELECT DISTINCT t.category_id AS old_id, t.user_id
            FROM tasks t
            JOIN categories c ON c.id = t.category_id
            WHERE t.user_id <> c.user_id
        ) pairs
    """)
    op.execute("""
        INSERT INTO categories (id, name, user_id)
        SELECT cc.new_id, c.name, cc.user_id
        FROM category_copies cc
        JOIN categories c ON c.id = cc.old_id
    """)
    op.execute("""
        UPDATE tasks t
        SET category_id = cc.new_id
        FROM category_copies cc
        WHERE t.category_id = cc.old_id
          AND t.user_id = cc.user_id
    """)

    op.execute("DELETE FROM categories WHERE user_id IS NULL")

    op.alter_column('categories', 'user_id', nullable=False)
    op.create_foreign_key(
        'categories_user_id_fkey',
        'categories', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('categories_user_id_fkey', 'categories', type_='foreignkey')
    op.drop_column('categories', 'user_id')
