import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPreferenceBase(BaseModel):
    theme: str = "system"
    timezone: str = "UTC"
    date_format: str = "YYYY-MM-DD"
    notification_preferences: dict | list | None = None
    ai_preferences: dict | list | None = None


class UserPreferenceCreate(UserPreferenceBase):
    user_id: uuid.UUID


class UserPreferenceUpdate(BaseModel):
    theme: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    notification_preferences: dict | list | None = None
    ai_preferences: dict | list | None = None


class UserPreferenceResponse(UserPreferenceBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
