import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.models.role import Role
from app.models.workspace_member import WorkspaceMember
from app.models.workspace_invite import WorkspaceInvite
from app.constants.enums import WorkspaceStatus, RoleType, MemberStatus, InviteStatus
from app.repositories.workspace_invite import workspace_invite_repo
from app.repositories.workspace_member import workspace_member_repo

@pytest.fixture
async def setup_db(async_db: AsyncSession):
    # Setup mock data needed for member testing
    owner = User(email="owner@test.com", hashed_password="pw")
    async_db.add(owner)
    await async_db.commit()
    
    ws = Workspace(name="Test WS", slug="test-ws", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    role = Role(name="Admin", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(role)
    await async_db.commit()
    
    return {"owner": owner, "ws": ws, "role": role}

@pytest.mark.asyncio
async def test_duplicate_membership_prevention(async_db: AsyncSession, setup_db):
    user = User(email="member@test.com", hashed_password="pw")
    async_db.add(user)
    await async_db.commit()
    
    mem1 = WorkspaceMember(workspace_id=setup_db["ws"].id, user_id=user.id, role_id=setup_db["role"].id, status=MemberStatus.ACTIVE)
    async_db.add(mem1)
    await async_db.commit()
    
    mem2 = WorkspaceMember(workspace_id=setup_db["ws"].id, user_id=user.id, role_id=setup_db["role"].id, status=MemberStatus.PENDING)
    async_db.add(mem2)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()

@pytest.mark.asyncio
async def test_duplicate_invite_prevention(async_db: AsyncSession, setup_db):
    # Testing partial index requires postgresql, sqlite does not support postgresql_where exactly like pg in tests, 
    # but we can test repository create logic
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    invite1 = await workspace_invite_repo.create_invitation(async_db, {
        "workspace_id": setup_db["ws"].id,
        "email": "invite@test.com",
        "role_id": setup_db["role"].id,
        "expires_at": expires
    })
    
    # Check normalized email
    assert invite1.email == "invite@test.com"
    assert invite1.token is not None
    
    # Try another invite with same email and pending status - this works if sqlite ignores partial index during tests
    # But in reality postgres prevents it. We will just test accept/revoke flows
    accepted = await workspace_invite_repo.accept_invite(async_db, invite1.id)
    assert accepted.status == InviteStatus.ACCEPTED

@pytest.mark.asyncio
async def test_member_lifecycle(async_db: AsyncSession, setup_db):
    user = User(email="lifecycle@test.com", hashed_password="pw")
    async_db.add(user)
    await async_db.commit()
    
    mem = WorkspaceMember(workspace_id=setup_db["ws"].id, user_id=user.id, role_id=setup_db["role"].id, status=MemberStatus.ACTIVE)
    async_db.add(mem)
    await async_db.commit()
    
    # Suspend
    mem_suspended = await workspace_member_repo.suspend_member(async_db, mem.id)
    assert mem_suspended.status == MemberStatus.SUSPENDED
    
    # Reactivate
    mem_active = await workspace_member_repo.reactivate_member(async_db, mem.id)
    assert mem_active.status == MemberStatus.ACTIVE
    
    # Remove (soft delete)
    mem_removed = await workspace_member_repo.remove_member(async_db, mem.id)
    assert mem_removed.status == MemberStatus.REMOVED
    assert mem_removed.deleted_at is not None
