from typing import Any

from app.constants.enums import ApiProvider
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider


class FacebookProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.META.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        from app.constants.enums import AssetType
        from app.integrations.connectors.facebook.exceptions import FacebookPublishError
        from app.integrations.connectors.facebook.publisher import FacebookPublisher
        from app.integrations.exceptions import IntegrationError
        from app.integrations.secrets.service import secret_service

        if not account.access_token:
            raise IntegrationError(
                f"No access token available for social account {account.id}"
            )

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = FacebookPublisher(access_token=decrypted_token)

        assets = content.assets if content.assets else []

        # Route based on assets
        if len(assets) == 0:
            if not content.body or not content.body.strip():
                raise IntegrationError(
                    f"Campaign content {content.id} body is empty, and no assets provided."
                )
            response = await publisher.publish_text_post(
                page_id=account.account_id, message=content.body
            )
        elif len(assets) == 1:
            asset = assets[0]
            if not asset.public_url:
                raise IntegrationError(f"Asset {asset.id} missing public_url")

            if asset.asset_type == AssetType.IMAGE:
                response = await publisher.publish_image_post(
                    page_id=account.account_id,
                    message=content.body or "",
                    image_url=asset.public_url,
                )
            elif asset.asset_type == AssetType.VIDEO:
                response = await publisher.publish_video_post(
                    page_id=account.account_id,
                    title=content.title or "",
                    description=content.body or "",
                    file_url=asset.public_url,
                )
            else:
                raise IntegrationError(
                    f"Unsupported asset type for Facebook: {asset.asset_type}"
                )
        else:
            raise IntegrationError(
                f"Facebook currently only supports up to 1 asset for MVP, found {len(assets)}"
            )

        post_id = response.get("id")
        if not post_id:
            raise FacebookPublishError("Meta API did not return a valid post ID.")

        return str(post_id)

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        # Fetch Facebook page info
        raise NotImplementedError("Facebook OAuth not yet implemented")
