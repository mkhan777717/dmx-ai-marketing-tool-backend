import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.constants.enums import NotificationType, NotificationPriority
from typing import Any

class NotificationBase(BaseModel):
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    body: str
    type: NotificationType = NotificationType.SYSTEM
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: dict[str, Any] | list[Any] | None = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    read_at: datetime | None = None

class NotificationResponse(NotificationBase):
    id: uuid.UUID
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
