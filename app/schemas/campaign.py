import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.constants.enums import CampaignStatus


class CampaignBase(BaseModel):
    campaign_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    objective: Optional[str] = Field(None, max_length=255)
    campaign_type: Optional[str] = Field(None, max_length=100)
    target_channels: Optional[str] = Field(
        None, description="Comma-separated list of target channels"
    )
    budget: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field("USD", max_length=3)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    brand_kit_id: Optional[uuid.UUID] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    campaign_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    objective: Optional[str] = Field(None, max_length=255)
    campaign_type: Optional[str] = Field(None, max_length=100)
    target_channels: Optional[str] = None
    budget: Optional[float] = Field(None, ge=0.0)
    currency: Optional[str] = Field(None, max_length=3)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    brand_kit_id: Optional[uuid.UUID] = None


class CampaignStatusUpdate(BaseModel):
    status: CampaignStatus


class CampaignResponse(CampaignBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    owner_id: uuid.UUID
    status: CampaignStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
