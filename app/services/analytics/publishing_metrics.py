import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import PublishStatus
from app.models.publish_history import PublishHistory


class PublishingMetricsService:
    @staticmethod
    async def get_metrics(db: AsyncSession, workspace_id: uuid.UUID) -> dict[str, Any]:
        """Calculate aggregated publishing metrics for a workspace."""
        published_stmt = select(func.count(PublishHistory.id)).where(
            PublishHistory.workspace_id == workspace_id,
            PublishHistory.status == PublishStatus.PUBLISHED,
        )
        failed_stmt = select(func.count(PublishHistory.id)).where(
            PublishHistory.workspace_id == workspace_id,
            PublishHistory.status == PublishStatus.FAILED,
        )
        pending_stmt = select(func.count(PublishHistory.id)).where(
            PublishHistory.workspace_id == workspace_id,
            PublishHistory.status == PublishStatus.PENDING,
        )

        published = (await db.execute(published_stmt)).scalar() or 0
        failed = (await db.execute(failed_stmt)).scalar() or 0
        pending = (await db.execute(pending_stmt)).scalar() or 0

        return {
            "published_posts": published,
            "failed_posts": failed,
            "pending_posts": pending,
        }
