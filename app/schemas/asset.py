import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.constants.enums import AssetType, AssetStatus

class AssetBase(BaseModel):
    file_name: str = Field(..., min_length=1, max_length=255)
    original_file_name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    
    asset_type: AssetType
    mime_type: str = Field(..., max_length=100)
    file_size: int = Field(..., ge=0)
    
    storage_provider: str = Field(..., max_length=50)
    storage_key: str = Field(..., max_length=1000)
    public_url: str | None = None
    thumbnail_url: str | None = None
    
    width: int | None = Field(None, ge=1)
    height: int | None = Field(None, ge=1)
    duration: int | None = Field(None, ge=1)
    
    checksum: str = Field(..., min_length=1, max_length=256)
    version: int = Field(default=1, ge=1)
    folder: str | None = Field("/", max_length=255)
    
    tags: list[str] | dict | None = None
    metadata_: dict | None = Field(None, alias="metadata")
    
    status: AssetStatus = AssetStatus.UPLOADING

class AssetCreate(AssetBase):
    workspace_id: uuid.UUID
    uploaded_by: uuid.UUID | None = None

class AssetUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    folder: str | None = Field(None, max_length=255)
    tags: list[str] | dict | None = None
    metadata_: dict | None = Field(None, alias="metadata")
    status: AssetStatus | None = None

class AssetResponse(AssetBase):
    id: uuid.UUID
    workspace_id: uuid.UUID
    uploaded_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
