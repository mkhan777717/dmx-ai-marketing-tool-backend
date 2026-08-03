import os
from datetime import datetime, timedelta, timezone

import httpx

from app.integrations.connectors.google.exceptions import GoogleAuthError
from app.integrations.connectors.google.schemas import GoogleTokenResponse


class GoogleOAuthHandler:
    OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:8000/api/v1/integrations/oauth/callback",
        )

    async def exchange_code(self, auth_code: str) -> dict:
        """Exchanges an authorization code for an access token and optionally a refresh token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.OAUTH_TOKEN_URL, data=data)

            if response.status_code != 200:
                raise GoogleAuthError(f"Failed to exchange code: {response.text}")

            token_data = response.json()
            token_response = GoogleTokenResponse(**token_data)

            return {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_response.expires_in),
            }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Exchanges a refresh token for a new access token."""
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.OAUTH_TOKEN_URL, data=data)

            if response.status_code != 200:
                raise GoogleAuthError(f"Failed to refresh token: {response.text}")

            token_data = response.json()

            return {
                "access_token": token_data.get("access_token"),
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_data.get("expires_in", 3599)),
            }
