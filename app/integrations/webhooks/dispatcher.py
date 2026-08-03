import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.base import BaseEvent
from app.events.publisher import EventPublisher

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    @staticmethod
    async def dispatch(
        db: AsyncSession,
        provider: str,
        payload: dict[str, Any],
        workspace_id: uuid.UUID,
    ) -> None:
        """
        Translates a provider-specific webhook payload into internal Domain Events
        and dispatches them through the existing Event System.
        """
        logger.info(f"Dispatching webhook from {provider} for workspace {workspace_id}")

        # Determine internal event type based on provider and payload
        event_type = f"integration.{provider.lower()}.webhook_received"

        event = BaseEvent(
            event_name=event_type,
            workspace_id=workspace_id,
            actor_id=None,  # System actor
            correlation_id=str(uuid.uuid4()),
            payload=payload,
            metadata={"provider": provider},
        )

        # Publish the event to our Event Bus
        await EventPublisher.publish(event)
