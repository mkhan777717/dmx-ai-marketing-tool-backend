import uuid
from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.campaign import Campaign
from app.constants.enums import CampaignStatus
from datetime import datetime, timezone

class CampaignRepository(BaseRepository[Campaign]):
    async def get_by_workspace(self, db: AsyncSession, workspace_id: uuid.UUID, limit: int = 100, offset: int = 0) -> Sequence[Campaign]:
        stmt = select(self.model).where(
            self.model.workspace_id == workspace_id,
            self.model.deleted_at.is_(None)
        ).options(
            selectinload(self.model.assets)
        ).order_by(desc(self.model.created_at)).limit(limit).offset(offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_id_and_workspace(self, db: AsyncSession, workspace_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign | None:
        stmt = select(self.model).where(
            self.model.id == campaign_id,
            self.model.workspace_id == workspace_id,
            self.model.deleted_at.is_(None)
        ).options(
            selectinload(self.model.assets)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_name(self, db: AsyncSession, workspace_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None) -> bool:
        conditions = [
            self.model.workspace_id == workspace_id,
            self.model.campaign_name == name,
            self.model.deleted_at.is_(None)
        ]
        if exclude_id:
            conditions.append(self.model.id != exclude_id)
            
        stmt = select(self.model).where(and_(*conditions))
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def soft_delete(self, db: AsyncSession, campaign: Campaign) -> bool:
        campaign.deleted_at = datetime.now(timezone.utc)
        campaign.status = CampaignStatus.ARCHIVED
        db.add(campaign)
        await db.flush()
        return True

    async def add_asset(self, db: AsyncSession, campaign: Campaign, asset) -> None:
        if asset not in campaign.assets:
            campaign.assets.append(asset)
            db.add(campaign)
            await db.flush()
            
    async def remove_asset(self, db: AsyncSession, campaign: Campaign, asset) -> None:
        if asset in campaign.assets:
            campaign.assets.remove(asset)
            db.add(campaign)
            await db.flush()

campaign_repo = CampaignRepository(Campaign)
