import os
from datetime import datetime, timedelta, timezone

import httpx

from app.integrations.connectors.whatsapp.exceptions import WhatsAppAuthError
from app.integrations.connectors.whatsapp.schemas import WhatsAppTokenResponse
from app.integrations.constants import META_GRAPH_API_VERSION


class WhatsAppOAuthHandler:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    OAUTH_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = os.getenv(
            "WHATSAPP_REDIRECT_URI",
            os.getenv(
                "FACEBOOK_REDIRECT_URI",
                "http://localhost:8000/api/v1/integrations/oauth/callback",
            ),
        )
        self._exchanged_codes: set[str] = set()

    async def exchange_code(
        self, auth_code: str, redirect_uri: str | None = None
    ) -> dict:
        """Exchanges an authorization code for a short-lived access token, then upgrades it to a long-lived token."""
        import hashlib
        import logging

        logger = logging.getLogger(__name__)
        code_fp = (
            hashlib.sha256(auth_code.encode()).hexdigest()[:10] if auth_code else "none"
        )

        if code_fp in self._exchanged_codes:
            logger.warning(
                f"[WhatsApp OAuth Exchange] WARNING: exchange_code invoked MORE THAN ONCE for code_fp={code_fp}!"
            )
        self._exchanged_codes.add(code_fp)

        effective_redirect_uri = redirect_uri or self.redirect_uri
        logger.info(
            f"[WhatsApp OAuth Exchange] Exchanging code: code_fp={code_fp}, redirect_uri={effective_redirect_uri}"
        )

        # 1. Exchange for short-lived token
        params = {
            "client_id": self.client_id,
            "redirect_uri": effective_redirect_uri,
            "client_secret": self.client_secret,
            "code": auth_code,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(self.OAUTH_URL, params=params)

            if response.status_code != 200:
                logger.error(
                    f"[WhatsApp OAuth Exchange] Code exchange failed: status={response.status_code}, code_fp={code_fp}"
                )
                raise WhatsAppAuthError(f"Failed to exchange code: {response.text}")

            token_data = response.json()
            short_lived_token = token_data.get("access_token")

            if not short_lived_token:
                raise WhatsAppAuthError("Access token missing from exchange response.")

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
                raise WhatsAppAuthError(
                    f"Failed to get long-lived token: {response.text}"
                )

            token_data = response.json()
            token_response = WhatsAppTokenResponse(**token_data)

            expires_in = token_response.expires_in or (60 * 24 * 3600)

            return {
                "access_token": token_response.access_token,
                "refresh_token": None,
                "expires_at": datetime.now(timezone.utc)
                + timedelta(seconds=expires_in),
            }
