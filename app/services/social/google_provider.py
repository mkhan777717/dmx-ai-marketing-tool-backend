from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ApiProvider
from app.db.session import AsyncSessionLocal
from app.integrations.connectors.google.business_profile import (
    GoogleBusinessProfilePublisher,
)
from app.integrations.connectors.google.exceptions import (
    GoogleAuthError,
    GoogleError,
)
from app.integrations.connectors.google.oauth import GoogleOAuthHandler
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.secrets.service import secret_service
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.repositories.social_account import social_account_repo
from app.services.social.base import BaseSocialProvider


class GoogleProvider(BaseSocialProvider):
    def __init__(self):
        super().__init__()

    @property
    def provider_name(self) -> str:
        return "google"

    async def get_account_info(
        self, db: AsyncSession, account: SocialAccount
    ) -> dict[str, Any]:
        """
        Retrieves basic account info.
        """
        return {
            "id": account.account_id,
            "name": account.name,
            "provider": "google",
        }

    async def publish_content(
        self,
        db: AsyncSession,
        account: SocialAccount,
        content: CampaignContent,
        **kwargs,
    ) -> str:
        if not account.access_token:
            raise GoogleAuthError("Google SocialAccount missing access token.")

        if not content.body or not content.body.strip():
            raise GoogleError("Google text publishing requires non-empty body content.")

        image_url = None
        is_video = False
        if content.assets:
            if len(content.assets) > 1:
                raise GoogleError(
                    "Google Provider only supports a single image or video for publishing."
                )
            asset = content.assets[0]
            if not asset.public_url or not asset.public_url.startswith(
                ("http://", "https://")
            ):
                raise GoogleError("Asset public_url must be a valid HTTP/HTTPS URL.")

            is_video = bool(asset.mime_type and asset.mime_type.startswith("video/"))
            is_image = bool(asset.mime_type and asset.mime_type.startswith("image/"))

            if not is_video and not is_image:
                raise GoogleError(
                    f"Unsupported MIME type {asset.mime_type}. Only images and videos are supported."
                )

            if is_image:
                if asset.mime_type not in ["image/jpeg", "image/png", "image/webp"]:
                    raise GoogleError(
                        f"Image format {asset.mime_type} is not supported by Google Business Profile."
                    )
                image_url = asset.public_url

        # Check token expiration
        now_utc = datetime.now(timezone.utc)
        acc_expires = account.expires_at
        if acc_expires and acc_expires.tzinfo is None:
            acc_expires = acc_expires.replace(tzinfo=timezone.utc)

        if acc_expires and acc_expires < now_utc + timedelta(minutes=5):
            if not account.refresh_token:
                raise GoogleAuthError(
                    "Google token expired and no refresh token available."
                )

            decrypted_refresh = secret_service.decrypt_token(account.refresh_token)
            credentials = secret_service.get_provider_credentials(
                ApiProvider.GOOGLE.value
            )
            oauth_handler = GoogleOAuthHandler(
                client_id=credentials.get("client_id", ""),
                client_secret=credentials.get("client_secret", ""),
            )

            new_tokens = await oauth_handler.refresh_access_token(decrypted_refresh)

            enc_access = secret_service.encrypt_token(new_tokens["access_token"])

            # Preserve existing refresh token if not returned (Google doesn't always return it)
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
                            session, account.workspace_id, ApiProvider.GOOGLE.value
                        )
                    )
                    soc_account = await social_account_repo.get_by_id(
                        session, id=account.id
                    )

                    if not conn or not soc_account:
                        raise GoogleAuthError(
                            "Missing database records for token persistence."
                        )

                    # Update BOTH records in the same dedicated session
                    conn.access_token = enc_access
                    conn.refresh_token = enc_refresh
                    # IntegrationConnection uses naive UTC typically
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
                    raise GoogleAuthError(
                        f"Failed to persist refreshed tokens: {str(e)}"
                    )

            # Update the in-memory object ONLY after commit succeeds
            account.access_token = enc_access
            account.refresh_token = enc_refresh
            account.expires_at = new_expires_at

        decrypted_token = secret_service.decrypt_token(account.access_token)

        if is_video:
            from app.integrations.connectors.google.youtube import YouTubePublisher

            asset = content.assets[0]
            publisher = YouTubePublisher(access_token=decrypted_token)

            # Use body as both title and description for YouTube in MVP
            post_id = await publisher.upload_video(
                asset_url=asset.public_url,
                title=content.body,
                description=content.body,
                file_size=asset.file_size,
                mime_type=asset.mime_type,
            )
            return str(post_id)
        else:
            publisher = GoogleBusinessProfilePublisher(access_token=decrypted_token)
            post_name = await publisher.publish_post(
                account_id=account.account_id,
                text=content.body,
                image_url=image_url,
            )
            return str(post_name)
