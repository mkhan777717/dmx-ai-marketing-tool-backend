import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.constants.enums import ScheduleStatus


class CampaignScheduleBase(BaseModel):
    publish_date: datetime
    timezone: str = Field(default="UTC", description="Timezone for the publish date")


class CampaignScheduleCreate(CampaignScheduleBase):
    pass


class CampaignScheduleUpdate(BaseModel):
    publish_date: Optional[datetime] = None
    timezone: Optional[str] = None
    status: Optional[ScheduleStatus] = None


class CampaignScheduleResponse(CampaignScheduleBase):
    id: uuid.UUID
    campaign_id: uuid.UUID
    status: ScheduleStatus
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
