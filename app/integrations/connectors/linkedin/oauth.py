import os
from datetime import datetime, timedelta, timezone

import httpx

from app.integrations.connectors.linkedin.exceptions import LinkedInAuthError
from app.integrations.connectors.linkedin.schemas import LinkedInTokenResponse


class LinkedInOAuthHandler:
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "LINKEDIN_REDIRECT_URI",
            "http://localhost:8000/api/v1/integrations/oauth/callback",
        )

    async def exchange_code(
        self, auth_code: str, redirect_uri: str | None = None
    ) -> dict:
        """Exchanges an authorization code for an access token."""
        effective_redirect_uri = redirect_uri or self.redirect_uri
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": effective_redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)

            if response.status_code != 200:
                raise LinkedInAuthError(f"Failed to exchange code: {response.text}")

            token_data = response.json()
            token_response = LinkedInTokenResponse(**token_data)

            return {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_response.expires_in),
            }

    async def refresh_token(self, refresh_token: str) -> dict:
        """Refreshes an access token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.TOKEN_URL, data=data)

            if response.status_code != 200:
                raise LinkedInAuthError(f"Failed to refresh token: {response.text}")

            token_data = response.json()
            token_response = LinkedInTokenResponse(**token_data)

            return {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token or refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_response.expires_in),
            }
