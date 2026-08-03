import uuid
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import CampaignStatus
from app.models.campaign import Campaign
from app.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    async def get_by_workspace_id(
        self, db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Campaign]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        status: CampaignStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Campaign]:
        stmt = (
            select(self.model)
            .where(self.model.workspace_id == workspace_id, self.model.status == status)
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def search_campaigns(
        self,
        db: AsyncSession,
        workspace_id: uuid.UUID,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Campaign]:
        search_pattern = f"%{query}%"
        stmt = (
            select(self.model)
            .where(
                self.model.workspace_id == workspace_id,
                or_(
                    self.model.campaign_name.ilike(search_pattern),
                    self.model.description.ilike(search_pattern),
                    self.model.objective.ilike(search_pattern),
                ),
            )
            .offset(skip)
            .limit(limit)
            .order_by(self.model.created_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()


campaign_repo = CampaignRepository(Campaign)
