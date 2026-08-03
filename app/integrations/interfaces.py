from typing import Any, Protocol

from pydantic import BaseModel


class IntegrationCapabilities(BaseModel):
    can_sync: bool = False
    can_webhook: bool = False
    supported_actions: list[str] = []


class BaseConnector(Protocol):
    """
    Standard interface that every external provider connector must implement.
    """

    async def connect(self, auth_code: str) -> dict[str, Any]:
        """Exchange auth code for tokens and connection metadata."""
        ...

    async def disconnect(self) -> bool:
        """Revoke tokens and clean up provider side if necessary."""
        ...

    async def validate(self) -> bool:
        """Check if the connection and tokens are still valid."""
        ...

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Trigger a sync with the provider."""
        ...

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Process an incoming webhook payload from this provider."""
        ...

    def get_capabilities(self) -> IntegrationCapabilities:
        """Return what this connector is capable of."""
        ...
