import uuid
import json
from typing import Any
from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.asset import AssetUpdate, AssetResponse
from app.schemas.responses import ApiResponse
from app.services.asset import asset_service
from app.repositories.asset import asset_repo
from app.api.dependencies.auth import get_current_user, get_current_workspace, require_permission
from app.constants.enums import AssetStatus, AssetType

router = APIRouter()

@router.post("/workspaces/{workspace_id}/assets/upload", response_model=ApiResponse[AssetResponse], status_code=status.HTTP_201_CREATED)
async def upload_asset(
    workspace_id: uuid.UUID,
    file: UploadFile = File(...),
    folder: str = Form("/"),
    tags_str: str | None = Form(None, alias="tags"),
    description: str | None = Form(None),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "create"))
) -> Any:
    tags = []
    if tags_str:
        try:
            tags = json.loads(tags_str)
        except:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            
    asset = await asset_service.upload_asset(
        db=db,
        user=user,
        workspace=workspace,
        file=file,
        folder=folder,
        tags=tags,
        description=description
    )
    await db.commit()
    await db.refresh(asset)
    return ApiResponse(success=True, message="Asset uploaded successfully", data=AssetResponse.model_validate(asset))

@router.get("/workspaces/{workspace_id}/assets", response_model=ApiResponse[list[AssetResponse]])
async def list_assets(
    workspace_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "read"))
) -> Any:
    assets = await asset_repo.list_assets(db, workspace.id, limit=limit, offset=offset)
    return ApiResponse(success=True, message="Assets retrieved successfully", data=[AssetResponse.model_validate(a) for a in assets])

@router.get("/workspaces/{workspace_id}/assets/search", response_model=ApiResponse[list[AssetResponse]])
async def search_assets(
    workspace_id: uuid.UUID,
    asset_type: AssetType | None = None,
    folder: str | None = None,
    uploader_id: uuid.UUID | None = None,
    asset_status: AssetStatus | None = None,
    q: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "read"))
) -> Any:
    assets = await asset_repo.search_assets(
        db=db,
        workspace_id=workspace.id,
        asset_type=asset_type,
        folder=folder,
        uploader_id=uploader_id,
        status=asset_status,
        filename_query=q,
        limit=limit,
        offset=offset
    )
    return ApiResponse(success=True, message="Assets found successfully", data=[AssetResponse.model_validate(a) for a in assets])

@router.get("/workspaces/{workspace_id}/assets/{asset_id}", response_model=ApiResponse[AssetResponse])
async def get_asset(
    workspace_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "read"))
) -> Any:
    asset = await asset_repo.get_asset(db, workspace.id, asset_id)
    if not asset:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Asset not found")
    return ApiResponse(success=True, message="Asset retrieved successfully", data=AssetResponse.model_validate(asset))

@router.patch("/workspaces/{workspace_id}/assets/{asset_id}", response_model=ApiResponse[AssetResponse])
async def update_asset(
    workspace_id: uuid.UUID,
    asset_id: uuid.UUID,
    data: AssetUpdate,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "update"))
) -> Any:
    asset = await asset_service.update_asset(db, user, workspace, asset_id, data)
    await db.commit()
    await db.refresh(asset)
    return ApiResponse(success=True, message="Asset updated successfully", data=AssetResponse.model_validate(asset))

@router.delete("/workspaces/{workspace_id}/assets/{asset_id}", response_model=ApiResponse[None])
async def delete_asset(
    workspace_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "delete"))
) -> Any:
    await asset_service.delete_asset(db, user, workspace, asset_id)
    await db.commit()
    return ApiResponse(success=True, message="Asset deleted successfully", data=None)

@router.post("/workspaces/{workspace_id}/assets/{asset_id}/restore", response_model=ApiResponse[AssetResponse])
async def restore_asset(
    workspace_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("asset", "update"))
) -> Any:
    asset = await asset_service.restore_asset(db, user, workspace, asset_id)
    await db.commit()
    await db.refresh(asset)
    return ApiResponse(success=True, message="Asset restored successfully", data=AssetResponse.model_validate(asset))
