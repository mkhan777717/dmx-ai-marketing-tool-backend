import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.social_account import SocialAccount
from app.repositories.social_account import social_account_repo
from app.schemas.social_account import SocialAccountConnectRequest
from app.services.social.factory import SocialProviderFactory


class SocialAccountService:
    @staticmethod
    async def connect_account(
        db: AsyncSession, workspace_id: uuid.UUID, request: SocialAccountConnectRequest
    ) -> SocialAccount:
        """
        Connect a new social account via OAuth.
        """
        provider_impl = SocialProviderFactory.get_provider(request.provider)

        # In a real scenario, this would exchange `request.oauth_code` for an access token
        # using the provider's OAuth 2.0 endpoints.
        # For now, we simulate this with the provider implementation or mock.

        # We would typically call:
        # token_data = await provider_impl.exchange_code(request.oauth_code)
        # account_info = await provider_impl.get_account_info(token_data.access_token)

        # Simulating OAuth flow with mock
        account_info = await provider_impl.get_account_info("mock_token")

        obj_in = {
            "workspace_id": workspace_id,
            "provider": request.provider,
            "account_id": account_info.get(
                "account_id", f"mock_acc_{uuid.uuid4().hex[:8]}"
            ),
            "name": account_info.get("name", "Mock Account"),
            "access_token": "mock_access_token_value",
            "refresh_token": "mock_refresh_token_value",
            "is_active": True,
        }

        return await social_account_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_accounts(
        db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[SocialAccount]:
        return await social_account_repo.get_by_workspace_id(
            db, workspace_id, skip, limit
        )
