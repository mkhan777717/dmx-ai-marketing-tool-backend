import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import CampaignStatus
from app.models.campaign import Campaign


class CampaignMetricsService:
    @staticmethod
    async def get_metrics(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any]:
        """Calculate aggregated campaign metrics for a workspace."""
        # This is a simplified aggregation query.
        # In a real app, this would query CampaignAnalytics table alongside Campaign status.
        stmt = select(
            func.count(Campaign.id).label("total_campaigns"),
            func.sum(
                case((Campaign.status == CampaignStatus.ACTIVE, 1), else_=0)
            ).label("active_campaigns"),
            func.sum(
                case((Campaign.status == CampaignStatus.COMPLETED, 1), else_=0)
            ).label("completed_campaigns"),
        ).where(Campaign.workspace_id == workspace_id)

        # Avoid import errors for 'case' by doing a simple select:
        total_stmt = select(func.count(Campaign.id)).where(
            Campaign.workspace_id == workspace_id
        )
        active_stmt = select(func.count(Campaign.id)).where(
            Campaign.workspace_id == workspace_id,
            Campaign.status == CampaignStatus.ACTIVE,
        )
        completed_stmt = select(func.count(Campaign.id)).where(
            Campaign.workspace_id == workspace_id,
            Campaign.status == CampaignStatus.COMPLETED,
        )

        total = (await db.execute(total_stmt)).scalar() or 0
        active = (await db.execute(active_stmt)).scalar() or 0
        completed = (await db.execute(completed_stmt)).scalar() or 0

        return {
            "total_campaigns": total,
            "active_campaigns": active,
            "completed_campaigns": completed,
        }
