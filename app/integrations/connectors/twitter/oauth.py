import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.integrations.connectors.twitter.exceptions import TwitterAuthError
from app.integrations.connectors.twitter.schemas import TwitterTokenResponse


class TwitterOAuthHandler:
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    REVOKE_URL = "https://api.twitter.com/2/oauth2/revoke"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "TWITTER_REDIRECT_URI",
            "http://localhost:8000/api/v1/integrations/oauth/callback",
        )

    def _get_auth_headers(self) -> dict[str, str]:
        """Generate Authorization header if client_secret is provided (Confidential Client)."""
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if self.client_secret:
            auth_string = f"{self.client_id}:{self.client_secret}"
            b64_auth = base64.b64encode(auth_string.encode()).decode()
            headers["Authorization"] = f"Basic {b64_auth}"
        return headers

    async def exchange_code(
        self, auth_code: str, code_verifier: str | None = None
    ) -> dict[str, Any]:
        """Exchanges an authorization code for an access token using PKCE."""
        if not code_verifier:
            raise TwitterAuthError(
                "code_verifier is strictly required for X/Twitter OAuth 2.0 PKCE token exchange."
            )

        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "code_verifier": code_verifier,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL, data=data, headers=self._get_auth_headers()
            )

            if response.status_code != 200:
                raise TwitterAuthError(f"Failed to exchange code: {response.text}")

            token_data = response.json()
            token_response = TwitterTokenResponse(**token_data)

            return {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_response.expires_in),
            }

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Exchanges a refresh token for a new access token."""
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL, data=data, headers=self._get_auth_headers()
            )

            if response.status_code != 200:
                raise TwitterAuthError(f"Failed to refresh token: {response.text}")

            token_data = response.json()
            token_response = TwitterTokenResponse(**token_data)

            return {
                "access_token": token_response.access_token,
                "refresh_token": token_response.refresh_token,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=token_response.expires_in),
            }

    async def revoke_token(self, access_token: str) -> bool:
        """Revokes an access token (Official API v2 Revocation Endpoint)."""
        data = {
            "token": access_token,
            "token_type_hint": "access_token",
            "client_id": self.client_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.REVOKE_URL, data=data, headers=self._get_auth_headers()
            )
            # Response is 200 OK on success
            return response.status_code == 200
