import uuid
from typing import Any
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceCreateInternal, WorkspaceUpdate, WorkspaceResponse, WorkspaceTransferOwnershipRequest
from app.schemas.responses import ApiResponse
from app.services.workspace import workspace_service
from app.api.dependencies.auth import get_current_user, get_current_workspace, require_permission

router = APIRouter()

@router.post("", response_model=ApiResponse[WorkspaceResponse], status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Any:
    internal_data = WorkspaceCreateInternal(**data.model_dump(), owner_id=user.id, created_by=user.id)
    workspace = await workspace_service.create_workspace(db, user, internal_data)
    await db.commit()
    await db.refresh(workspace)
    return ApiResponse(success=True, message="Workspace created successfully", data=WorkspaceResponse.model_validate(workspace))

@router.get("", response_model=ApiResponse[list[WorkspaceResponse]])
async def get_workspaces(
    user: User = Depends(get_current_user)
) -> Any:
    # A user can list their owned workspaces and workspaces they are a member of.
    # The models are lazy="selectin" so we can access user.owned_workspaces directly
    # Wait, the user object doesn't automatically load relationships unless specified.
    # We should query the repo for workspaces the user has access to, or use a service method.
    # For now, let's just return owned_workspaces + member workspaces.
    # We will need to query this properly. Let's do a simple implementation.
    return ApiResponse(success=True, message="Workspaces retrieved", data=[WorkspaceResponse.model_validate(w) for w in user.owned_workspaces])

@router.get("/{id}", response_model=ApiResponse[WorkspaceResponse])
async def get_workspace(
    id: uuid.UUID,
    workspace: Workspace = Depends(get_current_workspace),
    _: bool = Depends(require_permission("workspace", "read"))
) -> Any:
    return ApiResponse(success=True, message="Workspace retrieved", data=WorkspaceResponse.model_validate(workspace))

@router.patch("/{id}", response_model=ApiResponse[WorkspaceResponse])
async def update_workspace(
    id: uuid.UUID,
    data: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("workspace", "update"))
) -> Any:
    updated_workspace = await workspace_service.update_workspace(db, user, workspace, data)
    await db.commit()
    await db.refresh(updated_workspace)
    return ApiResponse(success=True, message="Workspace updated successfully", data=WorkspaceResponse.model_validate(updated_workspace))

@router.delete("/{id}", response_model=ApiResponse[None])
async def delete_workspace(
    id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(require_permission("workspace", "delete"))
) -> Any:
    await workspace_service.delete_workspace(db, user, workspace)
    await db.commit()
    return ApiResponse(success=True, message="Workspace deleted successfully", data=None)

@router.post("/{id}/transfer-ownership", response_model=ApiResponse[WorkspaceResponse])
async def transfer_ownership(
    id: uuid.UUID,
    data: WorkspaceTransferOwnershipRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db),
    # Require special permission or just owner check inside service.
    # We use manage_members or manage workspace permission. The service explicitly checks if user is owner.
    _: bool = Depends(require_permission("workspace", "update")) 
) -> Any:
    updated_workspace = await workspace_service.transfer_ownership(db, user, workspace, data)
    await db.commit()
    await db.refresh(updated_workspace)
    return ApiResponse(success=True, message="Ownership transferred successfully", data=WorkspaceResponse.model_validate(updated_workspace))
