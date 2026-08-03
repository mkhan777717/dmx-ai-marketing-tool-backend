from abc import ABC, abstractmethod
from typing import Any

from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount


class BaseSocialProvider(ABC):
    """
    Abstract base class for all Social Providers (Facebook, LinkedIn, etc.)
    Ensures decoupled business logic from external SDKs.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the social provider."""
        pass

    @abstractmethod
    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        """
        Publishes content to the social media platform.
        Must return the external_post_id on success, or raise an exception on failure.
        """
        pass

    @abstractmethod
    async def get_account_info(self, access_token: str) -> dict[str, Any]:
        """
        Fetches account profile information during the OAuth connection process.
        """
        pass
