import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.constants.enums import ApiProvider


class ApiKeyBase(BaseModel):
    workspace_id: uuid.UUID
    provider: ApiProvider
    key_name: str
    is_active: bool = True


class ApiKeyCreate(ApiKeyBase):
    secret: str  # The raw secret to be encrypted before saving


class ApiKeyUpdate(BaseModel):
    is_active: bool | None = None
    key_name: str | None = None


class ApiKeyResponse(ApiKeyBase):
    id: uuid.UUID
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    # Never expose encrypted_secret or raw secret in the response schema
    model_config = ConfigDict(from_attributes=True)
