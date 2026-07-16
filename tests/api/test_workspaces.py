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
async def setup_test_auth(async_db: AsyncSession, async_client: AsyncClient):
    # Setup User
    user = User(email="test3a@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(user)
    
    # Setup Target User
    user2 = User(email="target3a@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(user2)
    
    # Setup System Role 'Owner'
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(owner_role)
    
    # Setup System Role 'Viewer'
    viewer_role = Role(name="Viewer", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(viewer_role)
    
    # Setup Permissions
    perm1 = Permission(name="workspace.update", resource="workspace", action="update")
    perm2 = Permission(name="workspace.delete", resource="workspace", action="delete")
    perm3 = Permission(name="workspace.read", resource="workspace", action="read")
    async_db.add_all([perm1, perm2, perm3])
    await async_db.commit()
    
    # Assign permissions to roles
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm1.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    rp4 = RolePermission(role_id=viewer_role.id, permission_id=perm3.id)
    async_db.add_all([rp1, rp2, rp3, rp4])
    await async_db.commit()

    # Mock get_current_user in FastAPI
    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: user
    
    return {"user": user, "user2": user2, "owner_role": owner_role, "viewer_role": viewer_role}

@pytest.mark.asyncio
async def test_create_workspace(async_client: AsyncClient, setup_test_auth):
    response = await async_client.post("/api/v1/workspaces", json={
        "name": "New API Workspace"
    })
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "New API Workspace"
    assert data["slug"] == "new-api-workspace"
    assert data["owner_id"] == str(setup_test_auth["user"].id)

@pytest.mark.asyncio
async def test_get_workspace_and_permissions(async_client: AsyncClient, setup_test_auth, async_db: AsyncSession):
    # Setup workspace manually to test permission boundaries
    ws = Workspace(name="Test WS", slug="test-ws", owner_id=setup_test_auth["user"].id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    # Assign user as Owner
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=setup_test_auth["user"].id,
        role_id=setup_test_auth["owner_role"].id,
        status=MemberStatus.ACTIVE
    )
    async_db.add(member)
    await async_db.commit()

    response = await async_client.get(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Test WS"

@pytest.mark.asyncio
async def test_update_workspace(async_client: AsyncClient, setup_test_auth, async_db: AsyncSession):
    ws = Workspace(name="Update Test WS", slug="update-ws", owner_id=setup_test_auth["user"].id)
    async_db.add(ws)
    await async_db.commit()
    
    # Assign user as Owner
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=setup_test_auth["user"].id,
        role_id=setup_test_auth["owner_role"].id,
        status=MemberStatus.ACTIVE
    )
    async_db.add(member)
    await async_db.commit()

    response = await async_client.patch(f"/api/v1/workspaces/{ws.id}", json={
        "name": "Updated API WS"
    })
    
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated API WS"

@pytest.mark.asyncio
async def test_soft_delete_workspace(async_client: AsyncClient, setup_test_auth, async_db: AsyncSession):
    ws = Workspace(name="Delete Test WS", slug="delete-ws", owner_id=setup_test_auth["user"].id)
    async_db.add(ws)
    await async_db.commit()
    
    member = WorkspaceMember(workspace_id=ws.id, user_id=setup_test_auth["user"].id, role_id=setup_test_auth["owner_role"].id, status=MemberStatus.ACTIVE)
    async_db.add(member)
    await async_db.commit()

    response = await async_client.delete(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200
    
    await async_db.refresh(ws)
    assert ws.deleted_at is not None

@pytest.mark.asyncio
async def test_transfer_ownership(async_client: AsyncClient, setup_test_auth, async_db: AsyncSession):
    ws = Workspace(name="Transfer Test WS", slug="transfer-ws", owner_id=setup_test_auth["user"].id)
    async_db.add(ws)
    await async_db.commit()
    
    user1 = setup_test_auth["user"]
    user2 = setup_test_auth["user2"]
    viewer_role = setup_test_auth["viewer_role"]
    owner_role = setup_test_auth["owner_role"]
    
    # Create memberships
    mem1 = WorkspaceMember(workspace_id=ws.id, user_id=user1.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    mem2 = WorkspaceMember(workspace_id=ws.id, user_id=user2.id, role_id=viewer_role.id, status=MemberStatus.ACTIVE)
    async_db.add_all([mem1, mem2])
    await async_db.commit()
    
    response = await async_client.post(f"/api/v1/workspaces/{ws.id}/transfer-ownership", json={
        "new_owner_id": str(user2.id),
        "new_role_id": str(viewer_role.id)
    })
    
    assert response.status_code == 200
    assert response.json()["data"]["owner_id"] == str(user2.id)
    
    await async_db.refresh(ws)
    await async_db.refresh(mem1)
    await async_db.refresh(mem2)
    
    assert ws.owner_id == user2.id
    assert mem1.role_id == viewer_role.id
    assert mem2.role_id == owner_role.id
