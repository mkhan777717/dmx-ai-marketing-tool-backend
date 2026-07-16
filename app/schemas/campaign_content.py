import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.constants.enums import ContentType, ContentStatus
from app.schemas.asset import AssetResponse

class CampaignContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content_type: ContentType
    status: ContentStatus = ContentStatus.DRAFT
    language: str | None = Field(None, max_length=10)
    
    body: str | None = None
    summary: str | None = None
    hashtags: str | None = None
    cta: str | None = None
    
    seo_title: str | None = Field(None, max_length=255)
    seo_description: str | None = None
    
    scheduled_placeholder: str | None = None
    metadata_: dict | None = Field(None, alias="metadata")

class CampaignContentCreate(CampaignContentBase):
    campaign_id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID | None = None

class CampaignContentCreateRequest(CampaignContentBase):
    pass

class CampaignContentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    content_type: ContentType | None = None
    status: ContentStatus | None = None
    language: str | None = Field(None, max_length=10)
    
    body: str | None = None
    summary: str | None = None
    hashtags: str | None = None
    cta: str | None = None
    
    seo_title: str | None = Field(None, max_length=255)
    seo_description: str | None = None
    
    scheduled_placeholder: str | None = None
    metadata_: dict | None = Field(None, alias="metadata")

class CampaignContentResponse(CampaignContentBase):
    id: uuid.UUID
    campaign_id: uuid.UUID
    workspace_id: uuid.UUID
    
    version: int
    parent_version_id: uuid.UUID | None = None
    is_current: bool
    
    created_at: datetime
    updated_at: datetime
    
    assets: list[AssetResponse] = []
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
