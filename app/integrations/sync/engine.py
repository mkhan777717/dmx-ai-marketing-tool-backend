import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ApiProvider, JobPriority
from app.integrations.exceptions import OAuthTokenError
from app.integrations.oauth.models import ConnectionStatus
from app.integrations.oauth.repository import integration_connection_repo
from app.integrations.oauth.service import integration_service
from app.integrations.secrets.service import secret_service
from app.jobs.queue import queue_service
from app.repositories.social_account import social_account_repo

logger = logging.getLogger(__name__)


class SyncEngine:
    @staticmethod
    async def trigger_sync(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        provider: str,
        sync_type: str = "full",
    ) -> dict[str, Any]:
        """
        Trigger a sync for a specific provider.
        Instead of executing immediately, this enqueues a background job using our Job Framework.
        """
        provider = provider.lower()
        connection = await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )
        if not connection or connection.status != "CONNECTED":
            raise ValueError(f"No active connection for provider {provider}")

        # Ensure the connector supports syncing
        connector = await integration_service.get_connector_instance(connection)
        capabilities = connector.get_capabilities()
        if not capabilities.can_sync:
            raise ValueError(f"Provider {provider} does not support syncing.")

        payload = {
            "workspace_id": str(workspace_id),
            "provider": provider,
            "sync_type": sync_type,
        }

        job_id = await queue_service.enqueue(
            job_name="integration.sync", payload=payload, priority=JobPriority.HIGH
        )

        return {"status": "sync_enqueued", "job_id": str(job_id)}

    @staticmethod
    async def execute_sync_job(
        db: AsyncSession, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """
        The actual background execution logic called by the Job Worker.
        """
        workspace_id = uuid.UUID(payload["workspace_id"])
        provider = payload["provider"]
        sync_type = payload.get("sync_type", "full")

        connection = await integration_connection_repo.get_by_workspace_and_provider(
            db, workspace_id, provider
        )
        if not connection:
            raise Exception("Connection lost before sync could execute.")

        connector = await integration_service.get_connector_instance(connection)

        # Execute the sync via the connector abstraction
        try:
            sync_result = await connector.sync(sync_type=sync_type)
        except OAuthTokenError as e:
            logger.warning(
                f"Token expired for {provider} workspace {workspace_id}. Marking connection EXPIRED."
            )
            await integration_connection_repo.update(
                db, db_obj=connection, obj_in={"status": ConnectionStatus.EXPIRED}
            )
            raise e

        # Bridge 1: Persist fetched Facebook Pages to SocialAccount
        if provider == "facebook" and "pages" in sync_result:
            for page in sync_result["pages"]:
                page_access_token = page.get("access_token")
                if not page_access_token:
                    logger.warning(
                        f"Facebook page {page.get('id', 'unknown')} missing access token, skipping."
                    )
                    continue

                # 1. Find existing
                existing_accounts = await social_account_repo.get_all(
                    db,
                    filters={
                        "workspace_id": workspace_id,
                        "provider": ApiProvider.META,
                        "account_id": page["id"],
                    },
                )

                encrypted_token = secret_service.encrypt_token(page_access_token)

                if existing_accounts:
                    # 2. Update existing
                    existing = existing_accounts[0]
                    await social_account_repo.update(
                        db,
                        db_obj=existing,
                        obj_in={
                            "name": page["name"],
                            "access_token": encrypted_token,
                            "is_active": True,
                        },
                    )
                else:
                    # 3. Create new
                    await social_account_repo.create(
                        db,
                        obj_in={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.META,
                            "account_id": page["id"],
                            "name": page["name"],
                            "access_token": encrypted_token,
                            "is_active": True,
                        },
                    )

        elif provider == "instagram" and "instagram_accounts" in sync_result:
            for profile in sync_result["instagram_accounts"]:
                page_access_token = profile.get("page_access_token")
                if not page_access_token:
                    logger.warning(
                        f"Instagram account {profile.get('id', 'unknown')} missing page access token, skipping."
                    )
                    continue

                # 1. Find existing
                existing_accounts = await social_account_repo.get_all(
                    db,
                    filters={
                        "workspace_id": workspace_id,
                        "provider": ApiProvider.INSTAGRAM,
                        "account_id": profile["id"],
                    },
                )

                encrypted_token = secret_service.encrypt_token(page_access_token)
                account_name = (
                    profile.get("username") or profile.get("name") or "Unknown"
                )

                if existing_accounts:
                    # 2. Update existing
                    existing = existing_accounts[0]
                    await social_account_repo.update(
                        db,
                        db_obj=existing,
                        obj_in={
                            "name": account_name,
                            "access_token": encrypted_token,
                            "is_active": True,
                        },
                    )
                else:
                    # 3. Create new
                    await social_account_repo.create(
                        db,
                        obj_in={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.INSTAGRAM,
                            "account_id": profile["id"],
                            "name": account_name,
                            "access_token": encrypted_token,
                            "is_active": True,
                        },
                    )

        elif provider == "linkedin" and "profile" in sync_result:
            profile = sync_result["profile"]
            sub = profile.get("sub")
            if not sub:
                logger.warning(
                    "LinkedIn profile missing 'sub', skipping SocialAccount creation."
                )
            else:
                account_id = f"urn:li:person:{sub}"

                if not connection.access_token:
                    logger.warning(
                        f"IntegrationConnection for LinkedIn workspace {workspace_id} missing access token."
                    )
                else:
                    decrypted_token = secret_service.decrypt_token(
                        connection.access_token
                    )
                    encrypted_token = secret_service.encrypt_token(decrypted_token)

                    account_name = (
                        f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}".strip()
                        or "LinkedIn Member"
                    )

                    # 1. Find existing
                    existing_accounts = await social_account_repo.get_all(
                        db,
                        filters={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.LINKEDIN,
                            "account_id": account_id,
                        },
                    )

                    if existing_accounts:
                        # 2. Update existing
                        existing = existing_accounts[0]
                        await social_account_repo.update(
                            db,
                            db_obj=existing,
                            obj_in={
                                "name": account_name,
                                "access_token": encrypted_token,
                                "is_active": True,
                            },
                        )
                    else:
                        # 3. Create new
                        await social_account_repo.create(
                            db,
                            obj_in={
                                "workspace_id": workspace_id,
                                "provider": ApiProvider.LINKEDIN,
                                "account_id": account_id,
                                "name": account_name,
                                "access_token": encrypted_token,
                                "is_active": True,
                            },
                        )

        elif provider == "twitter" and "profile" in sync_result:
            profile = sync_result["profile"]
            account_id = profile.get("id")

            if not account_id:
                logger.warning(
                    "Twitter profile missing 'id', skipping SocialAccount creation."
                )
            else:
                account_id = str(account_id)
                if not connection.access_token:
                    logger.warning(
                        f"IntegrationConnection for Twitter workspace {workspace_id} missing access token."
                    )
                else:
                    decrypted_token = secret_service.decrypt_token(
                        connection.access_token
                    )
                    encrypted_token = secret_service.encrypt_token(decrypted_token)

                    encrypted_refresh_token = None
                    if connection.refresh_token:
                        decrypted_rt = secret_service.decrypt_token(
                            connection.refresh_token
                        )
                        encrypted_refresh_token = secret_service.encrypt_token(
                            decrypted_rt
                        )

                    account_name = (
                        profile.get("username") or profile.get("name") or "X Member"
                    )

                    # 1. Find existing
                    existing_accounts = await social_account_repo.get_all(
                        db,
                        filters={
                            "workspace_id": workspace_id,
                            "provider": ApiProvider.TWITTER,
                            "account_id": account_id,
                        },
                    )

                    if existing_accounts:
                        # 2. Update existing
                        existing = existing_accounts[0]
                        await social_account_repo.update(
                            db,
                            db_obj=existing,
                            obj_in={
                                "name": account_name,
                                "access_token": encrypted_token,
                                "refresh_token": encrypted_refresh_token,
                                "expires_at": connection.expires_at,
                                "is_active": True,
                            },
                        )
                    else:
                        # 3. Create new
                        await social_account_repo.create(
                            db,
                            obj_in={
                                "workspace_id": workspace_id,
                                "provider": ApiProvider.TWITTER,
                                "account_id": account_id,
                                "name": account_name,
                                "access_token": encrypted_token,
                                "refresh_token": encrypted_refresh_token,
                                "expires_at": connection.expires_at,
                                "is_active": True,
                            },
                        )

        elif provider == "google" and "business_accounts" in sync_result:
            business_accounts = sync_result["business_accounts"]
            if not business_accounts:
                logger.warning(
                    f"No Google business accounts found for workspace {workspace_id}."
                )

            if not connection.access_token:
                logger.warning(
                    f"IntegrationConnection for Google workspace {workspace_id} missing access token."
                )
            else:
                decrypted_token = secret_service.decrypt_token(connection.access_token)
                encrypted_token = secret_service.encrypt_token(decrypted_token)

                encrypted_refresh_token = None
                if connection.refresh_token:
                    decrypted_rt = secret_service.decrypt_token(
                        connection.refresh_token
                    )
                    encrypted_refresh_token = secret_service.encrypt_token(decrypted_rt)

                for account_data in business_accounts:
                    locations = account_data.get("locations", [])
                    for location in locations:
                        location_id = location.get("location_id")
                        location_name_str = (
                            location.get("location_name") or "GBP Location"
                        )

                        if not location_id:
                            logger.warning(
                                "Google location missing location_id, skipping."
                            )
                            continue

                        # We use the location resource name (e.g. accounts/123/locations/456) as the unique account_id
                        account_id_str = f"accounts/{account_data['account_id']}/locations/{location_id}"

                        # 1. Find existing
                        existing_accounts = await social_account_repo.get_all(
                            db,
                            filters={
                                "workspace_id": workspace_id,
                                "provider": ApiProvider.GOOGLE,
                                "account_id": account_id_str,
                            },
                        )

                        if existing_accounts:
                            # 2. Update existing
                            existing = existing_accounts[0]
                            await social_account_repo.update(
                                db,
                                db_obj=existing,
                                obj_in={
                                    "name": location_name_str,
                                    "access_token": encrypted_token,
                                    "refresh_token": encrypted_refresh_token,
                                    "expires_at": connection.expires_at,
                                    "is_active": True,
                                },
                            )
                        else:
                            # 3. Create new
                            await social_account_repo.create(
                                db,
                                obj_in={
                                    "workspace_id": workspace_id,
                                    "provider": ApiProvider.GOOGLE,
                                    "account_id": account_id_str,
                                    "name": location_name_str,
                                    "access_token": encrypted_token,
                                    "refresh_token": encrypted_refresh_token,
                                    "expires_at": connection.expires_at,
                                    "is_active": True,
                                },
                            )

        return sync_result


sync_engine = SyncEngine()
