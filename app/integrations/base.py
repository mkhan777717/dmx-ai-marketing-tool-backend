from abc import ABC, abstractmethod
from typing import Any

from app.integrations.interfaces import BaseConnector, IntegrationCapabilities


class AbstractConnector(ABC, BaseConnector):
    """
    Abstract base class providing common utility methods for connectors.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        self.credentials = credentials
        self.access_token = access_token

    @abstractmethod
    async def connect(self, auth_code: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        pass

    @abstractmethod
    async def validate(self) -> bool:
        pass

    @abstractmethod
    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        pass

    @abstractmethod
    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_capabilities(self) -> IntegrationCapabilities:
        pass
