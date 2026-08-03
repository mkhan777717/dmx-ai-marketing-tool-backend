import logging

from app.events.base import BaseEvent
from app.events.interfaces import BaseEventHandler
from app.jobs.queue import queue_service

logger = logging.getLogger(__name__)


class AnalyticsHandler(BaseEventHandler):
    """
    Listens to business events (CampaignCreated, PostPublished, etc.)
    and triggers updates to the Analytics Module.
    """

    async def handle(self, event: BaseEvent) -> None:
        logger.info(
            f"[AnalyticsHandler] Enqueueing analytics update for event: {event.event_name}"
        )
        await queue_service.enqueue(
            job_name="analytics.refresh_dashboard",
            payload={
                "event_name": event.event_name,
                "event_id": str(event.event_id),
                "workspace_id": str(event.workspace_id) if event.workspace_id else None,
            },
            queue="default",
        )
