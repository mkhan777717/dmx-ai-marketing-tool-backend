import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.constants.enums import CampaignStatus
from app.schemas.asset import AssetResponse

class CampaignBase(BaseModel):
    campaign_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    objective: str | None = Field(None, max_length=255)
    campaign_type: str | None = Field(None, max_length=100)
    target_channels: str | None = Field(None, max_length=1000)
    
    status: CampaignStatus = CampaignStatus.DRAFT
    budget: float | None = Field(None, ge=0)
    currency: str | None = Field("USD", min_length=3, max_length=3)
    
    start_date: datetime | None = None
    end_date: datetime | None = None
    
    brand_kit_id: uuid.UUID | None = None

class CampaignCreate(CampaignBase):
    workspace_id: uuid.UUID
    owner_id: uuid.UUID | None = None

class CampaignCreateRequest(CampaignBase):
    pass

class CampaignUpdate(BaseModel):
    campaign_name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    objective: str | None = Field(None, max_length=255)
    campaign_type: str | None = Field(None, max_length=100)
    target_channels: str | None = Field(None, max_length=1000)
    status: CampaignStatus | None = None
    budget: float | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    start_date: datetime | None = None
    end_date: datetime | None = None
    brand_kit_id: uuid.UUID | None = None

class CampaignResponse(CampaignBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    assets: list[AssetResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
