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

        image_asset = next(
            (a for a in content.assets if a.asset_type == AssetType.IMAGE), None
        )
        if not image_asset:
            raise IntegrationError(
                f"Campaign content {content.id} missing IMAGE asset required for Instagram."
            )
        if not image_asset.public_url:
            raise IntegrationError(
                f"Campaign content {content.id} image asset missing public_url."
            )

        publisher = InstagramPublisher(page_access_token=decrypted_token)
        response = await publisher.publish_image_post(
            ig_user_id=account.account_id,
            image_url=image_asset.public_url,
            caption=content.body or "",
        )

        post_id = response.get("id")
        if not post_id:
            raise InstagramPublishError("Meta API did not return a valid post ID.")
        return str(post_id)

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        # Fetch Instagram account info
        raise NotImplementedError("Instagram OAuth not yet implemented")
