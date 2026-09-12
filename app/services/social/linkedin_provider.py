from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import httpx

from app.constants.enums import ApiProvider, AssetType
from app.db.session import AsyncSessionLocal
from app.integrations.connectors.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInPublishError,
)
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

        if not account.account_id or not (
            account.account_id.startswith("urn:li:person:")
            or account.account_id.startswith("urn:li:organization:")
        ):
            raise IntegrationError(f"Invalid LinkedIn author URN: {account.account_id}")

        # Token Expiration / Refresh Check
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

            try:
                new_tokens = await oauth_handler.refresh_token(decrypted_refresh)
            except Exception as exc:
                raise LinkedInAuthError(
                    f"LinkedIn token refresh failed: {exc}. Please re-authenticate."
                ) from exc

            enc_access = secret_service.encrypt_token(new_tokens["access_token"])
            enc_refresh = (
                secret_service.encrypt_token(new_tokens["refresh_token"])
                if new_tokens.get("refresh_token")
                else account.refresh_token
            )
            new_expires_at = new_tokens["expires_at"]

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

                    if conn:
                        conn.access_token = enc_access
                        conn.refresh_token = enc_refresh
                        conn.expires_at = (
                            new_expires_at.replace(tzinfo=None)
                            if new_expires_at
                            else None
                        )

                    if soc_account:
                        soc_account.access_token = enc_access
                        soc_account.refresh_token = enc_refresh
                        soc_account.expires_at = new_expires_at

                    await session.commit()
                except Exception as e:
                    await session.rollback()
                    raise LinkedInAuthError(
                        f"Failed to persist refreshed tokens: {e}"
                    ) from e

            account.access_token = enc_access
            account.refresh_token = enc_refresh
            account.expires_at = new_expires_at

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = LinkedInPublisher(access_token=decrypted_token)

        # Asset Routing: Image, Video, or Text
        image_asset = next(
            (
                a
                for a in content.assets
                if getattr(a, "asset_type", None) in (AssetType.IMAGE, "IMAGE", "image")
            ),
            None,
        )
        video_asset = next(
            (
                a
                for a in content.assets
                if getattr(a, "asset_type", None) in (AssetType.VIDEO, "VIDEO", "video")
            ),
            None,
        )

        try:
            if video_asset:
                video_url = getattr(video_asset, "public_url", None) or getattr(
                    video_asset, "file_path", None
                )
                if not video_url:
                    raise IntegrationError("LinkedIn video asset missing public URL.")

                video_binary, mime_type = await self._download_asset_binary(
                    video_url, max_size_mb=100
                )
                post_id = await publisher.publish_video_post(
                    author_urn=account.account_id,
                    text=content.body or "",
                    video_binary=video_binary,
                    mime_type=mime_type or "video/mp4",
                    title=content.title or "",
                )

            elif image_asset:
                image_url = getattr(image_asset, "public_url", None) or getattr(
                    image_asset, "file_path", None
                )
                if not image_url:
                    raise IntegrationError("Image asset is missing a public URL.")

                mime_type = getattr(image_asset, "mime_type", "image/jpeg")
                supported_mimes = {
                    "image/jpeg",
                    "image/png",
                    "image/gif",
                    "application/octet-stream",
                }
                if mime_type not in supported_mimes:
                    raise IntegrationError(
                        f"Unsupported LinkedIn image MIME type: {mime_type}"
                    )

                image_binary, downloaded_mime = await self._download_asset_binary(
                    image_url, max_size_mb=10
                )
                post_id = await publisher.publish_image_post(
                    author_urn=account.account_id,
                    text=content.body or "",
                    image_binary=image_binary,
                    mime_type=(
                        mime_type
                        if mime_type != "application/octet-stream"
                        else downloaded_mime
                    ),
                )

            else:
                post_id = await publisher.publish_text_post(
                    author_urn=account.account_id, text=content.body
                )
        except (LinkedInPublishError, LinkedInAuthError) as exc:
            raise IntegrationError(f"LinkedIn publishing failed: {exc}") from exc

        if not post_id:
            raise IntegrationError("Failed to retrieve valid post ID from LinkedIn.")

        return str(post_id)

    async def _download_asset_binary(
        self, url: str, max_size_mb: int
    ) -> Tuple[bytes, str]:
        """Helper to download media binary safely with content length limits."""
        max_size_bytes = max_size_mb * 1024 * 1024
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    mime_type = (
                        response.headers.get("Content-Type", "application/octet-stream")
                        .split(";")[0]
                        .strip()
                    )
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_size_bytes:
                        raise IntegrationError(
                            f"Image size exceeds the maximum allowed limit of {max_size_bytes} bytes."
                        )

                    binary_data = await response.aread()
                    if len(binary_data) > max_size_bytes:
                        raise IntegrationError(
                            f"Downloaded image size exceeds the maximum allowed limit of {max_size_bytes} bytes."
                        )

                    return binary_data, mime_type
            except httpx.HTTPStatusError as e:
                raise IntegrationError(
                    f"Failed to download image from {url}: HTTP {e.response.status_code}"
                ) from e
            except httpx.RequestError as e:
                raise IntegrationError(
                    f"Failed to download image from {url}: {e}"
                ) from e

    async def get_account_info(self, account: SocialAccount | str) -> Dict[str, Any]:
        """Fetches profile or organization details for a connected LinkedIn account or token string."""
        if isinstance(account, str):
            access_token = account
            account_id = None
            account_name = "LinkedIn Member"
        else:
            if not account.access_token:
                raise IntegrationError(
                    f"No access token available for LinkedIn account {account.id}"
                )
            access_token = account.access_token
            account_id = account.account_id
            account_name = account.name or "LinkedIn Member"

        decrypted_token = secret_service.decrypt_token(access_token)
        sync_engine = LinkedInSyncEngine(decrypted_token)

        if account_id and account_id.startswith("urn:li:organization:"):
            return {
                "account_id": account_id,
                "name": account_name or f"Company Page ({account_id})",
                "username": account_name or f"Company Page ({account_id})",
                "profile_url": None,
            }

        profile_data = await sync_engine.fetch_profile()
        sub = profile_data.get("sub")
        if not sub:
            raise LinkedInAuthError(
                "LinkedIn profile response is missing the required 'sub' identifier."
            )

        profile_name = (
            profile_data.get("name")
            or f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
            or "LinkedIn Member"
        )

        return {
            "account_id": f"urn:li:person:{sub}",
            "name": profile_name,
            "username": profile_name,
            "profile_url": None,
        }
