import uuid

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.rbac import role_permission_repo
from app.repositories.workspace import workspace_repo
from app.repositories.workspace_member import workspace_member_repo
from app.services.supabase_auth import SupabaseAuthService

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """
    Dependency to get the current authenticated user.
    """
    token = credentials.credentials
    payload = SupabaseAuthService.verify_jwt(token)
    user = await SupabaseAuthService.get_or_create_user(db, payload)

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Inject into request state for middleware or downstream usage if needed
    request.state.user = user
    return user


async def get_current_workspace(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Workspace:
    """
    Dependency to get the workspace context and verify user belongs to it.
    """
    workspace = await workspace_repo.get_by_id(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    member = await workspace_member_repo.get_member(
        db, workspace_id=workspace.id, user_id=user.id
    )
    if not member or member.status != "ACTIVE":
        # Allow owner bypassing member check if not explicitly in workspace_members (though they should be)
        if workspace.owner_id != user.id:
            raise HTTPException(
                status_code=403, detail="Not a member of this workspace"
            )

    return workspace


def require_permission(resource: str, action: str):
    """
    Dependency generator for RBAC.
    """

    async def permission_checker(
        workspace_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ):
        member = await workspace_member_repo.get_member(
            db, workspace_id=workspace_id, user_id=user.id
        )
        if not member:
            workspace = await workspace_repo.get_by_id(db, workspace_id)
            if workspace and workspace.owner_id == user.id:
                return True  # Owner bypass
            raise HTTPException(status_code=403, detail="Not authorized")

        role_id = member.role_id
        permissions = await role_permission_repo.get_role_permissions(db, role_id)

        has_permission = any(
            p.resource == resource and p.action == action for p in permissions
        )
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {resource}.{action}",
            )

        return True

    return permission_checker
