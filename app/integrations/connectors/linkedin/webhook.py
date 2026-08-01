import hashlib
import hmac
from typing import Any, Dict


class LinkedInWebhookHandler:
    def __init__(self, client_secret: str):
        self.client_secret = client_secret

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verifies the HMAC SHA256 signature of a LinkedIn webhook payload.
        LinkedIn sends this in the X-LI-Signature header.
        """
        if not signature:
            return False

        expected_signature = hmac.new(
            key=self.client_secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

        # Constant time compare to prevent timing attacks
        return hmac.compare_digest(expected_signature, signature)

    def process_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes and maps a LinkedIn webhook event to our internal format.
        """
        # Mapping logic goes here based on event type
        event_type = payload.get("eventType")

        return {
            "source": "linkedin",
            "type": event_type,
            "raw_payload": payload,
            "mapped": True,
        }
