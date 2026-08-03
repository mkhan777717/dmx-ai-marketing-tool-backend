import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.constants.enums import PublishStatus


class PublishRequest(BaseModel):
    content_id: uuid.UUID
    social_account_id: uuid.UUID
    # Additional publishing options could go here (e.g. scheduling time if not immediate)


class PublishHistoryResponse(BaseModel):
    id: uuid.UUID
    content_id: uuid.UUID
    social_account_id: uuid.UUID
    status: PublishStatus
    external_post_id: Optional[str] = None
    error_message: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
