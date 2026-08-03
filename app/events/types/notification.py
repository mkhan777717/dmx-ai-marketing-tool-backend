import uuid
from typing import Optional

from app.events.base import BaseEvent


class NotificationCreated(BaseEvent):
    event_name: str = "NotificationCreated"
    notification_id: uuid.UUID
    target_user_id: uuid.UUID


class NotificationSent(BaseEvent):
    event_name: str = "NotificationSent"
    notification_id: uuid.UUID
    delivery_id: uuid.UUID


class NotificationRead(BaseEvent):
    event_name: str = "NotificationRead"
    notification_id: uuid.UUID


class NotificationFailed(BaseEvent):
    event_name: str = "NotificationFailed"
    notification_id: uuid.UUID
    error_message: Optional[str] = None
