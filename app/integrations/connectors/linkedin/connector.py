from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.linkedin.oauth import LinkedInOAuthHandler
from app.integrations.connectors.linkedin.publisher import LinkedInPublisher
from app.integrations.connectors.linkedin.sync import LinkedInSyncEngine
from app.integrations.connectors.linkedin.webhook import LinkedInWebhookHandler
from app.integrations.interfaces import IntegrationCapabilities


class LinkedInConnector(AbstractConnector):
    """
    LinkedIn specific implementation of the AbstractConnector.
    Handles all interactions with the LinkedIn API.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")

        self.oauth_handler = LinkedInOAuthHandler(self.client_id, self.client_secret)

        # Handlers that require access tokens are instantiated when needed
        # or if the access token is already provided
        self.webhook_handler = LinkedInWebhookHandler(self.client_secret)

    async def connect(
        self, auth_code: str, code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Exchanges authorization code for tokens and fetches initial metadata."""
        token_data = await self.oauth_handler.exchange_code(auth_code)

        # Fetch initial profile metadata to associate with the connection
        sync_engine = LinkedInSyncEngine(token_data["access_token"])
        profile_data = await sync_engine.fetch_profile()

        sub = profile_data.get("sub")
        if not sub:
            from app.integrations.connectors.linkedin.exceptions import (
                LinkedInAuthError,
            )

            raise LinkedInAuthError(
                "LinkedIn profile response is missing the required 'sub' identifier."
            )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": token_data["expires_at"],
            "author_urn": f"urn:li:person:{sub}",
            "profile_name": f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip(),
        }

    async def disconnect(self) -> bool:
        """
        LinkedIn doesn't have a strict API token revocation endpoint that we need to hit,
        but we can return True to signify successful local disconnect.
        """
        return True

    async def validate(self) -> bool:
        """Validates if the current access token is still active by fetching profile."""
        if not self.access_token:
            return False
        try:
            sync_engine = LinkedInSyncEngine(self.access_token)
            await sync_engine.fetch_profile()
            return True
        except Exception:
            return False

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Synchronizes data from LinkedIn (e.g. profile and organizations)."""
        if not self.access_token:
            raise ValueError("Access token required for sync.")
        sync_engine = LinkedInSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Processes incoming webhooks from LinkedIn."""
        # Note: In a real system the signature verification usually happens at the middleware/dispatcher
        # But we provide it here as per architecture requirements.
        return self.webhook_handler.process_payload(payload)

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=[
                "publish_text",
                "publish_image",
                "read_profile",
                "read_organizations",
            ],
        )

    async def publish(self, author_urn: str, content: str) -> dict[str, Any]:
        """Helper method to publish content to LinkedIn."""
        if not self.access_token:
            raise ValueError("Access token required for publishing.")
        publisher = LinkedInPublisher(self.access_token)
        return await publisher.publish_text_post(author_urn, content)
