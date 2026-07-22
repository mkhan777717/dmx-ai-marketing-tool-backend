import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_schedule import CampaignSchedule
from app.repositories.base import BaseRepository


class CampaignScheduleRepository(BaseRepository[CampaignSchedule]):
    def __init__(self) -> None:
        super().__init__(CampaignSchedule)

    async def get_by_campaign_id(
        self,
        db: AsyncSession,
        campaign_id: uuid.UUID,
        organization_id: uuid.UUID | None = None,
    ) -> CampaignSchedule | None:
        stmt = select(self.model).where(
            self.model.campaign_id == campaign_id
        )

        if organization_id is not None:
            stmt = stmt.where(
                self.model.organization_id == organization_id
            )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()


campaign_schedule_repo = CampaignScheduleRepository()