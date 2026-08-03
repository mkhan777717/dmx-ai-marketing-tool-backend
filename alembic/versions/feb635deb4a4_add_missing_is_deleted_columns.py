from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "feb635deb4a4"
down_revision: Union[str, Sequence[str], None] = "9dbb1d5fef6c"
branch_labels = None
depends_on = None


TABLES = [
    "users",
    "workspaces",
    "workspace_members",
    "campaigns",
    "assets",
    "brand_kits",
    "campaign_content",
    "social_accounts",
    "publish_history",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, "is_deleted")
