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
        accounts = await social_account_repo.get_by_workspace_id(
            db, workspace_id, skip, limit
        )
        if accounts:
            return accounts

        # Self-healing backfill pass for active connections created prior to inline persistence
        from app.constants.enums import ApiProvider
        from app.integrations.oauth.repository import integration_connection_repo

        connections = await integration_connection_repo.get_active_connections(
            db, workspace_id
        )
        healed = False
        for conn in connections:
            if (
                conn.provider == "linkedin"
                and conn.metadata_info
                and conn.metadata_info.get("author_urn")
            ):
                author_urn = conn.metadata_info["author_urn"]
                profile_name = (
                    conn.metadata_info.get("profile_name") or "LinkedIn Member"
                )
                existing = await social_account_repo.get_all(
                    db,
                    filters={
                        "workspace_id": workspace_id,
                        "provider": ApiProvider.LINKEDIN,
                        "account_id": author_urn,
                    },
                )
                if not existing:
                    await social_account_repo.create(
                        db,
                        obj_in={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.LINKEDIN,
                            "account_id": author_urn,
                            "name": profile_name,
                            "access_token": conn.access_token or "",
                            "refresh_token": conn.refresh_token,
                            "expires_at": conn.expires_at,
                            "is_active": True,
                        },
                    )
                    healed = True

        if healed:
            await db.commit()
            return await social_account_repo.get_by_workspace_id(
                db, workspace_id, skip, limit
            )

        return accounts
