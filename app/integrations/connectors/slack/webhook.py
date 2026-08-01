import hashlib
import hmac
import time
from typing import Any, Dict, Optional


class SlackWebhookHandler:
    def __init__(self, signing_secret: str):
        self.signing_secret = signing_secret

    def verify_signature(self, payload: bytes, signature: str, timestamp: str) -> bool:
        """
        Verifies the HMAC SHA256 signature of a Slack webhook payload.
        Slack requires combining the version 'v0', the timestamp, and the raw payload body.
        The resulting HMAC hash is compared against the 'X-Slack-Signature' header.
        """
        if not signature or not timestamp:
            return False

        # Protect against replay attacks (e.g. 5 minutes)
        try:
            if abs(time.time() - int(timestamp)) > 60 * 5:
                return False
        except ValueError:
            return False

        # Format: v0:timestamp:payload
        sig_basestring = f"v0:{timestamp}:{payload.decode('utf-8')}"

        expected_mac = hmac.new(
            key=self.signing_secret.encode("utf-8"),
            msg=sig_basestring.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        expected_signature = f"v0={expected_mac}"

        return hmac.compare_digest(expected_signature, signature)

    def verify_challenge(self, payload: Dict[str, Any]) -> Optional[str]:
        """
        Handles the url_verification challenge Slack sends when configuring the Events API.
        If it's a url_verification event, return the challenge string to echo back.
        """
        if payload.get("type") == "url_verification":
            return payload.get("challenge")
        return None

    def process_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes and maps a Slack webhook event to our internal format.
        Handles nested event envelopes for the Events API.
        """
        event_type = payload.get("type")

        # Unpack actual event from envelope if using Events API
        if event_type == "event_callback":
            inner_event = payload.get("event", {})
            event_type = inner_event.get("type", "unknown_callback")

        return {
            "source": "slack",
            "type": event_type,
            "raw_payload": payload,
            "mapped": True,
        }
