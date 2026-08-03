from typing import Type

from app.integrations.connectors.facebook import FacebookConnector
from app.integrations.connectors.google import GoogleConnector
from app.integrations.connectors.instagram import InstagramConnector
from app.integrations.connectors.linkedin import LinkedInConnector

# Import available connectors to ensure they can be registered
from app.integrations.connectors.mock import MockConnector
from app.integrations.connectors.slack import SlackConnector
from app.integrations.interfaces import BaseConnector


class ConnectorRegistry:
    _registry: dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, provider_name: str, connector_cls: Type[BaseConnector]) -> None:
        """Register a connector class for a specific provider."""
        cls._registry[provider_name.lower()] = connector_cls

    @classmethod
    def get_connector(cls, provider_name: str) -> Type[BaseConnector]:
        """Retrieve a registered connector class."""
        connector_cls = cls._registry.get(provider_name.lower())
        if not connector_cls:
            raise ValueError(f"No connector registered for provider: {provider_name}")
        return connector_cls


class ConnectorFactory:
    @staticmethod
    def create(
        provider_name: str, credentials: dict[str, str], access_token: str | None = None
    ) -> BaseConnector:
        """
        Instantiate a connector with credentials and token.
        Expects the connector constructor to take `credentials` and `access_token`.
        """
        connector_cls = ConnectorRegistry.get_connector(provider_name)
        # Using a convention that connectors take these kwargs
        return connector_cls(credentials=credentials, access_token=access_token)


# Auto-register known connectors
ConnectorRegistry.register("mock", MockConnector)
ConnectorRegistry.register("linkedin", LinkedInConnector)
ConnectorRegistry.register("facebook", FacebookConnector)
ConnectorRegistry.register("instagram", InstagramConnector)
ConnectorRegistry.register("google", GoogleConnector)
ConnectorRegistry.register("slack", SlackConnector)
