import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.constants.enums import MemberStatus, WorkspaceStatus
from app.main import app
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from scripts.seed_rbac import seed_rbac


@pytest.mark.asyncio
async def test_seed_rbac_idempotency_and_admin_permissions(
    async_db: AsyncSession, async_client: AsyncClient
):
    # 1. Run seed_rbac twice to ensure idempotency
    await seed_rbac(async_db)
    await seed_rbac(async_db)

    # 2. Verify System Roles exist
    stmt = select(Role).where(Role.is_system.is_(True))
    result = await async_db.execute(stmt)
    system_roles = {r.name: r for r in result.scalars().all()}

    assert "Owner" in system_roles
    assert "Admin" in system_roles
    assert "Editor" in system_roles
    assert "Viewer" in system_roles
    assert "Client" in system_roles

    admin_role = system_roles["Admin"]

    # 3. Verify Admin permissions in DB
    stmt = (
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == admin_role.id)
    )
    res = await async_db.execute(stmt)
    admin_perms = res.scalars().all()
    admin_perm_names = {p.name for p in admin_perms}

    # Admin MUST have workspace.read and workspace_member.read
    assert "workspace.read" in admin_perm_names
    assert "workspace_member.read" in admin_perm_names
    assert "workspace_member.update" in admin_perm_names
    assert "workspace_invite.create" in admin_perm_names

    # Admin MUST NOT have billing.manage
    assert "billing.manage" not in admin_perm_names

    # 4. End-to-end API test with Admin2 (non-owner with Admin role)
    suffix = uuid.uuid4().hex[:8]

    # Create Owner user
    ws_owner = User(
        email=f"ws_owner_{suffix}@test.com", supabase_user_id=uuid.uuid4()
    )
    # Create Admin2 user
    admin2_user = User(
        email=f"admin2_{suffix}@test.com", supabase_user_id=uuid.uuid4()
    )
    async_db.add_all([ws_owner, admin2_user])
    await async_db.commit()
    await async_db.refresh(ws_owner)
    await async_db.refresh(admin2_user)

    # Create Workspace owned by ws_owner
    ws = Workspace(
        name=f"Admin Test WS {suffix}",
        slug=f"admin-test-ws-{suffix}",
        owner_id=ws_owner.id,
        status=WorkspaceStatus.ACTIVE,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    # Add Admin2 user to workspace with Admin role
    admin2_member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=admin2_user.id,
        role_id=admin_role.id,
        status=MemberStatus.ACTIVE,
    )
    async_db.add(admin2_member)
    await async_db.commit()

    # Authenticate as Admin2
    app.dependency_overrides[get_current_user] = lambda: admin2_user

    try:
        # GET /api/v1/workspaces/{active_workspace_id} as Admin2 -> 200 OK
        resp_ws = await async_client.get(f"/api/v1/workspaces/{ws.id}")
        assert resp_ws.status_code == 200, f"Expected 200, got {resp_ws.status_code}: {resp_ws.text}"
        assert resp_ws.json()["data"]["id"] == str(ws.id)

        # GET /api/v1/workspaces/{active_workspace_id}/members as Admin2 -> 200 OK
        resp_members = await async_client.get(f"/api/v1/workspaces/{ws.id}/members")
        assert resp_members.status_code == 200, f"Expected 200, got {resp_members.status_code}: {resp_members.text}"
        assert len(resp_members.json()["data"]) >= 1
    finally:
        app.dependency_overrides.clear()
