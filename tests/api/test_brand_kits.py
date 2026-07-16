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
from app.services.brand_context import brand_context_service

@pytest.fixture
async def setup_brand_kit_env(async_db: AsyncSession, async_client: AsyncClient):
    owner = User(email="owner_bk@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(owner_role)
    
    perm = Permission(name="brand_kit.create", resource="brand_kit", action="create")
    perm2 = Permission(name="brand_kit.read", resource="brand_kit", action="read")
    perm3 = Permission(name="brand_kit.update", resource="brand_kit", action="update")
    perm4 = Permission(name="brand_kit.delete", resource="brand_kit", action="delete")
    async_db.add_all([perm, perm2, perm3, perm4])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    rp4 = RolePermission(role_id=owner_role.id, permission_id=perm4.id)
    async_db.add_all([rp1, rp2, rp3, rp4])
    await async_db.commit()
    
    ws = Workspace(name="BrandKit WS", slug="brandkit-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
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
async def test_create_brand_kit(async_client: AsyncClient, setup_brand_kit_env, async_db: AsyncSession):
    ws_id = setup_brand_kit_env["ws"].id
    
    payload = {
        "brand_name": "Test Brand",
        "primary_color": "#FF0000",
        "website_url": "test.com", # Should normalize to https://test.com
        "default_language": " en " # Should normalize to "en"
    }
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/brand-kit", json=payload)
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["brand_name"] == "Test Brand"
    assert data["primary_color"] == "#FF0000"
    assert data["website_url"] == "https://test.com"
    assert data["default_language"] == "en"

@pytest.mark.asyncio
async def test_create_duplicate_brand_kit(async_client: AsyncClient, setup_brand_kit_env, async_db: AsyncSession):
    ws_id = setup_brand_kit_env["ws"].id
    
    payload = {"brand_name": "Test Brand"}
    
    # First create
    await async_client.post(f"/api/v1/workspaces/{ws_id}/brand-kit", json=payload)
    
    # Second create should fail
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/brand-kit", json=payload)
    
    assert response.status_code == 400
    assert "already has a Brand Kit" in response.json()["detail"]

@pytest.mark.asyncio
async def test_brand_context_service(async_client: AsyncClient, setup_brand_kit_env, async_db: AsyncSession):
    ws_id = setup_brand_kit_env["ws"].id
    
    payload = {
        "brand_name": "Context Brand",
        "primary_color": "#00FF00"
    }
    
    await async_client.post(f"/api/v1/workspaces/{ws_id}/brand-kit", json=payload)
    
    context = await brand_context_service.build_context(async_db, ws_id)
    
    assert context is not None
    assert context["brand_name"] == "Context Brand"
    assert context["colors"]["primary"] == "#00FF00"
