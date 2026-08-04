import uuid
from datetime import datetime, timezone
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import PublishStatus
from app.models.publish_history import PublishHistory
from app.repositories.campaign_content import campaign_content_repo
from app.repositories.publish_history import publish_history_repo
from app.repositories.social_account import social_account_repo
from app.schemas.publishing import PublishRequest
from app.services.social.factory import SocialProviderFactory


class PublishingService:
    @staticmethod
    async def publish_content(
        db: AsyncSession, workspace_id: uuid.UUID, request: PublishRequest
    ) -> PublishHistory:
        """
        Publishes content to a social account.
        This function is designed to be easily invoked by a background Celery worker.
        """

        # 1. Fetch relations and validate
        content = await campaign_content_repo.get_by_id(db, id=request.content_id)
        if not content or content.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Content not found")

        account = await social_account_repo.get_by_id(db, id=request.social_account_id)
        if not account or account.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Social account not found")

        # 2. Create PENDING history record
        history_obj = {
            "workspace_id": workspace_id,
            "campaign_id": content.campaign_id,
            "content_id": content.id,
            "social_account_id": account.id,
            "status": PublishStatus.PENDING,
        }
        history_record = await publish_history_repo.create(db, obj_in=history_obj)

        # 3. Get provider and execute publish
        provider_impl = SocialProviderFactory.get_provider(account.provider)

        try:
            external_id = await provider_impl.publish_content(account, content)

            # 4a. Success update
            update_data = {
                "status": PublishStatus.PUBLISHED,
                "external_post_id": external_id,
                "published_at": datetime.now(timezone.utc),
            }
        except Exception as e:
            # 4b. Failure update
            update_data = {"status": PublishStatus.FAILED, "error_message": str(e)}

        # Commit the result to DB
        return await publish_history_repo.update(
            db, db_obj=history_record, obj_in=update_data
        )

    @staticmethod
    async def get_publish_history(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        campaign_id: uuid.UUID | None = None,
        content_id: uuid.UUID | None = None,
        status: str | None = None,
        social_account_id: uuid.UUID | None = None,
    ) -> Sequence[PublishHistory]:
        return await publish_history_repo.get_by_workspace_id(
            db,
            workspace_id,
            skip,
            limit,
            campaign_id,
            content_id,
            status,
            social_account_id,
        )
