import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import AssetStatus, AssetType, ContentStatus
from app.models.asset import Asset
from app.models.campaign_content import CampaignContent
from app.repositories.campaign import campaign_repo
from app.repositories.campaign_content import campaign_content_repo
from app.schemas.campaign_content import (
    AIContentGenerateRequest,
    AIContentGenerateResponse,
    CampaignContentCreate,
    CampaignContentUpdate,
)
from app.services.ai.factory import AIProviderFactory
from app.services.storage import StorageService


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

        image_url = content_in.image_url
        obj_in = content_in.model_dump(exclude={"image_url"})
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

        content = await campaign_content_repo.create(db, obj_in=obj_in)

        if image_url:
            cleaned_url = image_url.strip()
            filename = cleaned_url.split("/")[-1].split("?")[0] or "image.jpg"
            asset = Asset(
                workspace_id=workspace_id,
                file_name=filename,
                original_file_name=filename,
                display_name=filename,
                asset_type=AssetType.IMAGE,
                mime_type="image/jpeg",
                file_size=0,
                storage_provider="external",
                storage_key=f"external/{uuid.uuid4()}",
                public_url=cleaned_url,
                checksum=str(uuid.uuid4()),
                status=AssetStatus.READY,
            )
            db.add(asset)
            await db.flush()
            content.assets.append(asset)
            db.add(content)
            await db.flush()
            await db.refresh(content, attribute_names=["assets"])

        return content

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

    @staticmethod
    async def get_content(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        content_id: uuid.UUID,
    ) -> CampaignContent:
        content = await campaign_content_repo.get_by_id(db, id=content_id)
        if (
            not content
            or content.workspace_id != workspace_id
            or content.campaign_id != campaign_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Content not found"
            )
        return content

    @staticmethod
    async def update_content(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        content_id: uuid.UUID,
        content_in: CampaignContentUpdate,
    ) -> CampaignContent:
        content = await AIContentService.get_content(
            db, workspace_id, campaign_id, content_id
        )
        image_url = content_in.image_url
        update_data = content_in.model_dump(exclude_unset=True, exclude={"image_url"})
        content = await campaign_content_repo.update(
            db, db_obj=content, obj_in=update_data
        )

        if image_url:
            cleaned_url = image_url.strip()
            filename = cleaned_url.split("/")[-1].split("?")[0] or "image.jpg"
            asset = Asset(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                file_name=filename,
                original_file_name=filename,
                display_name=filename,
                asset_type=AssetType.IMAGE,
                mime_type="image/jpeg",
                file_size=0,
                storage_provider="external",
                storage_key=f"external/{uuid.uuid4()}",
                public_url=cleaned_url,
                checksum=str(uuid.uuid4()),
                status=AssetStatus.READY,
            )
            db.add(asset)
            await db.flush()
            content.assets.clear()
            content.assets.append(asset)
            db.add(content)
            await db.flush()
            await db.refresh(content, attribute_names=["assets"])

        return content

    @staticmethod
    async def delete_content(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        content_id: uuid.UUID,
    ) -> CampaignContent:
        content = await AIContentService.get_content(
            db,
            workspace_id,
            campaign_id,
            content_id,
        )

        deleted = await campaign_content_repo.delete(
            db,
            id=content.id,
            soft=True,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found",
            )

        return content

    @staticmethod
    async def upload_content_image(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        content_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> CampaignContent:
        content = await AIContentService.get_content(
            db, workspace_id, campaign_id, content_id
        )

        upload_result = await StorageService.upload_image(
            file_bytes=file_bytes,
            original_filename=filename,
            mime_type=content_type,
        )

        asset = Asset(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            file_name=filename,
            original_file_name=filename,
            display_name=filename,
            asset_type=AssetType.IMAGE,
            mime_type=upload_result["mime_type"],
            file_size=upload_result["file_size"],
            storage_provider=upload_result["storage_provider"],
            storage_key=upload_result["storage_key"],
            public_url=upload_result["public_url"],
            checksum=upload_result["checksum"],
            status=AssetStatus.READY,
        )
        db.add(asset)
        await db.flush()

        content.assets.clear()
        content.assets.append(asset)
        db.add(content)
        await db.flush()
        await db.refresh(content, attribute_names=["assets"])

        return content
