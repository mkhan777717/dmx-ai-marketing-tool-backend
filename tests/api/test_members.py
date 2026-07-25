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
    suffix = str(uuid.uuid4())[:8]
    # Setup owner
    owner = User(email=f"owner3b_{suffix}@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    # Setup member
    member_user = User(email=f"member3b_{suffix}@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(member_user)
    await async_db.commit()
    await async_db.refresh(owner)
    await async_db.refresh(member_user)
    
    from sqlalchemy.future import select
    # Setup role
    result = await async_db.execute(select(Role).filter_by(name="Owner", is_system=True))
    owner_role = result.scalars().first()
    result = await async_db.execute(select(Role).filter_by(name="Viewer", is_system=True))
    viewer_role = result.scalars().first()
    
    # Setup permission
    from sqlalchemy.future import select
    
    perms = []
    for action in ["read", "update", "delete"]:
        result = await async_db.execute(select(Permission).filter_by(resource="workspace_member", action=action))
        p = result.scalar_one_or_none()
        if not p:
            p = Permission(name=f"workspace_member.{action}", resource="workspace_member", action=action)
            async_db.add(p)
            try:
                await async_db.commit()
                await async_db.refresh(p)
            except Exception:
                await async_db.rollback()
                result = await async_db.execute(select(Permission).filter_by(resource="workspace_member", action=action))
                p = result.scalar_one_or_none()
        perms.append(p)
    perm1, perm2, perm3 = perms
    
    # Assign permissions to roles
    for role_id, perm_id in [(owner_role.id, perm1.id), (owner_role.id, perm2.id), (owner_role.id, perm3.id)]:
        rp = RolePermission(role_id=role_id, permission_id=perm_id)
        async_db.add(rp)
        try:
            await async_db.commit()
        except Exception:
            await async_db.rollback()

    await async_db.refresh(owner)
    await async_db.refresh(member_user)
    await async_db.refresh(owner_role)
    await async_db.refresh(viewer_role)
    
    # Setup Workspace
    ws = Workspace(name="Member Test WS", slug=f"member-ws-{suffix}", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)
    
    # Setup Memberships
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    m2 = WorkspaceMember(workspace_id=ws.id, user_id=member_user.id, role_id=viewer_role.id, status=MemberStatus.ACTIVE)
    async_db.add_all([m1, m2])
    await async_db.commit()
    await async_db.refresh(m1)
    await async_db.refresh(m2)

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
