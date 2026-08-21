from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.constants.enums import ApiProvider
from app.db.session import AsyncSessionLocal
from app.integrations.connectors.linkedin.exceptions import LinkedInAuthError
from app.integrations.connectors.linkedin.oauth import LinkedInOAuthHandler
from app.integrations.connectors.linkedin.publisher import LinkedInPublisher
from app.integrations.connectors.linkedin.sync import LinkedInSyncEngine
from app.integrations.exceptions import IntegrationError
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.secrets.service import secret_service
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.repositories.social_account import social_account_repo
from app.services.social.base import BaseSocialProvider


class LinkedInProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.LINKEDIN.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        if not account.access_token:
            raise IntegrationError("LinkedIn SocialAccount missing access token.")

        if not content.body or not content.body.strip():
            raise IntegrationError(
                "LinkedIn text publishing requires non-empty body content."
            )

        if not account.account_id or not account.account_id.startswith(
            "urn:li:person:"
        ):
            raise IntegrationError(f"Invalid LinkedIn author URN: {account.account_id}")

        # Check token expiration
        now_utc = datetime.now(timezone.utc)
        acc_expires = account.expires_at
        if acc_expires and acc_expires.tzinfo is None:
            acc_expires = acc_expires.replace(tzinfo=timezone.utc)

        if acc_expires and acc_expires < now_utc + timedelta(minutes=5):
            if not account.refresh_token:
                raise LinkedInAuthError(
                    "LinkedIn token expired and no refresh token available."
                )

            decrypted_refresh = secret_service.decrypt_token(account.refresh_token)
            credentials = secret_service.get_provider_credentials(
                ApiProvider.LINKEDIN.value
            )
            oauth_handler = LinkedInOAuthHandler(
                client_id=credentials.get("client_id", ""),
                client_secret=credentials.get("client_secret", ""),
            )

            new_tokens = await oauth_handler.refresh_token(decrypted_refresh)

            enc_access = secret_service.encrypt_token(new_tokens["access_token"])

            # Preserve existing refresh token if not returned
            if new_tokens.get("refresh_token"):
                enc_refresh = secret_service.encrypt_token(new_tokens["refresh_token"])
            else:
                enc_refresh = account.refresh_token

            new_expires_at = new_tokens["expires_at"]

            # Safely fetch and update BOTH IntegrationConnection and SocialAccount in a dedicated local session
            async with AsyncSessionLocal() as session:
                try:
                    conn = (
                        await integration_connection_repo.get_by_workspace_and_provider(
                            session, account.workspace_id, ApiProvider.LINKEDIN.value
                        )
                    )
                    soc_account = await social_account_repo.get_by_id(
                        session, id=account.id
                    )

                    if not conn or not soc_account:
                        raise LinkedInAuthError(
                            "Missing database records for token persistence."
                        )

                    # Update BOTH records in the same dedicated session
                    conn.access_token = enc_access
                    conn.refresh_token = enc_refresh
                    # IntegrationConnection uses naive UTC
                    conn.expires_at = (
                        new_expires_at.replace(tzinfo=None) if new_expires_at else None
                    )

                    soc_account.access_token = enc_access
                    soc_account.refresh_token = enc_refresh
                    # SocialAccount uses timezone-aware
                    soc_account.expires_at = new_expires_at

                    # Commit BOTH changes together
                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise LinkedInAuthError(
                        f"Failed to persist refreshed tokens: {str(e)}"
                    )

            # Update the in-memory object ONLY after commit succeeds
            account.access_token = enc_access
            account.refresh_token = enc_refresh
            account.expires_at = new_expires_at

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = LinkedInPublisher(access_token=decrypted_token)

        # Look for the first image asset
        from app.constants.enums import AssetType

        image_asset = next(
            (a for a in content.assets if a.asset_type == AssetType.IMAGE), None
        )

        if image_asset:
            if not image_asset.public_url:
                raise IntegrationError("Image asset is missing a public URL.")

            supported_mimes = {"image/jpeg", "image/png", "image/gif"}
            if image_asset.mime_type not in supported_mimes:
                raise IntegrationError(
                    f"Unsupported LinkedIn image MIME type: {image_asset.mime_type}"
                )

            # Enforce reasonable size limit (5MB) before loading entirely to memory
            max_size_bytes = 5 * 1024 * 1024

            # We must use a separate client to download the public asset
            async with httpx.AsyncClient() as client:
                try:
                    # Stream the response to check content length safely
                    async with client.stream("GET", image_asset.public_url) as response:
                        response.raise_for_status()

                        content_length = response.headers.get("Content-Length")
                        if content_length and int(content_length) > max_size_bytes:
                            raise IntegrationError(
                                f"Image size exceeds the maximum allowed limit of {max_size_bytes} bytes."
                            )

                        image_binary = await response.aread()

                        if len(image_binary) > max_size_bytes:
                            raise IntegrationError(
                                f"Downloaded image size exceeds the maximum allowed limit of {max_size_bytes} bytes."
                            )

                except httpx.RequestError as e:
                    raise IntegrationError(
                        f"Failed to download image from {image_asset.public_url}: {str(e)}"
                    )

            post_id = await publisher.publish_image_post(
                author_urn=account.account_id,
                text=content.body,
                image_binary=image_binary,
                mime_type=image_asset.mime_type,
            )
        else:
            post_id = await publisher.publish_text_post(
                author_urn=account.account_id, text=content.body
            )

        if not post_id:
            raise IntegrationError("Failed to retrieve valid post ID from LinkedIn.")

        return str(post_id)

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        decrypted_token = secret_service.decrypt_token(access_token)
        sync_engine = LinkedInSyncEngine(decrypted_token)
        profile_data = await sync_engine.fetch_profile()

        sub = profile_data.get("sub")
        if not sub:
            raise LinkedInAuthError(
                "LinkedIn profile response is missing the required 'sub' identifier."
            )

        profile_name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()

        return {
            "account_id": f"urn:li:person:{sub}",
            "name": profile_name,
            "username": profile_name,
            "profile_url": None,
        }
