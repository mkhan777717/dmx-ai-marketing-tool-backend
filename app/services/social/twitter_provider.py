from datetime import datetime, timedelta, timezone

import httpx

from app.constants.enums import ApiProvider
from app.db.session import AsyncSessionLocal
from app.integrations.connectors.twitter.exceptions import (
    TwitterAuthError,
    TwitterError,
)
from app.integrations.connectors.twitter.oauth import TwitterOAuthHandler
from app.integrations.connectors.twitter.publisher import TwitterPublisher
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.secrets.service import secret_service
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.repositories.social_account import social_account_repo
from app.services.social.base import BaseSocialProvider


class TwitterProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.TWITTER.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        if not account.access_token:
            raise TwitterError("Twitter SocialAccount missing access token.")

        if not content.body or not content.body.strip():
            raise TwitterError(
                "Twitter text publishing requires non-empty body content."
            )

        # Check token expiration
        now_utc = datetime.now(timezone.utc)
        acc_expires = account.expires_at
        if acc_expires and acc_expires.tzinfo is None:
            acc_expires = acc_expires.replace(tzinfo=timezone.utc)

        if acc_expires and acc_expires < now_utc + timedelta(minutes=5):
            if not account.refresh_token:
                raise TwitterAuthError(
                    "Twitter token expired and no refresh token available."
                )

            decrypted_refresh = secret_service.decrypt_token(account.refresh_token)
            credentials = secret_service.get_provider_credentials(
                ApiProvider.TWITTER.value
            )
            oauth_handler = TwitterOAuthHandler(
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
                            session, account.workspace_id, ApiProvider.TWITTER.value
                        )
                    )
                    soc_account = await social_account_repo.get_by_id(
                        session, id=account.id
                    )

                    if not conn or not soc_account:
                        raise TwitterAuthError(
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
                    raise TwitterAuthError(
                        f"Failed to persist refreshed tokens: {str(e)}"
                    )

            # Update the in-memory object ONLY after commit succeeds
            account.access_token = enc_access
            account.refresh_token = enc_refresh
            account.expires_at = new_expires_at

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = TwitterPublisher(access_token=decrypted_token)

        media_ids = []
        if content.assets:
            has_video = any(a.mime_type.startswith("video/") for a in content.assets)

            if has_video and len(content.assets) > 1:
                raise TwitterError(
                    "Twitter does not support attaching multiple videos or mixing images with video in a single post."
                )

            assets_to_upload = (
                content.assets[:4] if not has_video else [content.assets[0]]
            )

            async with httpx.AsyncClient(timeout=60.0) as client:
                for asset in assets_to_upload:
                    if not asset.public_url or not asset.public_url.startswith(
                        ("http://", "https://")
                    ):
                        raise TwitterError(
                            "Asset public_url must be a valid HTTP/HTTPS URL."
                        )

                    is_video = asset.mime_type.startswith("video/")

                    if is_video:
                        if asset.file_size > 512 * 1024 * 1024:
                            raise TwitterError(
                                f"Video {asset.file_name} exceeds 512MB limit."
                            )
                        if asset.mime_type not in ["video/mp4", "video/quicktime"]:
                            raise TwitterError(
                                f"Video format {asset.mime_type} is not supported for Twitter MVP."
                            )

                        try:
                            # Stream the video in chunks to avoid OOM
                            async with client.stream(
                                "GET", asset.public_url
                            ) as response:
                                response.raise_for_status()

                                async def chunk_generator():
                                    async for chunk in response.aiter_bytes(
                                        chunk_size=1024 * 1024 * 4
                                    ):  # 4MB chunks
                                        yield chunk

                                media_id = await publisher.upload_media(
                                    file_bytes=chunk_generator(),
                                    mime_type=asset.mime_type,
                                    total_bytes=asset.file_size,
                                    media_category="tweet_video",
                                )
                                media_ids.append(media_id)
                        except Exception as e:
                            raise TwitterError(
                                f"Failed to stream and upload video {asset.file_name}: {str(e)}"
                            )
                    else:
                        # Image flow
                        if asset.file_size > 5 * 1024 * 1024:
                            raise TwitterError(
                                f"Image {asset.file_name} exceeds 5MB limit."
                            )
                        if asset.mime_type not in [
                            "image/jpeg",
                            "image/png",
                            "image/webp",
                        ]:
                            raise TwitterError(
                                f"Image format {asset.mime_type} is not supported for Twitter MVP."
                            )

                        try:
                            img_response = await client.get(asset.public_url)
                            img_response.raise_for_status()
                            file_bytes = img_response.content

                            media_id = await publisher.upload_media(
                                file_bytes=file_bytes,
                                mime_type=asset.mime_type,
                                total_bytes=len(file_bytes),
                                media_category="tweet_image",
                            )
                            media_ids.append(media_id)
                        except Exception as e:
                            raise TwitterError(
                                f"Failed to download and upload image {asset.file_name}: {str(e)}"
                            )

        post_id = await publisher.publish_post(
            text=content.body, media_ids=media_ids if media_ids else None
        )

        if not post_id:
            raise TwitterError("Failed to retrieve valid post ID from Twitter.")

        return str(post_id)

    async def get_account_info(self, access_token: str) -> dict:
        raise NotImplementedError("Twitter OAuth not yet implemented")
