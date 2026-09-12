import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants.enums import ApiProvider, ContentStatus, ContentType

# --- Asset schemas for Media Attachment ---


class AssetResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    asset_type: str
    mime_type: str
    public_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# --- Base schemas for CampaignContent DB Model ---


class CampaignContentBase(BaseModel):
    title: str = Field(..., max_length=255)
    content_type: ContentType
    language: Optional[str] = Field("en", max_length=10)
    body: Optional[str] = None
    summary: Optional[str] = None
    hashtags: Optional[str] = None
    cta: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = None
    scheduled_placeholder: Optional[str] = None
    image_url: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(
        None, alias="metadata", validation_alias="metadata_"
    )

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("image_url must be a string")
        s = v.strip()
        if not s:
            return None
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError("image_url must be a valid HTTP or HTTPS URL")
        return s


class CampaignContentCreate(CampaignContentBase):
    campaign_id: uuid.UUID


class CampaignContentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content_type: Optional[ContentType] = None
    status: Optional[ContentStatus] = None
    language: Optional[str] = Field(None, max_length=10)
    body: Optional[str] = None
    summary: Optional[str] = None
    hashtags: Optional[str] = None
    cta: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=255)
    seo_description: Optional[str] = None
    scheduled_placeholder: Optional[str] = None
    image_url: Optional[str] = None
    metadata_: Optional[dict[str, Any]] = Field(
        None, alias="metadata", validation_alias="metadata_"
    )

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("image_url must be a string")
        s = v.strip()
        if not s:
            return None
        if not (s.startswith("http://") or s.startswith("https://")):
            raise ValueError("image_url must be a valid HTTP or HTTPS URL")
        return s


class CampaignContentResponse(CampaignContentBase):
    id: uuid.UUID
    campaign_id: uuid.UUID
    status: ContentStatus
    version: int
    parent_version_id: Optional[uuid.UUID]
    is_current: bool
    assets: list[AssetResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# --- Schemas for AI Generation Requests ---


class AIContentGenerateRequest(BaseModel):
    prompt: str = Field(..., description="The main prompt or topic for the AI")
    content_type: ContentType
    language: str = Field("en", max_length=10)
    brand_kit_id: Optional[uuid.UUID] = None
    tone_of_voice: Optional[str] = None
    target_audience: Optional[str] = None
    provider: ApiProvider = Field(default=ApiProvider.MOCK)


class AIContentGenerateResponse(BaseModel):
    content_type: ContentType
    body: str
    summary: Optional[str] = None
    hashtags: Optional[str] = None
    cta: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    provider_used: str
