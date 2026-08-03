import uuid
from typing import Optional

from app.events.base import BaseEvent


class PostPublished(BaseEvent):
    event_name: str = "PostPublished"
    content_id: uuid.UUID
    social_account_id: uuid.UUID
    external_post_id: str


class PostScheduled(BaseEvent):
    event_name: str = "PostScheduled"
    content_id: uuid.UUID
    social_account_id: uuid.UUID


class PostFailed(BaseEvent):
    event_name: str = "PostFailed"
    content_id: uuid.UUID
    social_account_id: uuid.UUID
    error_message: Optional[str] = None


class PublishingRetry(BaseEvent):
    event_name: str = "PublishingRetry"
    content_id: uuid.UUID
    social_account_id: uuid.UUID
