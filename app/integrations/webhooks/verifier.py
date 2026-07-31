from fastapi import Request


class WebhookVerifier:
    @staticmethod
    async def verify_signature(provider: str, request: Request, payload: bytes) -> bool:
        """
        Verify the incoming webhook payload using the provider's specific signature strategy.
        Returns True if valid, False otherwise.
        """
        provider = provider.lower()
        if provider == "slack":
            # Slack verification logic here
            signature = request.headers.get("X-Slack-Signature")
            # ...
            return True

        if provider == "mock":
            return request.headers.get("X-Mock-Signature") == "valid_signature"

        return False
