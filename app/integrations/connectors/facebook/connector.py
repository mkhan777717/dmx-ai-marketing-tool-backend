from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.facebook.oauth import FacebookOAuthHandler
from app.integrations.connectors.facebook.publisher import FacebookPublisher
from app.integrations.connectors.facebook.sync import FacebookSyncEngine
from app.integrations.connectors.facebook.webhook import FacebookWebhookHandler
from app.integrations.interfaces import IntegrationCapabilities


class FacebookConnector(AbstractConnector):
    """
    Facebook specific implementation of the AbstractConnector.
    Handles all interactions with the Facebook Graph API.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")

        self.oauth_handler = FacebookOAuthHandler(self.client_id, self.client_secret)

        # Webhook handler needs the App Secret to verify HMAC payload signatures
        self.webhook_handler = FacebookWebhookHandler(self.client_secret)

    async def connect(self, auth_code: str) -> dict[str, Any]:
        """Exchanges authorization code for tokens and fetches initial metadata."""
        # This exchanges for a short-lived token, then upgrades to a long-lived token
        token_data = await self.oauth_handler.exchange_code(auth_code)

        # Fetch initial profile metadata to associate with the connection
        sync_engine = FacebookSyncEngine(token_data["access_token"])
        profile_data = await sync_engine.fetch_profile()

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": token_data["expires_at"],
            "author_id": profile_data.get("id"),
            "profile_name": profile_data.get("name", ""),
        }

    async def disconnect(self) -> bool:
        """
        To fully disconnect we could revoke permissions via DELETE /me/permissions
        For now we rely on the platform deleting the tokens locally.
        """
        return True

    async def validate(self) -> bool:
        """Validates if the current access token is still active by fetching profile."""
        if not self.access_token:
            return False
        try:
            sync_engine = FacebookSyncEngine(self.access_token)
            await sync_engine.fetch_profile()
            return True
        except Exception:
            return False

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Synchronizes data from Facebook (e.g. profile and administered pages)."""
        if not self.access_token:
            raise ValueError("Access token required for sync.")
        sync_engine = FacebookSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Processes incoming webhooks from Facebook."""
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
                "read_pages",
            ],
        )

    async def publish(
        self, page_id: str, content: str, page_access_token: str
    ) -> dict[str, Any]:
        """Helper method to publish content to a specific Facebook Page."""
        # We must use the page_access_token to publish to a page, not the user access token
        publisher = FacebookPublisher(page_access_token)
        return await publisher.publish_text_post(page_id, content)
