import hashlib
import hmac
from typing import Any, Dict

from app.integrations.exceptions import WebhookVerificationError


class InstagramWebhookHandler:
    def __init__(self, client_secret: str):
        self.client_secret = client_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifies the HMAC SHA256 signature of an Instagram webhook payload.
        Instagram webhooks are routed through Facebook's webhook infrastructure
        and use the identical X-Hub-Signature-256 header.
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
        Verifies the hub.challenge when subscribing to a webhook.
        """
        if mode == "subscribe" and verify_token == expected_verify_token:
            return challenge
        raise WebhookVerificationError("Invalid verify token or mode")

    def process_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes and maps an Instagram webhook event to our internal format.
        """
        # Instagram webhook payloads arrive inside an "entry" list, often with "object": "instagram"
        object_type = payload.get("object")

        return {
            "source": "instagram",
            "type": object_type,
            "raw_payload": payload,
            "mapped": True,
        }
