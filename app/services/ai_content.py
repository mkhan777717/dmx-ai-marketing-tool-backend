import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ContentStatus
from app.models.campaign_content import CampaignContent
from app.repositories.campaign import campaign_repo
from app.repositories.campaign_content import campaign_content_repo
from app.schemas.campaign_content import (
    AIContentGenerateRequest,
    AIContentGenerateResponse,
    CampaignContentCreate,
)
from app.services.ai.factory import AIProviderFactory


class AIContentService:
    @staticmethod
    async def generate_content(
        workspace_id: uuid.UUID, request: AIContentGenerateRequest
    ) -> AIContentGenerateResponse:
        """
        Generate raw AI content using the specified provider.
        Does not save to DB.
        """
        provider = AIProviderFactory.get_provider(request.provider)

        # We can pass additional kwargs down to the provider here if needed
        # e.g., fetching BrandKit details to enrich the prompt

        response = await provider.generate_content(request=request)
        return response

    @staticmethod
    async def create_campaign_content(
        db: AsyncSession, workspace_id: uuid.UUID, content_in: CampaignContentCreate
    ) -> CampaignContent:
        """
        Save content to a campaign.
        """
        # Validate campaign exists and belongs to workspace
        campaign = await campaign_repo.get_by_id(db, id=content_in.campaign_id)
        if not campaign or campaign.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )

        # Check for existing latest version to increment version number if needed
        latest = await campaign_content_repo.get_latest_version(
            db,
            campaign_id=content_in.campaign_id,
            content_type=content_in.content_type,
            language=content_in.language or "en",
        )

        obj_in = content_in.model_dump()
        obj_in["workspace_id"] = workspace_id
        obj_in["status"] = ContentStatus.DRAFT

        if latest:
            # We are creating a new version of existing content
            obj_in["version"] = latest.version + 1
            obj_in["parent_version_id"] = latest.id

            # Mark the old one as not current
            await campaign_content_repo.update(
                db, db_obj=latest, obj_in={"is_current": False}
            )
        else:
            obj_in["version"] = 1
            obj_in["is_current"] = True

        return await campaign_content_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_campaign_contents(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CampaignContent]:
        # Validate campaign
        campaign = await campaign_repo.get_by_id(db, id=campaign_id)
        if not campaign or campaign.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
        return await campaign_content_repo.get_by_campaign_id(
            db, campaign_id, skip, limit
        )
