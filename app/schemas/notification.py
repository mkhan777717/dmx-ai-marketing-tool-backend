import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.constants.enums import NotificationPriority, NotificationType


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


class NotificationPreferenceResponse(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    in_app_enabled: bool
    email_enabled: bool
    push_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
