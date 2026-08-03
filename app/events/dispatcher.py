import asyncio
import logging

from app.events.base import BaseEvent
from app.events.registry import event_registry

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Dispatches events to all registered handlers for that event.
    """

    @staticmethod
    async def dispatch(event: BaseEvent) -> None:
        handlers = event_registry.get_handlers(event.event_name)
        if not handlers:
            logger.debug(f"No handlers registered for event: {event.event_name}")
            return

        # Execute handlers concurrently. We trap exceptions so one bad handler
        # doesn't crash the other handlers or the main dispatcher.
        tasks = []
        for handler in handlers:
            tasks.append(EventDispatcher._safe_execute(handler, event))

        await asyncio.gather(*tasks)

    @staticmethod
    async def _safe_execute(handler, event: BaseEvent) -> None:
        try:
            await handler.handle(event)
        except Exception as e:
            logger.error(
                f"Error executing handler {handler.__class__.__name__} "
                f"for event {event.event_name}: {str(e)}",
                exc_info=True,
            )
