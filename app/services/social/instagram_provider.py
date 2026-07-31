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
        # Implementation for Instagram Graph API goes here
        raise NotImplementedError("Instagram publishing not yet implemented")

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        # Fetch Instagram account info
        raise NotImplementedError("Instagram OAuth not yet implemented")
