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
async def setup_invites_env(async_db: AsyncSession, async_client: AsyncClient):
    owner = User(email="inviter3b@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    viewer_role = Role(name="Viewer", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(viewer_role)
    
    perm = Permission(name="workspace_invite.create", resource="workspace_invite", action="create")
    perm2 = Permission(name="workspace_invite.read", resource="workspace_invite", action="read")
    perm3 = Permission(name="workspace_invite.delete", resource="workspace_invite", action="delete")
    async_db.add_all([perm, perm2, perm3])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=viewer_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=viewer_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=viewer_role.id, permission_id=perm3.id)
    async_db.add_all([rp1, rp2, rp3])
    await async_db.commit()
    
    ws = Workspace(name="Invite Test WS", slug="invite-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=viewer_role.id, status=MemberStatus.ACTIVE)
    async_db.add(m1)
    await async_db.commit()

    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: owner
    
    return {"owner": owner, "ws": ws, "viewer_role": viewer_role}

@pytest.mark.asyncio
async def test_create_invite(async_client: AsyncClient, setup_invites_env):
    ws_id = setup_invites_env["ws"].id
    role_id = setup_invites_env["viewer_role"].id
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/invites", json={
        "email": "new_invitee@test.com",
        "role_id": str(role_id)
    })
    
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "new_invitee@test.com"
    assert "token" in response.json()["data"]

@pytest.mark.asyncio
async def test_accept_invite(async_client: AsyncClient, setup_invites_env, async_db: AsyncSession):
    ws_id = setup_invites_env["ws"].id
    role_id = setup_invites_env["viewer_role"].id
    
    # 1. Create Invite
    create_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/invites", json={
        "email": "accept_me@test.com",
        "role_id": str(role_id)
    })
    token = create_resp.json()["data"]["token"]
    
    # 2. Mock new authenticated user
    new_user = User(email="accept_me@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(new_user)
    await async_db.commit()
    
    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: new_user
    
    # 3. Accept invite
    accept_resp = await async_client.post(f"/api/v1/invites/{token}/accept")
    assert accept_resp.status_code == 200
    
@pytest.mark.asyncio
async def test_revoke_invite(async_client: AsyncClient, setup_invites_env):
    ws_id = setup_invites_env["ws"].id
    role_id = setup_invites_env["viewer_role"].id
    
    # Create Invite
    create_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/invites", json={
        "email": "revoke_me@test.com",
        "role_id": str(role_id)
    })
    invite_id = create_resp.json()["data"]["id"]
    
    # Revoke Invite
    revoke_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/invites/{invite_id}/revoke")
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["data"]["status"] == "REVOKED"
