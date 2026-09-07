from fastapi import Request

from app.integrations.connectors.facebook.webhook import FacebookWebhookHandler
from app.integrations.connectors.instagram.webhook import InstagramWebhookHandler
from app.integrations.connectors.slack.webhook import SlackWebhookHandler
from app.integrations.connectors.whatsapp.webhook import WhatsAppWebhookHandler
from app.integrations.secrets.service import secret_service


class WebhookVerifier:
    @staticmethod
    async def verify_signature(provider: str, request: Request, payload: bytes) -> bool:
        """
        Verify the incoming webhook payload using the provider's specific signature strategy.
        Returns True if valid, False otherwise.
        """
        provider = provider.lower()

        if provider == "instagram":
            credentials = secret_service.get_provider_credentials("instagram")
            handler = InstagramWebhookHandler(credentials.get("client_secret", ""))
            signature = request.headers.get("X-Hub-Signature-256", "")
            return handler.verify_signature(payload, signature)

        if provider == "whatsapp":
            credentials = secret_service.get_provider_credentials("whatsapp")
            handler = WhatsAppWebhookHandler(credentials.get("client_secret", ""))
            signature = request.headers.get("X-Hub-Signature-256", "")
            return handler.verify_signature(payload, signature)

        if provider in ("facebook", "meta"):
            credentials = secret_service.get_provider_credentials("facebook")
            handler = FacebookWebhookHandler(credentials.get("client_secret", ""))
            signature = request.headers.get("X-Hub-Signature-256", "")
            return handler.verify_signature(payload, signature)

        if provider == "slack":
            credentials = secret_service.get_provider_credentials("slack")
            signing_secret = (
                credentials.get("signing_secret")
                or secret_service.adapter.get_secret("SLACK_SIGNING_SECRET")
                or ""
            )
            handler = SlackWebhookHandler(signing_secret)
            signature = request.headers.get("X-Slack-Signature", "")
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            return handler.verify_signature(payload, signature, timestamp)

        if provider == "mock":
            return request.headers.get("X-Mock-Signature") == "valid_signature"

        return False
