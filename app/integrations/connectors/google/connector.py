from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.google.analytics import GoogleAnalyticsService
from app.integrations.connectors.google.business_profile import (
    GoogleBusinessProfilePublisher,
)
from app.integrations.connectors.google.calendar import GoogleCalendarService
from app.integrations.connectors.google.drive import GoogleDriveService

# Import sub-service stubs
from app.integrations.connectors.google.gmail import GmailService
from app.integrations.connectors.google.oauth import GoogleOAuthHandler
from app.integrations.connectors.google.sync import GoogleSyncEngine
from app.integrations.connectors.google.webhook import GoogleWebhookHandler
from app.integrations.connectors.google.youtube import YouTubePublisher
from app.integrations.interfaces import IntegrationCapabilities


class GoogleConnector(AbstractConnector):
    """
    Google specific implementation of the AbstractConnector.
    Serves as the foundation and OAuth hub for all Google-related APIs.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")

        self.oauth_handler = GoogleOAuthHandler(self.client_id, self.client_secret)
        self.webhook_handler = GoogleWebhookHandler(self.client_secret)

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

        sync_engine = GoogleSyncEngine(token_data["access_token"])
        profile_data = await sync_engine.fetch_profile()

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "expires_at": token_data["expires_at"],
            "author_id": profile_data.get("id"),
            "profile_name": profile_data.get("email", ""),
        }

    async def disconnect(self) -> bool:
        """Disconnects the integration."""
        # A true disconnect would call Google's revoke token endpoint.
        # For now, platform handles token deletion.
        return True

    async def validate(self) -> bool:
        """Validates if the current access token is still active."""
        if not self.access_token:
            return False
        try:
            sync_engine = GoogleSyncEngine(self.access_token)
            await sync_engine.fetch_profile()
            return True
        except Exception:
            return False

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refreshes the access token using the stored refresh token."""
        return await self.oauth_handler.refresh_access_token(refresh_token)

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Synchronizes data from Google Profile."""
        if not self.access_token:
            raise ValueError("Access token required for sync.")
        sync_engine = GoogleSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Processes incoming webhooks from Google (Pub/Sub)."""
        return self.webhook_handler.process_payload(payload)

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True, can_webhook=True, supported_actions=["read_profile"]
        )

    async def publish(
        self, page_id: str, content: str, page_access_token: str
    ) -> dict[str, Any]:
        """
        Base publishing method. For Google, this might route to YouTube or GMB in the future.
        """
        raise NotImplementedError(
            "Publishing directly through base Google connector is not supported. Target a specific sub-service."
        )

    # --- Sub-service Factories ---

    def get_gmail_service(self) -> GmailService:
        if not self.access_token:
            raise ValueError("Access token required.")
        return GmailService(self.access_token)

    def get_drive_service(self) -> GoogleDriveService:
        if not self.access_token:
            raise ValueError("Access token required.")
        return GoogleDriveService(self.access_token)

    def get_calendar_service(self) -> GoogleCalendarService:
        if not self.access_token:
            raise ValueError("Access token required.")
        return GoogleCalendarService(self.access_token)

    def get_youtube_service(self) -> YouTubePublisher:
        if not self.access_token:
            raise ValueError("Access token required.")
        return YouTubePublisher(self.access_token)

    def get_business_profile_service(self) -> GoogleBusinessProfilePublisher:
        if not self.access_token:
            raise ValueError("Access token required.")
        return GoogleBusinessProfilePublisher(self.access_token)

    def get_analytics_service(self) -> GoogleAnalyticsService:
        if not self.access_token:
            raise ValueError("Access token required.")
        return GoogleAnalyticsService(self.access_token)
