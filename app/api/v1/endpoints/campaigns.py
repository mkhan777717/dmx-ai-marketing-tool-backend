import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_user,
    get_current_workspace,
    require_permission,
)
from app.constants.enums import CampaignStatus
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignStatusUpdate,
    CampaignUpdate,
)
from app.schemas.responses import ApiResponse
from app.services.campaign import CampaignService

router = APIRouter()


@router.post(
    "/{workspace_id}/campaigns",
    response_model=ApiResponse[CampaignResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("campaign", "create"))],
)
async def create_campaign(
    workspace_id: uuid.UUID,
    campaign_in: CampaignCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    _=Depends(get_current_workspace),
):
    """
    Create a new campaign within a workspace.
    """
    campaign = await CampaignService.create_campaign(
        db, workspace_id, current_user.id, campaign_in
    )

    await db.commit()

    return ApiResponse(success=True, message="Campaign created", data=campaign)


@router.get(
    "/{workspace_id}/campaigns",
    response_model=ApiResponse[Sequence[CampaignResponse]],
    dependencies=[Depends(require_permission("campaign", "read"))],
)
async def list_campaigns(
    workspace_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    campaign_status: CampaignStatus | None = Query(None, alias="status"),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    List campaigns in a workspace.
    """
    campaigns = await CampaignService.get_campaigns(
        db, workspace_id, skip, limit, campaign_status, search
    )
    return ApiResponse(success=True, message="Campaigns retrieved", data=campaigns)


@router.get(
    "/{workspace_id}/campaigns/{campaign_id}",
    response_model=ApiResponse[CampaignResponse],
    dependencies=[Depends(require_permission("campaign", "read"))],
)
async def get_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Get a specific campaign by ID.
    """
    campaign = await CampaignService.get_campaign(db, workspace_id, campaign_id)
    return ApiResponse(success=True, message="Campaign retrieved", data=campaign)


@router.put(
    "/{workspace_id}/campaigns/{campaign_id}",
    response_model=ApiResponse[CampaignResponse],
    dependencies=[Depends(require_permission("campaign", "update"))],
)
async def update_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    campaign_in: CampaignUpdate,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Update a campaign.
    """
    campaign = await CampaignService.update_campaign(
        db, workspace_id, campaign_id, campaign_in
    )
    return ApiResponse(success=True, message="Campaign updated", data=campaign)


@router.delete(
    "/{workspace_id}/campaigns/{campaign_id}",
    response_model=ApiResponse[CampaignResponse],
    dependencies=[Depends(require_permission("campaign", "delete"))],
)
async def delete_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Soft delete a campaign.
    """
    campaign = await CampaignService.delete_campaign(db, workspace_id, campaign_id)

    await db.commit()

    return ApiResponse(
        success=True,
        message="Campaign deleted",
        data=campaign,
    )


@router.post(
    "/{workspace_id}/campaigns/{campaign_id}/status",
    response_model=ApiResponse[CampaignResponse],
    dependencies=[Depends(require_permission("campaign", "update"))],
)
async def change_campaign_status(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    status_update: CampaignStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    _=Depends(get_current_workspace),
):
    """
    Change the status of a campaign (e.g. publish, pause, archive).
    """
    campaign = await CampaignService.change_status(
        db, workspace_id, campaign_id, status_update
    )
    return ApiResponse(success=True, message="Campaign status changed", data=campaign)
