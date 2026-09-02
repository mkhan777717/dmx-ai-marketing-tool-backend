from typing import Any

from app.constants.enums import ApiProvider
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider


class InstagramProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.INSTAGRAM.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        from app.constants.enums import AssetType
        from app.integrations.connectors.instagram.exceptions import (
            InstagramPublishError,
        )
        from app.integrations.connectors.instagram.publisher import InstagramPublisher
        from app.integrations.exceptions import IntegrationError
        from app.integrations.secrets.service import secret_service

        if not account.access_token:
            raise IntegrationError(
                f"No access token available for social account {account.id}"
            )

        decrypted_token = secret_service.decrypt_token(account.access_token)

        supported_assets = (
            [
                a
                for a in content.assets
                if a.asset_type in (AssetType.IMAGE, AssetType.VIDEO)
            ]
            if content.assets
            else []
        )

        publisher = InstagramPublisher(page_access_token=decrypted_token)

        if len(supported_assets) >= 2:
            if len(supported_assets) > 10:
                raise IntegrationError(
                    f"Instagram Carousel supports up to 10 assets, but found {len(supported_assets)}."
                )

            carousel_items = []
            for idx, asset in enumerate(supported_assets, start=1):
                if not asset.public_url:
                    raise IntegrationError(
                        f"Asset {asset.id} (item {idx}) missing public_url required for Carousel."
                    )
                carousel_items.append(
                    {
                        "media_type": (
                            "VIDEO" if asset.asset_type == AssetType.VIDEO else "IMAGE"
                        ),
                        "url": asset.public_url,
                    }
                )

            response = await publisher.publish_carousel_post(
                ig_user_id=account.account_id,
                items=carousel_items,
                caption=content.body or "",
            )
        elif len(supported_assets) == 1:
            asset = supported_assets[0]
            if not asset.public_url:
                asset_kind = "video" if asset.asset_type == AssetType.VIDEO else "image"
                raise IntegrationError(
                    f"Campaign content {content.id} {asset_kind} asset missing public_url."
                )

            if asset.asset_type == AssetType.VIDEO:
                is_reel = False
                if content.metadata_ and isinstance(content.metadata_, dict):
                    is_reel = (
                        content.metadata_.get("is_reel") is True
                        or str(content.metadata_.get("post_type")).upper() == "REEL"
                        or str(content.metadata_.get("media_type")).upper() == "REELS"
                    )

                if is_reel:
                    response = await publisher.publish_reels_post(
                        ig_user_id=account.account_id,
                        video_url=asset.public_url,
                        caption=content.body or "",
                    )
                else:
                    response = await publisher.publish_video_post(
                        ig_user_id=account.account_id,
                        video_url=asset.public_url,
                        caption=content.body or "",
                    )
            else:
                response = await publisher.publish_image_post(
                    ig_user_id=account.account_id,
                    image_url=asset.public_url,
                    caption=content.body or "",
                )
        else:
            raise IntegrationError(
                f"Campaign content {content.id} missing IMAGE or VIDEO asset required for Instagram."
            )

        post_id = response.get("id")
        if not post_id:
            raise InstagramPublishError("Meta API did not return a valid post ID.")
        return str(post_id)

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        from app.integrations.connectors.instagram.exceptions import (
            InstagramAuthError,
        )
        from app.integrations.connectors.instagram.sync import InstagramSyncEngine
        from app.integrations.secrets.service import secret_service

        if not access_token:
            raise InstagramAuthError(
                "Access token is required to fetch Instagram account info."
            )

        decrypted_token = secret_service.decrypt_token(access_token)
        sync_engine = InstagramSyncEngine(decrypted_token)

        sync_result = await sync_engine.perform_sync(sync_type="full")
        ig_accounts = sync_result.get("instagram_accounts", [])

        if not ig_accounts:
            raise InstagramAuthError(
                "No linked Instagram Business Account found for the authenticated user."
            )

        primary_account = ig_accounts[0]
        account_id = primary_account.get("id")
        if not account_id:
            raise InstagramAuthError(
                "Instagram account profile response is missing account ID."
            )

        name = (
            primary_account.get("name")
            or primary_account.get("username")
            or "Instagram Account"
        )

        return {
            "account_id": account_id,
            "name": name,
            "username": primary_account.get("username", ""),
            "profile_picture_url": primary_account.get("profile_picture_url", ""),
            "linked_page_id": primary_account.get("linked_page_id"),
            "page_access_token": primary_account.get("page_access_token"),
        }
