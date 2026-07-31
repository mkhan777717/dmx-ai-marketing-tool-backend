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
        # Implementation for Facebook Graph API goes here
        raise NotImplementedError("Facebook publishing not yet implemented")

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        # Fetch Facebook page info
        raise NotImplementedError("Facebook OAuth not yet implemented")
