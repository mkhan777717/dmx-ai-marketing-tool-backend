import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import MemberStatus, WorkspaceStatus
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


@pytest.fixture
async def setup_test_auth(async_db: AsyncSession, async_client: AsyncClient):
    suffix = str(uuid.uuid4())[:8]
    # Setup User
    user = User(email=f"test3a_{suffix}@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(user)

    # Setup Target User
    user2 = User(email=f"target3a_{suffix}@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(user2)
    await async_db.commit()
    await async_db.refresh(user)
    await async_db.refresh(user2)

    from sqlalchemy.future import select

    # Setup System Role 'Owner'
    result = await async_db.execute(
        select(Role).filter_by(name="Owner", is_system=True)
    )
    owner_role = result.scalars().first()

    # Setup System Role 'Viewer'
    result = await async_db.execute(
        select(Role).filter_by(name="Viewer", is_system=True)
    )
    viewer_role = result.scalars().first()

    # Setup Permissions
    from sqlalchemy.future import select

    perms = []
    for action in ["update", "delete", "read"]:
        result = await async_db.execute(
            select(Permission).filter_by(resource="workspace", action=action)
        )
        p = result.scalar_one_or_none()
        if not p:
            p = Permission(
                name=f"workspace.{action}", resource="workspace", action=action
            )
            async_db.add(p)
            try:
                await async_db.commit()
                await async_db.refresh(p)
            except Exception:
                await async_db.rollback()
                result = await async_db.execute(
                    select(Permission).filter_by(resource="workspace", action=action)
                )
                p = result.scalar_one_or_none()
        perms.append(p)
    perm1, perm2, perm3 = perms

    # Assign permissions to roles
    for role_id, perm_id in [
        (owner_role.id, perm1.id),
        (owner_role.id, perm2.id),
        (owner_role.id, perm3.id),
        (viewer_role.id, perm3.id),
    ]:
        rp = RolePermission(role_id=role_id, permission_id=perm_id)
        async_db.add(rp)
        try:
            await async_db.commit()
        except Exception:
            await async_db.rollback()

    await async_db.refresh(user)
    await async_db.refresh(user2)
    await async_db.refresh(owner_role)
    await async_db.refresh(viewer_role)

    # Mock get_current_user in FastAPI
    from app.api.dependencies.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user

    return {
        "user": user,
        "user2": user2,
        "owner_role": owner_role,
        "viewer_role": viewer_role,
        "suffix": suffix,
    }


@pytest.mark.asyncio
async def test_create_workspace(async_client: AsyncClient, setup_test_auth):
    import uuid

    suffix = uuid.uuid4().hex[:8]
    response = await async_client.post(
        "/api/v1/workspaces", json={"name": f"New API Workspace {suffix}"}
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == f"New API Workspace {suffix}"
    assert data["slug"] == f"new-api-workspace-{suffix}"
    assert data["owner_id"] == str(setup_test_auth["user"].id)


@pytest.mark.asyncio
async def test_get_workspace_and_permissions(
    async_client: AsyncClient, setup_test_auth, async_db: AsyncSession
):
    # Setup workspace manually to test permission boundaries
    suffix = setup_test_auth["suffix"]
    ws = Workspace(
        name="Test WS",
        slug=f"test-ws-{suffix}",
        owner_id=setup_test_auth["user"].id,
        status=WorkspaceStatus.ACTIVE,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    # Assign user as Owner
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=setup_test_auth["user"].id,
        role_id=setup_test_auth["owner_role"].id,
        status=MemberStatus.ACTIVE,
    )
    async_db.add(member)
    await async_db.commit()

    response = await async_client.get(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Test WS"


@pytest.mark.asyncio
async def test_update_workspace(
    async_client: AsyncClient, setup_test_auth, async_db: AsyncSession
):
    suffix = setup_test_auth["suffix"]
    ws = Workspace(
        name="Update Test WS",
        slug=f"update-ws-{suffix}",
        owner_id=setup_test_auth["user"].id,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    # Assign user as Owner
    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=setup_test_auth["user"].id,
        role_id=setup_test_auth["owner_role"].id,
        status=MemberStatus.ACTIVE,
    )
    async_db.add(member)
    await async_db.commit()

    response = await async_client.patch(
        f"/api/v1/workspaces/{ws.id}", json={"name": "Updated API WS"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Updated API WS"


@pytest.mark.asyncio
async def test_soft_delete_workspace(
    async_client: AsyncClient, setup_test_auth, async_db: AsyncSession
):
    suffix = setup_test_auth["suffix"]
    ws = Workspace(
        name="Delete Test WS",
        slug=f"delete-ws-{suffix}",
        owner_id=setup_test_auth["user"].id,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    member = WorkspaceMember(
        workspace_id=ws.id,
        user_id=setup_test_auth["user"].id,
        role_id=setup_test_auth["owner_role"].id,
        status=MemberStatus.ACTIVE,
    )
    async_db.add(member)
    await async_db.commit()

    response = await async_client.delete(f"/api/v1/workspaces/{ws.id}")
    assert response.status_code == 200

    await async_db.refresh(ws)
    assert ws.deleted_at is not None


@pytest.mark.asyncio
async def test_transfer_ownership(
    async_client: AsyncClient, setup_test_auth, async_db: AsyncSession
):
    suffix = setup_test_auth["suffix"]
    ws = Workspace(
        name="Transfer Test WS",
        slug=f"transfer-ws-{suffix}",
        owner_id=setup_test_auth["user"].id,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    user1 = setup_test_auth["user"]
    user2 = setup_test_auth["user2"]
    viewer_role = setup_test_auth["viewer_role"]
    owner_role = setup_test_auth["owner_role"]

    # Create memberships
    mem1 = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user1.id,
        role_id=owner_role.id,
        status=MemberStatus.ACTIVE,
    )
    mem2 = WorkspaceMember(
        workspace_id=ws.id,
        user_id=user2.id,
        role_id=viewer_role.id,
        status=MemberStatus.ACTIVE,
    )
    async_db.add_all([mem1, mem2])
    await async_db.commit()

    response = await async_client.post(
        f"/api/v1/workspaces/{ws.id}/transfer-ownership",
        json={"new_owner_id": str(user2.id), "new_role_id": str(viewer_role.id)},
    )

    assert response.status_code == 200
    assert response.json()["data"]["owner_id"] == str(user2.id)

    await async_db.refresh(ws)
    await async_db.refresh(mem1)
    await async_db.refresh(mem2)

    assert ws.owner_id == user2.id
    assert mem1.role_id == viewer_role.id
    assert mem2.role_id == owner_role.id
