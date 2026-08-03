"""add is_deleted_to_soft_delete_models

Revision ID: 9dbb1d5fef6c
Revises: f89bcb79da50
Create Date: 2026-08-03 16:12:40.024949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dbb1d5fef6c'
down_revision: Union[str, Sequence[str], None] = 'f89bcb79da50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
