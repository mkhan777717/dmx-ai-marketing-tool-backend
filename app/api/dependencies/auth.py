import uuid

from fastapi import Depends, Header, HTTPException, Request
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


async def get_workspace_id(
    request: Request,
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
) -> uuid.UUID | None:
    """
    Resolves workspace_id from path parameter, query parameter, or X-Workspace-ID header.
    """
    # 1. Path parameters
    if "workspace_id" in request.path_params:
        val = request.path_params["workspace_id"]
        if isinstance(val, uuid.UUID):
            return val
        try:
            return uuid.UUID(str(val))
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid workspace_id in path")

    # 2. Query parameters
    query_ws = request.query_params.get("workspace_id")
    if query_ws:
        try:
            return uuid.UUID(query_ws)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid workspace_id in query")

    # 3. Header (X-Workspace-ID)
    if x_workspace_id:
        try:
            return uuid.UUID(x_workspace_id)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid X-Workspace-ID header format"
            )

    return None


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
    workspace_id: uuid.UUID | None = Depends(get_workspace_id),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Workspace:
    """
    Dependency to get the workspace context and verify user belongs to it.
    """
    if not workspace_id:
        raise HTTPException(
            status_code=400,
            detail="Workspace context required (X-Workspace-ID header or workspace_id parameter)",
        )

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
        workspace_id: uuid.UUID | None = Depends(get_workspace_id),
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session),
    ):
        if not workspace_id:
            raise HTTPException(
                status_code=400,
                detail="Workspace context required (X-Workspace-ID header or workspace_id parameter)",
            )

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
