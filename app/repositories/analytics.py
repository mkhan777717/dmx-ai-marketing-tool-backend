import uuid
from datetime import date
from typing import Optional, Sequence

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import SnapshotType
from app.models.ai_usage import AIUsage
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.models.campaign_analytics import CampaignAnalytics
from app.repositories.base import BaseRepository


class AnalyticsSnapshotRepository(BaseRepository[AnalyticsSnapshot]):
    async def get_by_date_and_type(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        snapshot_date: date,
        snapshot_type: SnapshotType,
    ) -> Optional[AnalyticsSnapshot]:
        stmt = select(self.model).where(
            and_(
                self.model.workspace_id == workspace_id,
                self.model.snapshot_date == snapshot_date,
                self.model.snapshot_type == snapshot_type,
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_snapshot(
        self, db: AsyncSession, workspace_id: uuid.UUID, snapshot_type: SnapshotType
    ) -> Optional[AnalyticsSnapshot]:
        stmt = (
            select(self.model)
            .where(
                and_(
                    self.model.workspace_id == workspace_id,
                    self.model.snapshot_type == snapshot_type,
                )
            )
            .order_by(desc(self.model.snapshot_date))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


class CampaignAnalyticsRepository(BaseRepository[CampaignAnalytics]):
    async def get_by_campaign_id(
        self, db: AsyncSession, campaign_id: uuid.UUID
    ) -> Optional[CampaignAnalytics]:
        stmt = select(self.model).where(self.model.campaign_id == campaign_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_workspace_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[CampaignAnalytics]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


class AIUsageRepository(BaseRepository[AIUsage]):
    async def get_by_workspace_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[AIUsage]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


analytics_snapshot_repo = AnalyticsSnapshotRepository(AnalyticsSnapshot)
campaign_analytics_repo = CampaignAnalyticsRepository(CampaignAnalytics)
ai_usage_repo = AIUsageRepository(AIUsage)
