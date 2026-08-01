import uuid
from typing import Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_content import CampaignContent
from app.repositories.base import BaseRepository


class CampaignContentRepository(BaseRepository[CampaignContent]):
    async def get_by_campaign_id(
        self, db: AsyncSession, campaign_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[CampaignContent]:
        """
        Get all content associated with a campaign.
        """
        stmt = (
            select(self.model)
            .where(self.model.campaign_id == campaign_id)
            .offset(skip)
            .limit(limit)
            .order_by(desc(self.model.created_at))
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_latest_version(
        self, db: AsyncSession, campaign_id: uuid.UUID, content_type: str, language: str
    ) -> CampaignContent | None:
        """
        Get the latest version of a specific content type and language for a campaign.
        """
        stmt = (
            select(self.model)
            .where(
                self.model.campaign_id == campaign_id,
                self.model.content_type == content_type,
                self.model.language == language,
                self.model.is_current,
            )
            .order_by(desc(self.model.version))
            .limit(1)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


campaign_content_repo = CampaignContentRepository(CampaignContent)
