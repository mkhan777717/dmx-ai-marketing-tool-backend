import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount
from app.models.workspace_member import WorkspaceMember


class WorkspaceMetricsService:
    @staticmethod
    async def get_metrics(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any]:
        """Calculate aggregated workspace metrics."""
        accounts_stmt = select(func.count(SocialAccount.id)).where(
            SocialAccount.workspace_id == workspace_id
        )
        members_stmt = select(func.count(WorkspaceMember.id)).where(
            WorkspaceMember.workspace_id == workspace_id
        )

        accounts = (await db.execute(accounts_stmt)).scalar() or 0
        members = (await db.execute(members_stmt)).scalar() or 0

        return {
            "connected_accounts": accounts,
            "members": members,
        }
