from typing import Any

import httpx

from app.integrations.base import AbstractConnector
from app.integrations.connectors.twitter.exceptions import (
    TwitterApiError,
    TwitterAuthError,
)
from app.integrations.connectors.twitter.oauth import TwitterOAuthHandler
from app.integrations.interfaces import IntegrationCapabilities


class TwitterConnector(AbstractConnector):
    """
    Connector for X (Twitter) API v2.
    Phase 1 supports OAuth 2.0 Authorization Code with PKCE.
    """

    def __init__(self, credentials: dict[str, str], access_token: str | None = None):
        super().__init__(credentials, access_token)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.oauth_handler = TwitterOAuthHandler(self.client_id, self.client_secret)

    async def connect(
        self,
        auth_code: str,
        code_verifier: str | None = None,
        redirect_uri: str | None = None,
    ) -> dict[str, Any]:
        """Exchanges authorization code for tokens using PKCE."""
        if not code_verifier:
            raise TwitterAuthError(
                "code_verifier is strictly required for X/Twitter OAuth 2.0 PKCE token exchange."
            )

        token_data = await self.oauth_handler.exchange_code(
            auth_code, code_verifier=code_verifier, redirect_uri=redirect_uri
        )
        # Fetch initial metadata to validate connection
        self.access_token = token_data["access_token"]
        try:
            profile_data = await self._fetch_profile()
            token_data["metadata"] = profile_data
        except Exception as e:
            # If fetching profile fails right after token exchange, something is wrong
            raise TwitterAuthError(
                f"Token exchange succeeded but profile fetch failed: {str(e)}"
            )

        return token_data

    async def _fetch_profile(self) -> dict[str, Any]:
        """Fetches the authenticated user's profile from X API v2."""
        if not self.access_token:
            raise TwitterAuthError("Missing access token for profile fetch.")

        url = "https://api.twitter.com/2/users/me"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise TwitterApiError(f"Failed to fetch user profile: {response.text}")

            # Extract standard data payload from API v2
            data = response.json()
            return data.get("data", {})

    async def validate(self) -> bool:
        """Validates the current access token by fetching the user profile."""
        try:
            await self._fetch_profile()
            return True
        except Exception:
            return False

    async def disconnect(self) -> bool:
        """Revokes the access token (provider-side) and local disconnect."""
        if not self.access_token:
            return True
        try:
            return await self.oauth_handler.revoke_token(self.access_token)
        except Exception:
            # If the revoke call fails (e.g. token already expired/revoked remotely),
            # we still return True so the local system can clean it up.
            return True

    async def sync(self, sync_type: str = "full") -> dict[str, Any]:
        """Fetches the user profile for sync."""
        profile_data = await self._fetch_profile()
        return {"profile": profile_data, "records_synced": 1}

    async def webhook(
        self, payload: dict[str, Any], signature: str | None = None
    ) -> dict[str, Any]:
        """Placeholder for Phase 1. Webhooks are out of scope."""
        return {}

    def get_capabilities(self) -> IntegrationCapabilities:
        """Reports the actual supported capabilities for Phase 2."""
        return IntegrationCapabilities(
            can_sync=True,
            can_webhook=False,
            supported_actions=["read_profile"],
        )
