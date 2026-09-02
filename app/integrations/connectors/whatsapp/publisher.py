import logging
from typing import Any, Dict

import httpx

from app.integrations.connectors.whatsapp.exceptions import WhatsAppPublishError
from app.integrations.constants import META_GRAPH_API_VERSION

logger = logging.getLogger(__name__)


class WhatsAppPublisher:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, access_token: str):
        self.access_token = access_token

    async def send_text_message(
        self, phone_number_id: str, recipient: str, message: str
    ) -> Dict[str, Any]:
        """
        Sends a text message to a recipient phone number via WhatsApp Cloud API.
        Endpoint: POST /{phone_number_id}/messages
        """
        if not self.access_token:
            raise WhatsAppPublishError(
                "Access token is required to send WhatsApp message."
            )

        if not phone_number_id:
            raise WhatsAppPublishError("WhatsApp phone_number_id is required.")

        if not recipient or not str(recipient).strip():
            raise WhatsAppPublishError("Recipient phone number is required.")

        if not message or not str(message).strip():
            raise WhatsAppPublishError("Message body is required.")

        recipient_clean = str(recipient).strip()
        message_clean = str(message).strip()

        url = f"{self.BASE_URL}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_clean,
            "type": "text",
            "text": {"body": message_clean},
            "access_token": self.access_token,
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except Exception as e:
                logger.error(f"Network failure sending WhatsApp text message: {e}")
                raise WhatsAppPublishError(
                    f"Network error sending WhatsApp message: {e}"
                ) from e

            if response.status_code not in (200, 201):
                raise WhatsAppPublishError(
                    f"Failed to send WhatsApp text message (Status {response.status_code}): {response.text}",
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except Exception as exc:
                raise WhatsAppPublishError(
                    "WhatsApp API response returned invalid JSON."
                ) from exc

            messages = data.get("messages")
            if not messages or not isinstance(messages, list) or len(messages) == 0:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            message_id = messages[0].get("id")
            if not message_id:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            return data

    async def send_template_message(
        self,
        phone_number_id: str,
        recipient: str,
        template_name: str,
        language_code: str = "en_US",
        components: list[dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        Sends an approved pre-registered WhatsApp template message.
        Endpoint: POST /{phone_number_id}/messages
        """
        if not self.access_token:
            raise WhatsAppPublishError(
                "Access token is required to send WhatsApp message."
            )

        if not phone_number_id:
            raise WhatsAppPublishError("WhatsApp phone_number_id is required.")

        if not recipient or not str(recipient).strip():
            raise WhatsAppPublishError("Recipient phone number is required.")

        if not template_name or not str(template_name).strip():
            raise WhatsAppPublishError("Template name is required.")

        if not language_code or not str(language_code).strip():
            raise WhatsAppPublishError("Language code is required.")

        recipient_clean = str(recipient).strip()
        template_clean = str(template_name).strip()
        lang_clean = str(language_code).strip()

        template_obj: dict[str, Any] = {
            "name": template_clean,
            "language": {"code": lang_clean},
        }
        if components and isinstance(components, list):
            template_obj["components"] = components

        url = f"{self.BASE_URL}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_clean,
            "type": "template",
            "template": template_obj,
            "access_token": self.access_token,
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except Exception as e:
                logger.error(f"Network failure sending WhatsApp template message: {e}")
                raise WhatsAppPublishError(
                    f"Network error sending WhatsApp message: {e}"
                ) from e

            if response.status_code not in (200, 201):
                raise WhatsAppPublishError(
                    f"Failed to send WhatsApp template message (Status {response.status_code}): {response.text}",
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except Exception as exc:
                raise WhatsAppPublishError(
                    "WhatsApp API response returned invalid JSON."
                ) from exc

            messages = data.get("messages")
            if not messages or not isinstance(messages, list) or len(messages) == 0:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            message_id = messages[0].get("id")
            if not message_id:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            return data

    async def send_media_message(
        self,
        phone_number_id: str,
        recipient: str,
        media_type: str,
        media_url: str,
        caption: str = "",
        filename: str = "",
    ) -> Dict[str, Any]:
        """
        Sends an image, video, or document message via WhatsApp Cloud API using a public media URL.
        Endpoint: POST /{phone_number_id}/messages
        """
        if not self.access_token:
            raise WhatsAppPublishError(
                "Access token is required to send WhatsApp message."
            )

        if not phone_number_id:
            raise WhatsAppPublishError("WhatsApp phone_number_id is required.")

        if not recipient or not str(recipient).strip():
            raise WhatsAppPublishError("Recipient phone number is required.")

        if not media_type or str(media_type).lower() not in (
            "image",
            "video",
            "document",
        ):
            raise WhatsAppPublishError(
                f"Unsupported media_type '{media_type}'. Must be 'image', 'video', or 'document'."
            )

        if not media_url or not str(media_url).strip():
            raise WhatsAppPublishError("Media URL is required.")

        recipient_clean = str(recipient).strip()
        type_clean = str(media_type).lower()
        url_clean = str(media_url).strip()

        media_obj: dict[str, Any] = {"link": url_clean}
        if caption and str(caption).strip():
            media_obj["caption"] = str(caption).strip()

        if type_clean == "document" and filename and str(filename).strip():
            media_obj["filename"] = str(filename).strip()

        url = f"{self.BASE_URL}/{phone_number_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_clean,
            "type": type_clean,
            type_clean: media_obj,
            "access_token": self.access_token,
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
            except Exception as e:
                logger.error(f"Network failure sending WhatsApp media message: {e}")
                raise WhatsAppPublishError(
                    f"Network error sending WhatsApp message: {e}"
                ) from e

            if response.status_code not in (200, 201):
                raise WhatsAppPublishError(
                    f"Failed to send WhatsApp {type_clean} message (Status {response.status_code}): {response.text}",
                    status_code=response.status_code,
                )

            try:
                data = response.json()
            except Exception as exc:
                raise WhatsAppPublishError(
                    "WhatsApp API response returned invalid JSON."
                ) from exc

            messages = data.get("messages")
            if not messages or not isinstance(messages, list) or len(messages) == 0:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            message_id = messages[0].get("id")
            if not message_id:
                raise WhatsAppPublishError("WhatsApp API response missing message ID.")

            return data
