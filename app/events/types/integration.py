import uuid
from typing import Optional

from app.events.base import BaseEvent


class IntegrationTokenExpired(BaseEvent):
    event_name: str = "IntegrationTokenExpired"
    workspace_id: uuid.UUID
    provider: str
    connection_id: Optional[uuid.UUID] = None
    reason: Optional[str] = "Meta long-lived access token has expired or was revoked."
