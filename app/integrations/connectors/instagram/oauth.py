import os
from datetime import datetime, timedelta, timezone

import httpx

from app.integrations.connectors.instagram.exceptions import InstagramAuthError
from app.integrations.connectors.instagram.schemas import InstagramTokenResponse


class InstagramOAuthHandler:
    # Instagram Graph API uses the Facebook Graph API endpoints for OAuth
    GRAPH_API_VERSION = "v18.0"
    OAUTH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "INSTAGRAM_REDIRECT_URI",
            "http://localhost:8000/api/v1/integrations/oauth/callback",
        )

    async def exchange_code(self, auth_code: str) -> dict:
        """Exchanges an authorization code for a short-lived access token, then upgrades it to a long-lived token."""
        # 1. Exchange for short-lived token
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.client_secret,
            "code": auth_code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.OAUTH_URL, params=params)

            if response.status_code != 200:
                raise InstagramAuthError(f"Failed to exchange code: {response.text}")

            token_data = response.json()
            short_lived_token = token_data.get("access_token")

            if not short_lived_token:
                raise InstagramAuthError("Access token missing from exchange response.")

            # 2. Exchange for long-lived token
            return await self.exchange_for_long_lived_token(short_lived_token)

    async def exchange_for_long_lived_token(self, short_lived_token: str) -> dict:
        """Exchanges a short-lived token for a 60-day long-lived token."""
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "fb_exchange_token": short_lived_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.OAUTH_URL, params=params)

            if response.status_code != 200:
                raise InstagramAuthError(
                    f"Failed to get long-lived token: {response.text}"
                )

            token_data = response.json()
            token_response = InstagramTokenResponse(**token_data)

            expires_in = token_response.expires_in or (60 * 24 * 3600)

            return {
                "access_token": token_response.access_token,
                "refresh_token": None,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=expires_in),
            }
