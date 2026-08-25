from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.slack.oauth import SlackOAuthHandler
from app.integrations.connectors.slack.publisher import SlackPublisher
from app.integrations.connectors.slack.sync import SlackSyncEngine
from app.integrations.connectors.slack.webhook import SlackWebhookHandler
from app.integrations.interfaces import IntegrationCapabilities


class SlackConnector(AbstractConnector):
    """
    Slack specific implementation of the AbstractConnector.
    Handles all interactions with the Slack Web API and Events API.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.signing_secret = credentials.get("signing_secret", "")

        self.oauth_handler = SlackOAuthHandler(self.client_id, self.client_secret)
        self.webhook_handler = SlackWebhookHandler(self.signing_secret)

    async def connect(
        self, auth_code: str, code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Exchanges authorization code for bot tokens and fetches initial metadata."""
        token_data = await self.oauth_handler.exchange_code(auth_code)

        return {
            "access_token": token_data["access_token"],
            "refresh_token": None,
            "expires_at": None,
            "author_id": token_data["bot_user_id"],
            "profile_name": token_data["team_name"],
        }

    async def disconnect(self) -> bool:
        """Disconnects the integration."""
        return True

    async def validate(self) -> bool:
        """Validates if the current access token is still active using auth.test."""
        if not self.access_token:
            return False
        try:
            sync_engine = SlackSyncEngine(self.access_token)
            await sync_engine.verify_auth()
            return True
        except Exception:
            return False

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Synchronizes data from Slack (e.g. channel lists)."""
        if not self.access_token:
            raise ValueError("Access token required for sync.")
        sync_engine = SlackSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """
        Processes incoming webhooks from Slack Events API or Interactions.
        Note: The platform layer usually handles raw signature validation before passing the parsed JSON here.
        However, if the platform passes it to the connector, this acts as the processor.
        For url_verification, we return the challenge.
        """
        challenge = self.webhook_handler.verify_challenge(payload)
        if challenge:
            return {"challenge": challenge}

        return self.webhook_handler.process_payload(payload)

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=[
                "publish_text",
                "publish_blocks",
                "read_profile",
                "read_channels",
            ],
        )

    async def publish(
        self, channel_id: str, content: str, blocks: list = None, thread_ts: str = None
    ) -> dict[str, Any]:
        """
        Publishes a message to a Slack channel.
        `channel_id` is passed as the `page_id` arg in the generic interface.
        """
        if not self.access_token:
            raise ValueError("Access token required for publishing.")

        publisher = SlackPublisher(self.access_token)
        return await publisher.publish_message(
            channel_id=channel_id, text=content, blocks=blocks, thread_ts=thread_ts
        )
