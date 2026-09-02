import os

import httpx

from app.integrations.connectors.slack.exceptions import SlackAuthError
from app.integrations.connectors.slack.schemas import SlackOAuthResponse


class SlackOAuthHandler:
    OAUTH_ACCESS_URL = "https://slack.com/api/oauth.v2.access"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "SLACK_REDIRECT_URI",
            "http://localhost:8000/api/v1/integrations/oauth/callback",
        )

    async def exchange_code(
        self, auth_code: str, redirect_uri: str | None = None
    ) -> dict:
        """Exchanges an authorization code for a bot access token and workspace info."""
        effective_redirect_uri = redirect_uri or self.redirect_uri
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "redirect_uri": effective_redirect_uri,
        }

        # Slack requires POST requests for OAuth with form-encoded data
        async with httpx.AsyncClient() as client:
            response = await client.post(self.OAUTH_ACCESS_URL, data=data)

            if response.status_code != 200:
                raise SlackAuthError(
                    f"HTTP error during code exchange: {response.status_code}"
                )

            token_data = response.json()

            if not token_data.get("ok"):
                error_msg = token_data.get("error", "Unknown Slack OAuth Error")
                raise SlackAuthError(f"Slack OAuth failed: {error_msg}")

            validated_data = SlackOAuthResponse(**token_data)

            # Slack bot tokens don't typically expire by default,
            # though user tokens might if token rotation is enabled.
            # We assume bot token usage for this integration.
            return {
                "access_token": validated_data.access_token,
                "team_id": validated_data.team.id,
                "team_name": validated_data.team.name,
                "bot_user_id": validated_data.bot_user_id,
                "app_id": validated_data.app_id,
            }
