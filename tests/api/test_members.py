import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.role import Role
from app.models.workspace_member import WorkspaceMember
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.constants.enums import RoleType, MemberStatus, WorkspaceStatus

@pytest.fixture
async def setup_members_env(async_db: AsyncSession, async_client: AsyncClient):
    # Setup owner
    owner = User(email="owner3b@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    # Setup member
    member_user = User(email="member3b@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(member_user)
    
    # Setup role
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    viewer_role = Role(name="Viewer", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add_all([owner_role, viewer_role])
    await async_db.commit()
    
    # Setup permission
    perm = Permission(name="workspace_member.read", resource="workspace_member", action="read")
    perm2 = Permission(name="workspace_member.update", resource="workspace_member", action="update")
    perm3 = Permission(name="workspace_member.delete", resource="workspace_member", action="delete")
    async_db.add_all([perm, perm2, perm3])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    async_db.add_all([rp1, rp2, rp3])
    await async_db.commit()
    
    # Setup Workspace
    ws = Workspace(name="Member Test WS", slug="member-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    # Setup Memberships
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    m2 = WorkspaceMember(workspace_id=ws.id, user_id=member_user.id, role_id=viewer_role.id, status=MemberStatus.ACTIVE)
    async_db.add_all([m1, m2])
    await async_db.commit()

    # Mock Auth context
    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: owner
    
    return {"owner": owner, "member_user": member_user, "ws": ws, "m2": m2, "viewer_role": viewer_role, "owner_role": owner_role}

@pytest.mark.asyncio
async def test_get_members(async_client: AsyncClient, setup_members_env):
    ws_id = setup_members_env["ws"].id
    response = await async_client.get(f"/api/v1/workspaces/{ws_id}/members")
    
    assert response.status_code == 200
    assert len(response.json()["data"]) == 2

@pytest.mark.asyncio
async def test_change_member_role(async_client: AsyncClient, setup_members_env, async_db: AsyncSession):
    ws_id = setup_members_env["ws"].id
    mem_id = setup_members_env["m2"].id
    owner_role_id = setup_members_env["owner_role"].id
    
    response = await async_client.patch(f"/api/v1/workspaces/{ws_id}/members/{mem_id}", json={
        "role_id": str(owner_role_id)
    })
    
    assert response.status_code == 200
    assert response.json()["data"]["role_id"] == str(owner_role_id)

@pytest.mark.asyncio
async def test_suspend_member(async_client: AsyncClient, setup_members_env):
    ws_id = setup_members_env["ws"].id
    mem_id = setup_members_env["m2"].id
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/members/{mem_id}/suspend")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "SUSPENDED"

@pytest.mark.asyncio
async def test_remove_member(async_client: AsyncClient, setup_members_env):
    ws_id = setup_members_env["ws"].id
    mem_id = setup_members_env["m2"].id
    
    response = await async_client.delete(f"/api/v1/workspaces/{ws_id}/members/{mem_id}")
    assert response.status_code == 200
