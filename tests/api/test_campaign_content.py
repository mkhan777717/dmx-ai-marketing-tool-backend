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
from app.models.campaign import Campaign
from app.constants.enums import RoleType, MemberStatus, WorkspaceStatus, CampaignStatus

@pytest.fixture
async def setup_content_env(async_db: AsyncSession, async_client: AsyncClient):
    owner = User(email="content_owner@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    
    owner_role = Role(name="Owner", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(owner_role)
    
    perm = Permission(name="campaign_content.create", resource="campaign_content", action="create")
    perm2 = Permission(name="campaign_content.read", resource="campaign_content", action="read")
    perm3 = Permission(name="campaign_content.update", resource="campaign_content", action="update")
    perm4 = Permission(name="campaign_content.delete", resource="campaign_content", action="delete")
    async_db.add_all([perm, perm2, perm3, perm4])
    await async_db.commit()
    
    rp1 = RolePermission(role_id=owner_role.id, permission_id=perm.id)
    rp2 = RolePermission(role_id=owner_role.id, permission_id=perm2.id)
    rp3 = RolePermission(role_id=owner_role.id, permission_id=perm3.id)
    rp4 = RolePermission(role_id=owner_role.id, permission_id=perm4.id)
    async_db.add_all([rp1, rp2, rp3, rp4])
    await async_db.commit()
    
    ws = Workspace(name="Content WS", slug="content-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    m1 = WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role_id=owner_role.id, status=MemberStatus.ACTIVE)
    async_db.add(m1)
    await async_db.commit()

    camp = Campaign(
        workspace_id=ws.id, 
        owner_id=owner.id, 
        campaign_name="Test Campaign", 
        status=CampaignStatus.ACTIVE
    )
    async_db.add(camp)
    await async_db.commit()

    from app.api.dependencies.auth import get_current_user
    from app.main import app
    app.dependency_overrides[get_current_user] = lambda: owner
    
    return {"owner": owner, "ws": ws, "owner_role": owner_role, "campaign": camp}


@pytest.mark.asyncio
async def test_create_content(async_client: AsyncClient, setup_content_env, async_db: AsyncSession):
    ws_id = setup_content_env["ws"].id
    camp_id = setup_content_env["campaign"].id
    
    payload = {
        "title": "Welcome Email",
        "content_type": "EMAIL",
        "body": "Hello world!"
    }
    
    response = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content", json=payload)
    
    assert response.status_code == 201
    assert response.json()["data"]["title"] == "Welcome Email"
    assert response.json()["data"]["version"] == 1
    assert response.json()["data"]["is_current"] is True

@pytest.mark.asyncio
async def test_versioning_flow(async_client: AsyncClient, setup_content_env, async_db: AsyncSession):
    ws_id = setup_content_env["ws"].id
    camp_id = setup_content_env["campaign"].id
    
    payload = {
        "title": "V1 Content",
        "content_type": "BLOG",
        "body": "Original text"
    }
    
    create_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content", json=payload)
    content_id = create_resp.json()["data"]["id"]
    
    # Create new version
    ver_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{content_id}/version")
    assert ver_resp.status_code == 200
    v2_id = ver_resp.json()["data"]["id"]
    assert ver_resp.json()["data"]["version"] == 2
    assert ver_resp.json()["data"]["is_current"] is True
    
    # Update V2
    update_payload = {"title": "V2 Content"}
    await async_client.patch(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{v2_id}", json=update_payload)
    
    # V1 should not be current
    v1_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{content_id}")
    assert v1_resp.status_code == 404  # Because get_current_version filters is_current=True
    
    # List versions
    list_resp = await async_client.get(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{content_id}/versions")
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 2
    
    # Restore V1
    restore_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{content_id}/restore")
    assert restore_resp.status_code == 200
    assert restore_resp.json()["data"]["is_current"] is True
    assert restore_resp.json()["data"]["id"] == content_id

@pytest.mark.asyncio
async def test_status_transition_notifications(async_client: AsyncClient, setup_content_env, async_db: AsyncSession):
    ws_id = setup_content_env["ws"].id
    camp_id = setup_content_env["campaign"].id
    
    payload = {
        "title": "Review Me",
        "content_type": "SOCIAL_POST"
    }
    create_resp = await async_client.post(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content", json=payload)
    content_id = create_resp.json()["data"]["id"]
    
    # Update status to IN_REVIEW
    update_payload = {"status": "IN_REVIEW"}
    resp = await async_client.patch(f"/api/v1/workspaces/{ws_id}/campaigns/{camp_id}/content/{content_id}", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "IN_REVIEW"
