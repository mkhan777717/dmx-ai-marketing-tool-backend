import asyncio
from typing import List

from app.events.base import BaseEvent
from app.events.dispatcher import EventDispatcher


class EventPublisher:
    """
    Interface for the Service Layer to publish events.
    """

    @staticmethod
    async def publish(event: BaseEvent) -> None:
        """
        Publish a single event.
        For now, this dispatches immediately in an asyncio task so that it doesn't
        block the caller. In a future implementation, this could push to Redis/Celery.
        """
        # Fire and forget (dispatches in the background immediately).
        # We don't await the dispatch directly so we don't block the HTTP response
        # waiting for handlers to finish (unless required).
        asyncio.create_task(EventDispatcher.dispatch(event))

    @staticmethod
    async def publish_many(events: List[BaseEvent]) -> None:
        """
        Publish multiple events.
        """
        for event in events:
            await EventPublisher.publish(event)
