import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import CampaignStatus
from app.models.brand_kit import BrandKit
from app.models.campaign import Campaign
from app.repositories.campaign import campaign_repo
from app.schemas.campaign import (CampaignCreate, CampaignStatusUpdate,
                                  CampaignUpdate)


class CampaignService:
    @staticmethod
    async def create_campaign(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        owner_id: uuid.UUID,
        campaign_in: CampaignCreate,
    ) -> Campaign:
        # Validate dates
        if campaign_in.start_date and campaign_in.end_date:
            if campaign_in.end_date <= campaign_in.start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End date must be after start date",
                )

        # Validate brand kit if provided
        if campaign_in.brand_kit_id:
            brand_kit_stmt = select(BrandKit).where(
                BrandKit.id == campaign_in.brand_kit_id,
                BrandKit.workspace_id == workspace_id,
            )
            result = await db.execute(brand_kit_stmt)
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Brand kit not found in this workspace",
                )

        obj_in = campaign_in.model_dump()
        obj_in["workspace_id"] = workspace_id
        obj_in["owner_id"] = owner_id
        obj_in["status"] = CampaignStatus.DRAFT

        return await campaign_repo.create(db, obj_in=obj_in)

    @staticmethod
    async def get_campaign(
        db: AsyncSession, workspace_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> Campaign:
        campaign = await campaign_repo.get_by_id(db, id=campaign_id)
        if not campaign or campaign.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
        return campaign

    @staticmethod
    async def get_campaigns(
        db: AsyncSession, workspace_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> Sequence[Campaign]:
        return await campaign_repo.get_by_workspace_id(db, workspace_id, skip, limit)

    @staticmethod
    async def update_campaign(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        campaign_in: CampaignUpdate,
    ) -> Campaign:
        campaign = await CampaignService.get_campaign(db, workspace_id, campaign_id)

        # Validate dates
        new_start = (
            campaign_in.start_date
            if campaign_in.start_date is not None
            else campaign.start_date
        )
        new_end = (
            campaign_in.end_date
            if campaign_in.end_date is not None
            else campaign.end_date
        )
        if new_start and new_end and new_end <= new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date",
            )

        # Validate brand kit
        if (
            campaign_in.brand_kit_id
            and campaign_in.brand_kit_id != campaign.brand_kit_id
        ):
            brand_kit_stmt = select(BrandKit).where(
                BrandKit.id == campaign_in.brand_kit_id,
                BrandKit.workspace_id == workspace_id,
            )
            result = await db.execute(brand_kit_stmt)
            if not result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Brand kit not found in this workspace",
                )

        update_data = campaign_in.model_dump(exclude_unset=True)
        return await campaign_repo.update(db, db_obj=campaign, obj_in=update_data)

    @staticmethod
    async def delete_campaign(
        db: AsyncSession, workspace_id: uuid.UUID, campaign_id: uuid.UUID
    ) -> Campaign:
        campaign = await CampaignService.get_campaign(db, workspace_id, campaign_id)
        return await campaign_repo.remove(db, id=campaign.id)

    @staticmethod
    async def change_status(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        campaign_id: uuid.UUID,
        status_in: CampaignStatusUpdate,
    ) -> Campaign:
        campaign = await CampaignService.get_campaign(db, workspace_id, campaign_id)

        # Valid state transitions
        current_status = campaign.status
        new_status = status_in.status

        # If already at the status, do nothing
        if current_status == new_status:
            return campaign

        # Define valid transitions
        # DRAFT -> ACTIVE, ARCHIVED
        # ACTIVE -> PAUSED, COMPLETED, ARCHIVED
        # PAUSED -> ACTIVE, COMPLETED, ARCHIVED
        # COMPLETED -> ARCHIVED
        valid_transitions = {
            CampaignStatus.DRAFT: [CampaignStatus.ACTIVE, CampaignStatus.ARCHIVED],
            CampaignStatus.ACTIVE: [
                CampaignStatus.PAUSED,
                CampaignStatus.COMPLETED,
                CampaignStatus.ARCHIVED,
            ],
            CampaignStatus.PAUSED: [
                CampaignStatus.ACTIVE,
                CampaignStatus.COMPLETED,
                CampaignStatus.ARCHIVED,
            ],
            CampaignStatus.COMPLETED: [CampaignStatus.ARCHIVED],
            CampaignStatus.ARCHIVED: [],
        }

        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition campaign from {current_status.value} to {new_status.value}",
            )

        return await campaign_repo.update(
            db, db_obj=campaign, obj_in={"status": new_status}
        )
