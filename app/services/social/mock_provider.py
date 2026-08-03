import asyncio
import uuid
from typing import Any

from app.constants.enums import ApiProvider
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider


class MockSocialProvider(BaseSocialProvider):
    """
    Mock Social Provider used for testing and local development.
    Simulates network latency and successful publish events.
    """

    @property
    def provider_name(self) -> str:
        return ApiProvider.MOCK.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        # Simulate network delay
        await asyncio.sleep(0.5)

        # Simulate an external post ID
        external_post_id = f"mock_post_{uuid.uuid4().hex[:8]}"
        return external_post_id

    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        return {
            "account_id": f"mock_acc_{uuid.uuid4().hex[:8]}",
            "name": "Mock Social Page",
        }
