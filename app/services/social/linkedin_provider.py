from typing import Any

from app.constants.enums import ApiProvider
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider


class LinkedInProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.LINKEDIN.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        # Implementation for LinkedIn REST API goes here
        raise NotImplementedError("LinkedIn publishing not yet implemented")

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        # Fetch LinkedIn organization/profile info
        raise NotImplementedError("LinkedIn OAuth not yet implemented")
