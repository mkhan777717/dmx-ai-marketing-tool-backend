import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class EventPriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class BaseEvent(BaseModel):
    """
    Base Event that all domain events must inherit from.
    """

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_name: str
    event_version: str = "1.0"

    workspace_id: Optional[uuid.UUID] = None
    actor_id: Optional[uuid.UUID] = None  # User or System ID that triggered the event

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None  # To track a chain of events

    priority: EventPriority = EventPriority.NORMAL

    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)
