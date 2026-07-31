import uuid
from abc import ABC, abstractmethod
from typing import Any


class BaseNotificationProvider(ABC):
    """
    Abstract interface for all notification delivery providers.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def send(
        self, user_id: uuid.UUID, title: str, body: str, data: dict[str, Any] = None
    ) -> bool:
        """
        Sends the notification.
        Returns True if successful, False otherwise.
        """
        pass
