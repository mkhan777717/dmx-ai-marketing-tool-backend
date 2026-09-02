from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.linkedin.exceptions import LinkedInAuthError
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
        self.webhook_handler = LinkedInWebhookHandler(self.client_secret)

    async def connect(
        self,
        auth_code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        """Exchanges authorization code for tokens and fetches initial metadata."""
        token_data = await self.oauth_handler.exchange_code(
            auth_code, redirect_uri=redirect_uri
        )

        # Fetch initial profile metadata to associate with the connection
        sync_engine = LinkedInSyncEngine(token_data["access_token"])
        profile_data = await sync_engine.fetch_profile()

        sub = profile_data.get("sub")
        if not sub:
            raise LinkedInAuthError(
                "LinkedIn profile response is missing the required 'sub' identifier."
            )

        profile_name = (
            profile_data.get("name")
            or f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
            or "LinkedIn Member"
        )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": token_data["expires_at"],
            "author_urn": f"urn:li:person:{sub}",
            "profile_name": profile_name,
        }

    async def disconnect(self) -> bool:
        """Returns True to signify successful local disconnect."""
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
        return self.webhook_handler.process_payload(payload)

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=[
                "publish_text",
                "publish_image",
                "publish_video",
                "read_profile",
            ],
        )

    async def publish(
        self,
        author_urn: str,
        content: str,
        media_binary: bytes | None = None,
        mime_type: str = "image/jpeg",
        media_type: str = "text",
    ) -> str:
        """Helper method to publish content (text, image, or video) to LinkedIn."""
        if not self.access_token:
            raise ValueError("Access token required for publishing.")

        publisher = LinkedInPublisher(self.access_token)

        if media_binary and media_type == "video":
            return await publisher.publish_video_post(
                author_urn=author_urn,
                text=content,
                video_binary=media_binary,
                mime_type=mime_type,
            )
        elif media_binary:
            return await publisher.publish_image_post(
                author_urn=author_urn,
                text=content,
                image_binary=media_binary,
                mime_type=mime_type,
            )
        else:
            return await publisher.publish_text_post(
                author_urn=author_urn, text=content
            )
