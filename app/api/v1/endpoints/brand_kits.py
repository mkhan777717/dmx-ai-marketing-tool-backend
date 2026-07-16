import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.brand_kit import BrandKitCreateRequest, BrandKitCreate, BrandKitUpdate, BrandKitResponse
from app.schemas.responses import ApiResponse
from app.services.brand_kit import brand_kit_service
from app.api.dependencies.auth import get_current_user, get_current_workspace, require_permission

router = APIRouter()

@router.post("/workspaces/{workspace_id}/brand-kit", response_model=ApiResponse[BrandKitResponse], status_code=status.HTTP_201_CREATED)
async def create_brand_kit(
    workspace_id: uuid.UUID,
    data: BrandKitCreateRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("brand_kit", "create"))
) -> Any:
    # Build internal creation schema
    create_data = BrandKitCreate(**data.model_dump(), workspace_id=workspace.id)
    kit = await brand_kit_service.create_brand_kit(db, user, workspace, create_data)
    await db.commit()
    await db.refresh(kit)
    return ApiResponse(success=True, message="Brand Kit created successfully", data=BrandKitResponse.model_validate(kit))

@router.get("/workspaces/{workspace_id}/brand-kit", response_model=ApiResponse[BrandKitResponse])
async def get_brand_kit(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("brand_kit", "read"))
) -> Any:
    kit = await brand_kit_service.get_brand_kit(db, workspace.id)
    return ApiResponse(success=True, message="Brand Kit retrieved successfully", data=BrandKitResponse.model_validate(kit))

@router.patch("/workspaces/{workspace_id}/brand-kit", response_model=ApiResponse[BrandKitResponse])
async def update_brand_kit(
    workspace_id: uuid.UUID,
    data: BrandKitUpdate,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("brand_kit", "update"))
) -> Any:
    kit = await brand_kit_service.update_brand_kit(db, user, workspace, data)
    await db.commit()
    await db.refresh(kit)
    return ApiResponse(success=True, message="Brand Kit updated successfully", data=BrandKitResponse.model_validate(kit))

@router.delete("/workspaces/{workspace_id}/brand-kit", response_model=ApiResponse[None])
async def delete_brand_kit(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("brand_kit", "delete"))
) -> Any:
    await brand_kit_service.delete_brand_kit(db, user, workspace)
    await db.commit()
    return ApiResponse(success=True, message="Brand Kit deleted successfully", data=None)
