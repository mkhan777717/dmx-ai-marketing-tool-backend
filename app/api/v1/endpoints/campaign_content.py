import uuid
from typing import Any
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.campaign_content import CampaignContentCreateRequest, CampaignContentCreate, CampaignContentUpdate, CampaignContentResponse
from app.schemas.responses import ApiResponse
from app.services.campaign_content import campaign_content_service, campaign_version_service
from app.repositories.campaign_content import campaign_content_repo
from app.api.dependencies.auth import get_current_user, get_current_workspace, require_permission

router = APIRouter()

@router.post("/workspaces/{workspace_id}/campaigns/{campaign_id}/content", response_model=ApiResponse[CampaignContentResponse], status_code=status.HTTP_201_CREATED)
async def create_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    data: CampaignContentCreateRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "create"))
) -> Any:
    create_data = CampaignContentCreate(**data.model_dump(), campaign_id=campaign_id, workspace_id=workspace.id, created_by=user.id)
    content = await campaign_content_service.create_content(db, user, workspace, create_data)
    await db.commit()
    await db.refresh(content)
    return ApiResponse(success=True, message="Campaign content created successfully", data=CampaignContentResponse.model_validate(content))

@router.get("/workspaces/{workspace_id}/campaigns/{campaign_id}/content", response_model=ApiResponse[list[CampaignContentResponse]])
async def list_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "read"))
) -> Any:
    contents = await campaign_content_repo.list_by_campaign(db, workspace.id, campaign_id, limit=limit, offset=offset)
    return ApiResponse(success=True, message="Campaign contents retrieved successfully", data=[CampaignContentResponse.model_validate(c) for c in contents])

@router.get("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}", response_model=ApiResponse[CampaignContentResponse])
async def get_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "read"))
) -> Any:
    content = await campaign_content_repo.get_current_version(db, workspace.id, campaign_id, content_id)
    if not content:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Campaign content not found")
    return ApiResponse(success=True, message="Campaign content retrieved successfully", data=CampaignContentResponse.model_validate(content))

@router.patch("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}", response_model=ApiResponse[CampaignContentResponse])
async def update_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    data: CampaignContentUpdate,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "update"))
) -> Any:
    content = await campaign_content_service.update_content(db, user, workspace, campaign_id, content_id, data)
    await db.commit()
    await db.refresh(content)
    return ApiResponse(success=True, message="Campaign content updated successfully", data=CampaignContentResponse.model_validate(content))

@router.delete("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}", response_model=ApiResponse[None])
async def delete_content(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "delete"))
) -> Any:
    await campaign_content_service.delete_content(db, user, workspace, campaign_id, content_id)
    await db.commit()
    return ApiResponse(success=True, message="Campaign content deleted successfully", data=None)

@router.post("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}/version", response_model=ApiResponse[CampaignContentResponse])
async def create_version(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "update"))
) -> Any:
    new_version = await campaign_version_service.create_version(db, user, workspace, campaign_id, content_id)
    await db.commit()
    await db.refresh(new_version)
    return ApiResponse(success=True, message="New version created successfully", data=CampaignContentResponse.model_validate(new_version))

@router.get("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}/versions", response_model=ApiResponse[list[CampaignContentResponse]])
async def list_versions(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "read"))
) -> Any:
    versions = await campaign_content_repo.list_versions(db, workspace.id, content_id)
    return ApiResponse(success=True, message="Versions retrieved successfully", data=[CampaignContentResponse.model_validate(v) for v in versions])

@router.post("/workspaces/{workspace_id}/campaigns/{campaign_id}/content/{content_id}/restore", response_model=ApiResponse[CampaignContentResponse])
async def restore_version(
    workspace_id: uuid.UUID,
    campaign_id: uuid.UUID,
    content_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("campaign_content", "update"))
) -> Any:
    restored = await campaign_version_service.restore_version(db, user, workspace, campaign_id, content_id)
    await db.commit()
    await db.refresh(restored)
    return ApiResponse(success=True, message="Version restored successfully", data=CampaignContentResponse.model_validate(restored))
