import pytest
import uuid
import io
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
async def setup_asset_env(async_db: AsyncSession, async_client: AsyncClient):
    owner = User(email="asset_owner@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(owner_role)
    
    perm = Permission(name="asset.create", resource="asset", action="create")
    perm2 = Permission(name="asset.read", resource="asset", action="read")
    perm3 = Permission(name="asset.update", resource="asset", action="update")
    perm4 = Permission(name="asset.delete", resource="asset", action="delete")
    async_db.add_all([perm, perm2, perm3, perm4])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    rp4 = RolePermission(role_id=owner_role.id, permission_id=perm4.id)
    async_db.add_all([rp1, rp2, rp3, rp4])
    await async_db.commit()
    
    ws = Workspace(name="Asset WS", slug="asset-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    async_db.add(m1)
    await async_db.commit()

    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: owner
    
    return {"owner": owner, "ws": ws, "owner_role": owner_role}

@pytest.mark.asyncio
async def test_upload_asset(async_client: AsyncClient, setup_asset_env, async_db: AsyncSession):
    ws_id = setup_asset_env["ws"].id
    
    file_content = b"fake image content"
    files = {'file': ('test.jpg', io.BytesIO(file_content), 'image/jpeg')}
    data = {'folder': '/campaigns', 'tags': 'logo,brand'}
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/upload", files=files, data=data)
    
    assert response.status_code == 201
    assert response.json()["data"]["original_file_name"] == "test.jpg"
    assert response.json()["data"]["asset_type"] == "IMAGE"
    assert response.json()["data"]["folder"] == "/campaigns"
    assert "logo" in response.json()["data"]["tags"]

@pytest.mark.asyncio
async def test_duplicate_upload(async_client: AsyncClient, setup_asset_env, async_db: AsyncSession):
    ws_id = setup_asset_env["ws"].id
    file_content = b"duplicate content"
    
    files1 = {'file': ('test1.jpg', io.BytesIO(file_content), 'image/jpeg')}
    await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/upload", files=files1)
    
    files2 = {'file': ('test2.jpg', io.BytesIO(file_content), 'image/jpeg')}
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/upload", files=files2)
    
    assert response.status_code == 409
    assert "identical asset already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_search_assets(async_client: AsyncClient, setup_asset_env, async_db: AsyncSession):
    ws_id = setup_asset_env["ws"].id
    
    file_content = b"searchable content"
    files = {'file': ('findme.txt', io.BytesIO(file_content), 'text/plain')}
    await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/upload", files=files)
    
    response = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets/search?q=findme")
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["original_file_name"] == "findme.txt"

@pytest.mark.asyncio
async def test_soft_delete_and_restore(async_client: AsyncClient, setup_asset_env, async_db: AsyncSession):
    ws_id = setup_asset_env["ws"].id
    
    file_content = b"delete content"
    files = {'file': ('del.jpg', io.BytesIO(file_content), 'image/jpeg')}
    upload_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/upload", files=files)
    asset_id = upload_resp.json()["data"]["id"]
    
    # Soft delete
    del_resp = await async_client.delete(f"/api/v1/workspaces/{ws_id}/assets/{asset_id}")
    assert del_resp.status_code == 200
    
    # Cannot find in regular list
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets")
    assert not any(a["id"] == asset_id for a in list_resp.json()["data"])
    
    # Restore
    res_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/assets/{asset_id}/restore")
    assert res_resp.status_code == 200
    
    # Can find in regular list again
    list_resp2 = await async_client.get(f"/api/v1/workspaces/{ws_id}/assets")
    assert any(a["id"] == asset_id for a in list_resp2.json()["data"])
