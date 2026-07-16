import uuid
from typing import Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.campaign import CampaignCreateRequest, CampaignCreate, CampaignUpdate, CampaignResponse
from app.schemas.responses import ApiResponse
from app.services.campaign import campaign_service
from app.repositories.campaign import campaign_repo
from app.api.dependencies.auth import get_current_user, get_current_workspace, require_permission

router = APIRouter()

@router.post("/workspaces/{workspace_id}/campaigns", response_model=ApiResponse[CampaignResponse], status_code=status.HTTP_201_CREATED)
async def create_campaign(
    workspace_id: uuid.UUID,
    data: CampaignCreateRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "create"))
) -> Any:
    create_data = CampaignCreate(**data.model_dump(), workspace_id=workspace.id, owner_id=user.id)
    campaign = await campaign_service.create_campaign(db, user, workspace, create_data)
    await db.commit()
    await db.refresh(campaign)
    return ApiResponse(success=True, message="Campaign created successfully", data=CampaignResponse.model_validate(campaign))

@router.get("/workspaces/{workspace_id}/campaigns", response_model=ApiResponse[list[CampaignResponse]])
async def list_campaigns(
    workspace_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "read"))
) -> Any:
    campaigns = await campaign_repo.get_by_workspace(db, workspace.id, limit=limit, offset=offset)
    return ApiResponse(success=True, message="Campaigns retrieved successfully", data=[CampaignResponse.model_validate(c) for c in campaigns])

@router.get("/workspaces/{workspace_id}/campaigns/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def get_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "read"))
) -> Any:
    campaign = await campaign_repo.get_by_id_and_workspace(db, workspace.id, campaign_id)
    if not campaign:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign not found")
    return ApiResponse(success=True, message="Campaign retrieved successfully", data=CampaignResponse.model_validate(campaign))

@router.patch("/workspaces/{workspace_id}/campaigns/{campaign_id}", response_model=ApiResponse[CampaignResponse])
async def update_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: CampaignUpdate,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "update"))
) -> Any:
    campaign = await campaign_service.update_campaign(db, user, workspace, campaign_id, data)
    await db.commit()
    await db.refresh(campaign)
    return ApiResponse(success=True, message="Campaign updated successfully", data=CampaignResponse.model_validate(campaign))

@router.delete("/workspaces/{workspace_id}/campaigns/{campaign_id}", response_model=ApiResponse[None])
async def delete_campaign(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "delete"))
) -> Any:
    await campaign_service.delete_campaign(db, user, workspace, campaign_id)
    await db.commit()
    return ApiResponse(success=True, message="Campaign deleted successfully", data=None)

@router.post("/workspaces/{workspace_id}/campaigns/{campaign_id}/assets/{asset_id}", response_model=ApiResponse[CampaignResponse])
async def attach_asset(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "update"))
) -> Any:
    campaign = await campaign_service.attach_asset(db, user, workspace, campaign_id, asset_id)
    await db.commit()
    await db.refresh(campaign)
    return ApiResponse(success=True, message="Asset attached to campaign", data=CampaignResponse.model_validate(campaign))

@router.delete("/workspaces/{workspace_id}/campaigns/{campaign_id}/assets/{asset_id}", response_model=ApiResponse[CampaignResponse])
async def detach_asset(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign", "update"))
) -> Any:
    campaign = await campaign_service.detach_asset(db, user, workspace, campaign_id, asset_id)
    await db.commit()
    await db.refresh(campaign)
    return ApiResponse(success=True, message="Asset detached from campaign", data=CampaignResponse.model_validate(campaign))
