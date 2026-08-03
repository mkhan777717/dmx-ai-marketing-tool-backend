import logging

from app.events.base import BaseEvent
from app.events.interfaces import BaseEventHandler

logger = logging.getLogger(__name__)


class WebhookHandler(BaseEventHandler):
    """
    Listens to public-facing business events and dispatches HTTP POST
    requests to user-configured Webhook URLs.
    """

    async def handle(self, event: BaseEvent) -> None:
        logger.info(
            f"[WebhookHandler] Processing event: {event.event_name} (ID: {event.event_id})"
        )
        # In a real scenario, this would query Webhook endpoints registered for the workspace
        # and queue an HTTP request.
        pass
