import uuid
import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, HttpUrl, Field, field_validator
from typing import Any

# Simple regex for hex color
HEX_COLOR_REGEX = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")

class BrandKitBase(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=100)
    logo_url: str | None = None
    
    primary_color: str | None = Field(None, max_length=7)
    secondary_color: str | None = Field(None, max_length=7)
    accent_color: str | None = Field(None, max_length=7)
    font_family: str | None = Field(None, max_length=100)
    
    brand_voice: str | None = Field(None, max_length=200)
    tone_of_voice: str | None = Field(None, max_length=200)
    brand_description: str | None = Field(None, max_length=1000)
    
    website_url: str | None = None
    industry: str | None = Field(None, max_length=100)
    target_audience: str | None = Field(None, max_length=1000)
    default_language: str | None = Field(None, min_length=2, max_length=10)
    
    ai_writing_instructions: str | None = Field(None, max_length=5000)
    ai_content_restrictions: str | None = Field(None, max_length=5000)

    @field_validator("primary_color", "secondary_color", "accent_color", mode="before")
    @classmethod
    def validate_hex_colors(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not HEX_COLOR_REGEX.match(v):
                raise ValueError("Must be a valid hex color code (e.g., #FFFFFF)")
        return v

    @field_validator("website_url", "logo_url", mode="before")
    @classmethod
    def validate_and_normalize_urls(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not v.startswith("http"):
                v = f"https://{v}"
        return v

    @field_validator("default_language", mode="before")
    @classmethod
    def normalize_language(cls, v: str | None) -> str | None:
        if v:
            return v.strip().lower()
        return v

class BrandKitCreate(BrandKitBase):
    workspace_id: uuid.UUID

class BrandKitCreateRequest(BrandKitBase):
    pass

class BrandKitUpdate(BrandKitBase):
    brand_name: str | None = Field(None, min_length=1, max_length=100) # Override to make optional

class BrandKitResponse(BrandKitBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
