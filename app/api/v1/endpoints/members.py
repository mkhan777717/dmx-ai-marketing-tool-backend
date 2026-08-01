import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_user,
    get_current_workspace,
    require_permission,
)
from app.db.session import get_db_session
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.responses import ApiResponse
from app.schemas.workspace_member import (
    WorkspaceMemberResponse,
    WorkspaceMemberUpdateRequest,
)
from app.services.workspace_member import workspace_member_service

router = APIRouter()


@router.get(
    "/{workspace_id}/members", response_model=ApiResponse[list[WorkspaceMemberResponse]]
)
async def get_members(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "read")),
) -> Any:
    members = await workspace_member_service.get_members(db, workspace.id)
    return ApiResponse(
        success=True,
        message="Members retrieved successfully",
        data=[WorkspaceMemberResponse.model_validate(m) for m in members],
    )


@router.get(
    "/{workspace_id}/members/{member_id}",
    response_model=ApiResponse[WorkspaceMemberResponse],
)
async def get_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "read")),
) -> Any:
    member = await workspace_member_service.get_member(db, workspace.id, member_id)
    return ApiResponse(
        success=True,
        message="Member retrieved successfully",
        data=WorkspaceMemberResponse.model_validate(member),
    )


@router.patch(
    "/{workspace_id}/members/{member_id}",
    response_model=ApiResponse[WorkspaceMemberResponse],
)
async def update_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    data: WorkspaceMemberUpdateRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "update")),
) -> Any:
    member = await workspace_member_service.change_role(
        db, user, workspace, member_id, data.role_id
    )
    await db.commit()
    await db.refresh(member)
    return ApiResponse(
        success=True,
        message="Member role updated successfully",
        data=WorkspaceMemberResponse.model_validate(member),
    )


@router.delete("/{workspace_id}/members/{member_id}", response_model=ApiResponse[None])
async def remove_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "delete")),
) -> Any:
    await workspace_member_service.remove_member(db, user, workspace, member_id)
    await db.commit()
    return ApiResponse(success=True, message="Member removed successfully", data=None)


@router.post(
    "/{workspace_id}/members/{member_id}/suspend",
    response_model=ApiResponse[WorkspaceMemberResponse],
)
async def suspend_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "update")),
) -> Any:
    member = await workspace_member_service.suspend_member(
        db, user, workspace, member_id
    )
    await db.commit()
    await db.refresh(member)
    return ApiResponse(
        success=True,
        message="Member suspended successfully",
        data=WorkspaceMemberResponse.model_validate(member),
    )


@router.post(
    "/{workspace_id}/members/{member_id}/reactivate",
    response_model=ApiResponse[WorkspaceMemberResponse],
)
async def reactivate_member(
    workspace_id: uuid.UUID,
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_member", "update")),
) -> Any:
    member = await workspace_member_service.reactivate_member(
        db, user, workspace, member_id
    )
    await db.commit()
    await db.refresh(member)
    return ApiResponse(
        success=True,
        message="Member reactivated successfully",
        data=WorkspaceMemberResponse.model_validate(member),
    )
