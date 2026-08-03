import uuid
from typing import Optional

from app.events.base import BaseEvent


class AIContentGenerated(BaseEvent):
    event_name: str = "AIContentGenerated"
    provider: str
    tokens_used: int
    content_id: Optional[uuid.UUID] = None


class AIContentRegenerated(BaseEvent):
    event_name: str = "AIContentRegenerated"
    provider: str
    tokens_used: int
    content_id: Optional[uuid.UUID] = None


class AIProviderFailed(BaseEvent):
    event_name: str = "AIProviderFailed"
    provider: str
    error_message: str
