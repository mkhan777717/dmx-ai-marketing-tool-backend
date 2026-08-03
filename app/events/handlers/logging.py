import logging

from app.events.base import BaseEvent
from app.events.interfaces import BaseEventHandler

logger = logging.getLogger(__name__)


class LoggingHandler(BaseEventHandler):
    """
    A simple pass-through handler that logs every event flowing through the system.
    """

    async def handle(self, event: BaseEvent) -> None:
        logger.debug(f"[LoggingHandler] Event Dispatched: {event.json()}")
