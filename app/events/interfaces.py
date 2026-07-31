from abc import ABC, abstractmethod

from app.events.base import BaseEvent


class BaseEventHandler(ABC):
    """
    Abstract interface that all Event Handlers must implement.
    """

    @abstractmethod
    async def handle(self, event: BaseEvent) -> None:
        """
        Process the given event. This must not raise exceptions that could
        crash the caller, it should handle its own failures gracefully.
        """
        pass
