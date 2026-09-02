import logging
from typing import Any, Dict

from app.integrations.connectors.whatsapp.sync import WhatsAppSyncEngine
from app.integrations.exceptions import IntegrationError
from app.integrations.secrets.service import secret_service
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider

logger = logging.getLogger(__name__)


class WhatsAppProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return "whatsapp"

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        """
        Sends a WhatsApp message (template, image, video, document, or text) using the stored SocialAccount.
        Extracts recipient phone number from content.metadata_ ('recipient' or 'to' or 'recipient_phone').
        """
        from app.constants.enums import AssetType
        from app.integrations.connectors.whatsapp.exceptions import WhatsAppPublishError
        from app.integrations.connectors.whatsapp.publisher import WhatsAppPublisher

        if not account.access_token:
            raise IntegrationError(
                f"No access token available for WhatsApp social account {account.id}"
            )

        recipient = None
        metadata = content.metadata_ if isinstance(content.metadata_, dict) else {}
        if metadata:
            recipient = (
                metadata.get("recipient")
                or metadata.get("to")
                or metadata.get("recipient_phone")
            )

        if not recipient:
            raise IntegrationError(
                f"Campaign content {content.id} metadata missing recipient phone number ('recipient' or 'to')."
            )

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = WhatsAppPublisher(access_token=decrypted_token)

        # 1. Template Routing
        if "template_name" in metadata or "template" in metadata:
            template_name = metadata.get("template_name") or metadata.get(
                "template", {}
            ).get("name")
            language_code = metadata.get("language_code") or metadata.get(
                "template", {}
            ).get("language", {}).get("code", "en_US")
            components = metadata.get("components") or metadata.get("template", {}).get(
                "components"
            )

            if not template_name:
                raise IntegrationError(
                    "WhatsApp template message requires 'template_name'."
                )

            try:
                res = await publisher.send_template_message(
                    phone_number_id=account.account_id,
                    recipient=str(recipient),
                    template_name=str(template_name),
                    language_code=str(language_code),
                    components=components,
                )
            except WhatsAppPublishError as exc:
                raise IntegrationError(
                    f"WhatsApp template message sending failed: {exc}"
                ) from exc

            return self._extract_message_id(res)

        # 2. Media Routing
        if content.assets and len(content.assets) > 0:
            supported_asset = None
            media_type = None

            for asset in content.assets:
                asset_t = getattr(asset, "asset_type", None)
                if asset_t in (AssetType.IMAGE, "IMAGE", "image"):
                    supported_asset = asset
                    media_type = "image"
                    break
                elif asset_t in (AssetType.VIDEO, "VIDEO", "video"):
                    supported_asset = asset
                    media_type = "video"
                    break
                elif asset_t in (AssetType.DOCUMENT, "DOCUMENT", "document"):
                    supported_asset = asset
                    media_type = "document"
                    break

            if supported_asset and media_type:
                media_url = getattr(supported_asset, "public_url", None) or getattr(
                    supported_asset, "file_path", None
                )
                if not media_url:
                    raise IntegrationError(
                        f"WhatsApp {media_type} asset missing public URL."
                    )

                caption = content.body or metadata.get("caption", "")
                filename = (
                    metadata.get("filename")
                    or getattr(supported_asset, "file_name", None)
                    or getattr(supported_asset, "original_file_name", None)
                    or getattr(supported_asset, "name", "")
                )

                try:
                    res = await publisher.send_media_message(
                        phone_number_id=account.account_id,
                        recipient=str(recipient),
                        media_type=media_type,
                        media_url=str(media_url),
                        caption=str(caption) if caption else "",
                        filename=str(filename) if filename else "",
                    )
                except WhatsAppPublishError as exc:
                    raise IntegrationError(
                        f"WhatsApp {media_type} message sending failed: {exc}"
                    ) from exc

                return self._extract_message_id(res)

        # 3. Text Message Routing
        if not content.body or not content.body.strip():
            raise IntegrationError(
                f"Campaign content {content.id} missing text body required for WhatsApp message."
            )

        try:
            res = await publisher.send_text_message(
                phone_number_id=account.account_id,
                recipient=str(recipient),
                message=content.body,
            )
        except WhatsAppPublishError as exc:
            raise IntegrationError(
                f"WhatsApp text message sending failed: {exc}"
            ) from exc

        return self._extract_message_id(res)

    def _extract_message_id(self, res: Dict[str, Any]) -> str:
        messages = res.get("messages", [])
        if messages and isinstance(messages, list) and len(messages) > 0:
            msg_id = messages[0].get("id")
            if msg_id:
                return str(msg_id)
        raise IntegrationError(
            "WhatsApp Cloud API response did not contain a message ID."
        )

    async def get_account_info(self, account: SocialAccount) -> Dict[str, Any]:
        """
        Fetches status, WABA ID, and phone number information for the connected WhatsApp Account.
        """
        if not account.access_token:
            raise IntegrationError(
                f"No access token available for WhatsApp social account {account.id}"
            )

        decrypted_token = secret_service.decrypt_token(account.access_token)
        sync_engine = WhatsAppSyncEngine(access_token=decrypted_token)

        try:
            phone_numbers = await sync_engine.fetch_wabas_with_phone_numbers()
        except Exception as e:
            logger.error(
                f"Failed to fetch WhatsApp account info for account {account.account_id}: {e}"
            )
            raise IntegrationError(f"Failed to fetch WhatsApp account info: {e}") from e

        account_info = next(
            (pn for pn in phone_numbers if pn["phone_number_id"] == account.account_id),
            None,
        )

        if not account_info and phone_numbers:
            account_info = phone_numbers[0]

        if not account_info:
            return {
                "account_id": account.account_id,
                "name": account.name,
                "status": "connected",
                "phone_numbers": [],
            }

        return {
            "account_id": account_info.get("phone_number_id", account.account_id),
            "waba_id": account_info.get("waba_id"),
            "display_phone_number": account_info.get("display_phone_number"),
            "verified_name": account_info.get("verified_name"),
            "quality_rating": account_info.get("quality_rating"),
            "status": "connected",
        }
