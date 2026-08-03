import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
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
from app.schemas.workspace_invite import WorkspaceInviteRequest, WorkspaceInviteResponse
from app.services.workspace_invitation import workspace_invitation_service

router = APIRouter()


@router.post(
    "/workspaces/{workspace_id}/invites",
    response_model=ApiResponse[WorkspaceInviteResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    workspace_id: uuid.UUID,
    data: WorkspaceInviteRequest,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_invite", "create")),
) -> Any:
    invite = await workspace_invitation_service.create_invite(
        db, user, workspace, data.email, data.role_id
    )
    await db.commit()
    await db.refresh(invite)
    return ApiResponse(
        success=True,
        message="Invitation sent successfully",
        data=WorkspaceInviteResponse.model_validate(invite),
    )


@router.get(
    "/workspaces/{workspace_id}/invites",
    response_model=ApiResponse[list[WorkspaceInviteResponse]],
)
async def get_invites(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_invite", "read")),
) -> Any:
    invites = await workspace_invitation_service.get_invites(db, workspace.id)
    return ApiResponse(
        success=True,
        message="Invitations retrieved successfully",
        data=[WorkspaceInviteResponse.model_validate(i) for i in invites],
    )


@router.post(
    "/workspaces/{workspace_id}/invites/{invite_id}/revoke",
    response_model=ApiResponse[WorkspaceInviteResponse],
)
async def revoke_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_invite", "delete")),
) -> Any:
    invite = await workspace_invitation_service.revoke_invite(
        db, user, workspace, invite_id
    )
    await db.commit()
    await db.refresh(invite)
    return ApiResponse(
        success=True,
        message="Invitation revoked successfully",
        data=WorkspaceInviteResponse.model_validate(invite),
    )


@router.post(
    "/workspaces/{workspace_id}/invites/{invite_id}/resend",
    response_model=ApiResponse[WorkspaceInviteResponse],
)
async def resend_invite(
    workspace_id: uuid.UUID,
    invite_id: uuid.UUID,
    user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
    db: AsyncSession = Depends(get_db_session),
    _: bool = Depends(require_permission("workspace_invite", "update")),
) -> Any:
    invite = await workspace_invitation_service.resend_invite(
        db, user, workspace, invite_id
    )
    await db.commit()
    await db.refresh(invite)
    return ApiResponse(
        success=True,
        message="Invitation resent successfully",
        data=WorkspaceInviteResponse.model_validate(invite),
    )


@router.post("/invites/{token}/accept", response_model=ApiResponse[None])
async def accept_invite(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    await workspace_invitation_service.accept_invite(db, user, token)
    await db.commit()
    return ApiResponse(
        success=True, message="Invitation accepted successfully", data=None
    )
