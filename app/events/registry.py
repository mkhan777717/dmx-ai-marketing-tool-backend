from collections import defaultdict
from typing import List

from app.events.exceptions import HandlerRegistrationError
from app.events.interfaces import BaseEventHandler


class EventRegistry:
    """
    Central registry for event handlers.
    Maps event_name to a list of instantiated BaseEventHandlers.
    """

    def __init__(self):
        self._handlers: dict[str, List[BaseEventHandler]] = defaultdict(list)

    def register_handler(self, event_name: str, handler: BaseEventHandler) -> None:
        if not isinstance(handler, BaseEventHandler):
            raise HandlerRegistrationError(
                f"Handler {handler} must implement BaseEventHandler"
            )

        # Prevent duplicates
        if handler not in self._handlers[event_name]:
            self._handlers[event_name].append(handler)

    def remove_handler(self, event_name: str, handler: BaseEventHandler) -> None:
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)

    def get_handlers(self, event_name: str) -> List[BaseEventHandler]:
        return self._handlers.get(event_name, [])


# Global singleton registry
event_registry = EventRegistry()
