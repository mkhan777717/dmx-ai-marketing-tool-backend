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
from app.models.brand_kit import BrandKit
from app.models.asset import Asset
from app.constants.enums import RoleType, MemberStatus, WorkspaceStatus, AssetType, AssetStatus

@pytest.fixture
async def setup_campaign_env(async_db: AsyncSession, async_client: AsyncClient):
    owner = User(email="campaign_owner@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(owner_role)
    
    perm = Permission(name="campaign.create", resource="campaign", action="create")
    perm2 = Permission(name="campaign.read", resource="campaign", action="read")
    perm3 = Permission(name="campaign.update", resource="campaign", action="update")
    perm4 = Permission(name="campaign.delete", resource="campaign", action="delete")
    async_db.add_all([perm, perm2, perm3, perm4])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    rp4 = RolePermission(role_id=owner_role.id, permission_id=perm4.id)
    async_db.add_all([rp1, rp2, rp3, rp4])
    await async_db.commit()
    
    ws = Workspace(name="Campaign WS", slug="campaign-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    bk = BrandKit(workspace_id=ws.id, brand_name="BK", primary_color="#123456")
    async_db.add(bk)
    await async_db.commit()

    asset = Asset(
        workspace_id=ws.id, 
        uploaded_by=owner.id,
        file_name="test.png",
        original_file_name="test.png",
        asset_type=AssetType.IMAGE,
        mime_type="image/png",
        file_size=1234,
        storage_provider="local",
        storage_key="test-key",
        checksum="dummy-hash",
        status=AssetStatus.READY
    )
    async_db.add(asset)
    await async_db.commit()
    
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    async_db.add(m1)
    await async_db.commit()

    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: owner
    
    return {"owner": owner, "ws": ws, "owner_role": owner_role, "brand_kit": bk, "asset": asset}


@pytest.mark.asyncio
async def test_create_campaign(async_client: AsyncClient, setup_campaign_env, async_db: AsyncSession):
    ws_id = setup_campaign_env["ws"].id
    bk_id = setup_campaign_env["brand_kit"].id
    
    payload = {
        "campaign_name": "Summer Sale",
        "description": "50% off everything",
        "budget": 5000.00,
        "brand_kit_id": str(bk_id)
    }
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns", json=payload)
    
    assert response.status_code == 201
    assert response.json()["data"]["campaign_name"] == "Summer Sale"
    assert response.json()["data"]["status"] == "DRAFT"

@pytest.mark.asyncio
async def test_unique_campaign_name(async_client: AsyncClient, setup_campaign_env, async_db: AsyncSession):
    ws_id = setup_campaign_env["ws"].id
    
    payload = {"campaign_name": "Unique Campaign"}
    
    await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns", json=payload)
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns", json=payload)
    
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_date_validation(async_client: AsyncClient, setup_campaign_env, async_db: AsyncSession):
    ws_id = setup_campaign_env["ws"].id
    
    payload = {
        "campaign_name": "Bad Dates",
        "start_date": "2026-12-01T00:00:00Z",
        "end_date": "2026-11-01T00:00:00Z"
    }
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns", json=payload)
    
    assert response.status_code == 400
    assert "Start date cannot be after end date" in response.json()["detail"]

@pytest.mark.asyncio
async def test_attach_asset(async_client: AsyncClient, setup_campaign_env, async_db: AsyncSession):
    ws_id = setup_campaign_env["ws"].id
    asset_id = setup_campaign_env["asset"].id
    
    payload = {"campaign_name": "Asset Campaign"}
    create_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns", json=payload)
    campaign_id = create_resp.json()["data"]["id"]
    
    attach_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{campaign_id}/assets/{asset_id}")
    assert attach_resp.status_code == 200
    assert len(attach_resp.json()["data"]["assets"]) == 1
    assert attach_resp.json()["data"]["assets"][0]["id"] == str(asset_id)
