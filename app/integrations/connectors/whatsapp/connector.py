from typing import Any

from app.integrations.base import AbstractConnector
from app.integrations.connectors.whatsapp.oauth import WhatsAppOAuthHandler
from app.integrations.connectors.whatsapp.sync import WhatsAppSyncEngine
from app.integrations.connectors.whatsapp.webhook import WhatsAppWebhookHandler
from app.integrations.exceptions import OAuthTokenError, WebhookVerificationError
from app.integrations.interfaces import IntegrationCapabilities


class WhatsAppConnector(AbstractConnector):
    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.oauth_handler = WhatsAppOAuthHandler(
            client_id=self.client_id,
            client_secret=self.client_secret,
        )
        self.webhook_handler = WhatsAppWebhookHandler(self.client_secret)

    async def connect(
        self,
        auth_code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        """Exchanges authorization code for WhatsApp Meta access token."""
        import logging

        logger = logging.getLogger(__name__)

        token_data = await self.oauth_handler.exchange_code(
            auth_code, redirect_uri=redirect_uri
        )
        self.access_token = token_data.get("access_token")

        # Discover initial WABAs & phone numbers to populate metadata
        if self.access_token:
            try:
                sync_engine = WhatsAppSyncEngine(self.access_token)
                waba_data = await sync_engine.perform_sync("full")
                token_data["waba_info"] = waba_data
            except Exception as exc:
                logger.warning(
                    f"Initial WABA discovery during WhatsApp connect encountered warning: {exc}"
                )
                token_data["waba_info"] = {
                    "whatsapp_phone_numbers": [],
                    "records_synced": 0,
                    "warning": str(exc),
                }

        return token_data

    async def validate(self) -> bool:
        """Validates current access token by making a lightweight WABA API query."""
        if not self.access_token:
            return False

        sync_engine = WhatsAppSyncEngine(self.access_token)
        try:
            await sync_engine.fetch_wabas()
            return True
        except (OAuthTokenError, Exception):
            return False

    async def disconnect(self) -> bool:
        """Revokes or cleans up connection locally."""
        return True

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Performs synchronization of WABAs and phone numbers."""
        if not self.access_token:
            raise OAuthTokenError("Access token missing for WhatsApp sync.")

        sync_engine = WhatsAppSyncEngine(self.access_token)
        return await sync_engine.perform_sync(sync_type=sync_type)

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Processes an incoming WhatsApp webhook payload."""
        if signature and not self.webhook_handler.verify_signature(
            str(payload).encode("utf-8"), signature
        ):
            raise WebhookVerificationError("Invalid WhatsApp webhook signature.")
        return self.webhook_handler.parse_webhook_payload(payload)

    async def publish(
        self,
        page_id: str,
        content: str,
        page_access_token: str,
        recipient: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Helper method to send a WhatsApp message (text, template, or media) to a recipient.
        `page_id` is the WhatsApp phone_number_id.
        `page_access_token` is the associated access token.
        """
        if not recipient:
            recipient = kwargs.get("to") or kwargs.get("recipient_phone")
        if not recipient:
            raise ValueError(
                "WhatsApp message sending requires a recipient phone number."
            )

        from app.integrations.connectors.whatsapp.publisher import WhatsAppPublisher

        publisher = WhatsAppPublisher(page_access_token)

        # Template routing
        if "template_name" in kwargs or "template" in kwargs:
            template_name = kwargs.get("template_name") or kwargs.get(
                "template", {}
            ).get("name")
            language_code = kwargs.get("language_code") or kwargs.get(
                "template", {}
            ).get("language", {}).get("code", "en_US")
            components = kwargs.get("components") or kwargs.get("template", {}).get(
                "components"
            )
            return await publisher.send_template_message(
                phone_number_id=page_id,
                recipient=recipient,
                template_name=template_name,
                language_code=language_code,
                components=components,
            )

        # Media routing
        media_type = kwargs.get("media_type")
        media_url = kwargs.get("media_url") or kwargs.get("url")
        if media_type and media_url:
            caption = content or kwargs.get("caption", "")
            filename = kwargs.get("filename", "")
            return await publisher.send_media_message(
                phone_number_id=page_id,
                recipient=recipient,
                media_type=media_type,
                media_url=media_url,
                caption=caption,
                filename=filename,
            )

        # Text routing
        return await publisher.send_text_message(
            phone_number_id=page_id, recipient=recipient, message=content
        )

    def get_capabilities(self) -> IntegrationCapabilities:
        """Returns the supported capabilities of this connector."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=True,
            supported_actions=[
                "read_profile",
                "publish_text",
                "publish_template",
                "publish_image",
                "publish_video",
                "publish_document",
            ],
        )
