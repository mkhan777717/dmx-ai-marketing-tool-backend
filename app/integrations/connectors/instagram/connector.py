from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.instagram.oauth import InstagramOAuthHandler
from app.integrations.connectors.instagram.publisher import InstagramPublisher
from app.integrations.connectors.instagram.sync import InstagramSyncEngine
from app.integrations.connectors.instagram.webhook import InstagramWebhookHandler
from app.integrations.interfaces import IntegrationCapabilities


class InstagramConnector(AbstractConnector):
    """
    Instagram specific implementation of the AbstractConnector.
    Handles all interactions with the Instagram Graph API.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")

        self.oauth_handler = InstagramOAuthHandler(self.client_id, self.client_secret)
        self.webhook_handler = InstagramWebhookHandler(self.client_secret)

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

        sync_engine = InstagramSyncEngine(token_data["access_token"])
        sync_data = await sync_engine.perform_sync(sync_type="full")

        # We take the first linked Instagram account as the primary profile for this connection, if available
        author_id = None
        profile_name = ""

        if (
            sync_data.get("instagram_accounts")
            and len(sync_data["instagram_accounts"]) > 0
        ):
            primary_account = sync_data["instagram_accounts"][0]
            author_id = primary_account.get("id")
            profile_name = (
                primary_account.get("username") or primary_account.get("name") or ""
            )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": token_data["expires_at"],
            "author_id": author_id,
            "profile_name": profile_name,
        }

    async def disconnect(self) -> bool:
        """Disconnects the integration."""
        return True

    async def validate(self) -> bool:
        """Validates if the current access token is still active by attempting to fetch linked pages."""
        if not self.access_token:
            return False
        try:
            sync_engine = InstagramSyncEngine(self.access_token)
            await sync_engine.fetch_pages_with_instagram()
            return True
        except Exception:
            return False

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Synchronizes data from Instagram (e.g. business profiles and pages)."""
        if not self.access_token:
            raise ValueError("Access token required for sync.")
        sync_engine = InstagramSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Processes incoming webhooks from Instagram."""
        return self.webhook_handler.process_payload(payload)

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=[
                "publish_image",
                "publish_video",
                "publish_reels",
                "publish_carousel",
                "read_profile",
            ],
        )

    async def publish(
        self,
        page_id: str,
        content: str,
        page_access_token: str,
        image_url: str = "",
        video_url: str = "",
        image_urls: list[str] | None = None,
        items: list[Any] | None = None,
        is_reel: bool = False,
    ) -> dict[str, Any]:
        """
        Helper method to publish an image, video, Reels, or Carousel post to a specific Instagram Account.
        In the context of the platform, `page_id` is the IG User ID, and `page_access_token` is the associated Facebook Page access token.
        """
        publisher = InstagramPublisher(page_access_token)

        carousel_items = items or image_urls
        if carousel_items:
            return await publisher.publish_carousel_post(
                page_id, items=carousel_items, caption=content
            )

        if not image_url and not video_url:
            raise ValueError(
                "Instagram publishing requires an image_url, video_url, or items/image_urls list."
            )

        if video_url:
            if is_reel:
                return await publisher.publish_reels_post(
                    page_id, video_url=video_url, caption=content
                )
            return await publisher.publish_video_post(
                page_id, video_url=video_url, caption=content
            )
        return await publisher.publish_image_post(
            page_id, image_url=image_url, caption=content
        )
