import logging

from app.events.base import BaseEvent
from app.events.interfaces import BaseEventHandler
from app.jobs.queue import queue_service

logger = logging.getLogger(__name__)


class NotificationHandler(BaseEventHandler):
    """
    Listens to business events and decides if a Notification should be created
    and dispatched to the user based on their NotificationPreferences.
    """

    async def handle(self, event: BaseEvent) -> None:
        logger.info(
            f"[NotificationHandler] Enqueueing notification process for event: {event.event_name}"
        )
        await queue_service.enqueue(
            job_name="notifications.process_event",
            payload={
                "event_name": event.event_name,
                "event_id": str(event.event_id),
                "actor_id": str(event.actor_id) if event.actor_id else None,
            },
            queue="high",
        )
