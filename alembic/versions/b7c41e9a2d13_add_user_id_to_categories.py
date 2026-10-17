"""add user_id to categories

Revision ID: b7c41e9a2d13
Revises: f92e3cead050
Create Date: 2026-10-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c41e9a2d13'
down_revision: Union[str, Sequence[str], None] = 'f92e3cead050'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing categories have no owner and cannot be assigned one,
    # so they are dropped; tasks referencing them get category_id = NULL
    # via the existing ON DELETE SET NULL.
    op.execute("DELETE FROM categories")

    op.add_column('categories', sa.Column('user_id', sa.String(), nullable=False))
    op.create_foreign_key(
        'categories_user_id_fkey',
        'categories', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('categories_user_id_fkey', 'categories', type_='foreignkey')
    op.drop_column('categories', 'user_id')
