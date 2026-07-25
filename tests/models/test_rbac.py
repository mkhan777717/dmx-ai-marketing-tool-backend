import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.constants.enums import RoleType
from app.repositories.rbac import role_repo, role_permission_repo

@pytest.mark.asyncio
async def test_permission_uniqueness(async_db: AsyncSession):
    suffix = str(uuid.uuid4())[:8]
    perm1 = Permission(name=f"test_{suffix}.read", resource=f"test_{suffix}", action="read")
    async_db.add(perm1)
    await async_db.commit()
    
    # Test duplicate name
    perm2 = Permission(name=f"test_{suffix}.read", resource="other", action="other")
    async_db.add(perm2)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()
    
    # Test duplicate resource+action
    perm3 = Permission(name=f"other_{suffix}.read", resource=f"test_{suffix}", action="read")
    async_db.add(perm3)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()

@pytest.mark.asyncio
async def test_role_and_assignment(async_db: AsyncSession):
    suffix = str(uuid.uuid4())[:8]
    # Create role
    role = Role(name=f"CustomRole_{suffix}", role_type=RoleType.CUSTOM, is_system=False)
    async_db.add(role)
    
    # Create perm
    perm = Permission(name=f"module_{suffix}.write", resource=f"module_{suffix}", action="write")
    async_db.add(perm)
    await async_db.commit()
    await async_db.refresh(role)
    await async_db.refresh(perm)
    
    # Assign perm
    rp = await role_permission_repo.assign_permission(async_db, role.id, perm.id)
    assert rp is not None
    
    # Check duplicate assignment
    rp_dup = await role_permission_repo.assign_permission(async_db, role.id, perm.id)
    assert rp_dup is None
    
    # Check get_role_permissions
    perms = await role_permission_repo.get_role_permissions(async_db, role.id)
    assert len(perms) == 1
    assert perms[0].name == f"module_{suffix}.write"
    
    # Remove perm
    removed = await role_permission_repo.remove_permission(async_db, role.id, perm.id)
    assert removed is True
    
    perms_after = await role_permission_repo.get_role_permissions(async_db, role.id)
    assert len(perms_after) == 0

@pytest.mark.asyncio
async def test_clone_system_role(async_db: AsyncSession):
    suffix = str(uuid.uuid4())[:8]
    # Setup system role
    sys_role = Role(name=f"SysAdmin_{suffix}", role_type=RoleType.SYSTEM, is_system=True)
    async_db.add(sys_role)
    perm = Permission(name=f"sys_{suffix}.read", resource=f"sys_{suffix}", action="read")
    async_db.add(perm)
    await async_db.commit()
    
    await role_permission_repo.assign_permission(async_db, sys_role.id, perm.id)
    
    # Clone it
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.constants.enums import WorkspaceStatus
    
    owner = User(email=f"owner_{suffix}@test.com", supabase_user_id=uuid.uuid4())
    async_db.add(owner)
    await async_db.commit()
    
    ws = Workspace(name="Test WS", slug=f"test-ws-{suffix}", owner_id=owner.id, status=WorkspaceStatus.ACTIVE)
    async_db.add(ws)
    await async_db.commit()
    
    ws_id = ws.id
    cloned = await role_repo.clone_system_role_to_workspace(async_db, sys_role.id, ws_id, "ClonedAdmin")
    
    assert cloned is not None
    assert cloned.workspace_id == ws_id
    assert cloned.is_system is False
    assert cloned.role_type == RoleType.CUSTOM
    
    # Check perms were cloned
    cloned_perms = await role_permission_repo.get_role_permissions(async_db, cloned.id)
    assert len(cloned_perms) == 1
    assert cloned_perms[0].id == perm.id
