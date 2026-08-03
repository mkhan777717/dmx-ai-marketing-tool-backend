"""phase_2e_supabase_auth

Revision ID: 2e_supabase_auth
Revises: 2d_members_invites
Create Date: 2026-07-15 11:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e_supabase_auth"
down_revision: Union[str, None] = "2d_members_invites"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove custom auth fields
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "last_login")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "two_factor_enabled")
    op.drop_column("users", "is_verified")

    # Add supabase auth fields
    op.add_column("users", sa.Column("supabase_user_id", sa.UUID(), nullable=False))
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(
        op.f("ix_users_supabase_user_id"), "users", ["supabase_user_id"], unique=True
    )


def downgrade() -> None:
    # Revert supabase auth fields
    op.drop_index(op.f("ix_users_supabase_user_id"), table_name="users")
    op.drop_column("users", "supabase_user_id")
    op.drop_column("users", "is_verified")

    # Revert to custom auth fields
    op.add_column(
        "users",
        sa.Column("is_verified", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled", sa.BOOLEAN(), autoincrement=False, nullable=False
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at", sa.DateTime(), autoincrement=False, nullable=True
        ),
    )
    op.add_column(
        "users",
        sa.Column("last_login", sa.DateTime(), autoincrement=False, nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("hashed_password", sa.VARCHAR(), autoincrement=False, nullable=False),
    )
