import hashlib
import hmac
import logging
from typing import Any, Dict

from app.integrations.exceptions import WebhookVerificationError

logger = logging.getLogger(__name__)


class WhatsAppWebhookHandler:
    def __init__(self, client_secret: str):
        self.client_secret = client_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifies the HMAC SHA256 signature of a WhatsApp webhook payload.
        Meta Cloud API sends this in the X-Hub-Signature-256 header.
        Format: sha256=mac
        """
        if (
            not self.client_secret
            or not signature
            or not signature.startswith("sha256=")
        ):
            return False

        received_mac = signature[7:]  # Strip 'sha256='

        expected_signature = hmac.new(
            key=self.client_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, received_mac)

    def verify_challenge(
        self, mode: str, verify_token: str, challenge: str, expected_verify_token: str
    ) -> str:
        """
        Verifies the WhatsApp hub.challenge when subscribing to a webhook.
        """
        if (
            mode == "subscribe"
            and expected_verify_token
            and verify_token == expected_verify_token
        ):
            return challenge
        raise WebhookVerificationError("Invalid verify token or mode")

    def parse_webhook_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses a Meta WhatsApp Cloud API webhook payload into structured events.
        Extracts phone_number_id, statuses, incoming messages, and contact info.
        """
        result: Dict[str, Any] = {
            "source": "whatsapp",
            "object": payload.get("object"),
            "statuses": [],
            "messages": [],
            "phone_number_id": None,
        }

        entries = payload.get("entry", [])
        if not isinstance(entries, list):
            return result

        for entry in entries:
            changes = entry.get("changes", [])
            if not isinstance(changes, list):
                continue

            for change in changes:
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue

                metadata = value.get("metadata", {})
                if isinstance(metadata, dict) and metadata.get("phone_number_id"):
                    result["phone_number_id"] = metadata.get("phone_number_id")

                # Parse Status Events
                statuses = value.get("statuses", [])
                if isinstance(statuses, list):
                    for status_item in statuses:
                        if isinstance(status_item, dict):
                            parsed_status = self._parse_status_item(
                                status_item, metadata
                            )
                            result["statuses"].append(parsed_status)

                # Parse Incoming Message Events
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])
                contact_map = {}
                if isinstance(contacts, list):
                    for c in contacts:
                        if isinstance(c, dict) and c.get("wa_id"):
                            contact_map[c.get("wa_id")] = c.get("profile", {}).get(
                                "name", ""
                            )

                if isinstance(messages, list):
                    for msg_item in messages:
                        if isinstance(msg_item, dict):
                            parsed_msg = self._parse_message_item(
                                msg_item, metadata, contact_map
                            )
                            result["messages"].append(parsed_msg)

        return result

    def _parse_status_item(
        self, item: Dict[str, Any], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extracts status details (sent, delivered, read, failed)."""
        status_str = str(item.get("status", "unknown")).lower()
        errors = item.get("errors", [])
        error_detail = None
        if errors and isinstance(errors, list) and len(errors) > 0:
            err = errors[0]
            if isinstance(err, dict):
                error_detail = f"Code {err.get('code')}: {err.get('title', err.get('message', 'Unknown error'))}"

        return {
            "message_id": item.get("id"),
            "recipient_id": item.get("recipient_id"),
            "status": status_str,
            "timestamp": item.get("timestamp"),
            "phone_number_id": metadata.get("phone_number_id"),
            "error_detail": error_detail,
            "conversation": item.get("conversation"),
            "pricing": item.get("pricing"),
        }

    def _parse_message_item(
        self,
        item: Dict[str, Any],
        metadata: Dict[str, Any],
        contact_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Extracts incoming message details."""
        msg_type = item.get("type", "unknown")
        sender = item.get("from")
        text_body = None

        if msg_type == "text":
            text_obj = item.get("text", {})
            if isinstance(text_obj, dict):
                text_body = text_obj.get("body")

        return {
            "message_id": item.get("id"),
            "from": sender,
            "sender_name": contact_map.get(sender, ""),
            "timestamp": item.get("timestamp"),
            "type": msg_type,
            "body": text_body,
            "phone_number_id": metadata.get("phone_number_id"),
            "display_phone_number": metadata.get("display_phone_number"),
        }
