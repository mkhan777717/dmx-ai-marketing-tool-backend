import pytest
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.workspace import Workspace
from app.constants.enums import WorkspaceStatus

@pytest.mark.asyncio
async def test_workspace_creation_and_relationships(async_db: AsyncSession):
    # Create owner
    owner = User(email="owner@example.com", hashed_password="pw")
    async_db.add(owner)
    await async_db.commit()
    await async_db.refresh(owner)
    
    # Test model creation and relationship
    ws = Workspace(
        name="Test Workspace",
        slug="test-workspace",
        owner_id=owner.id,
        created_by=owner.id,
        status=WorkspaceStatus.ACTIVE
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)
    
    assert ws.id is not None
    assert ws.slug == "test-workspace"
    assert ws.owner_id == owner.id
    
    # Test slug uniqueness
    ws2 = Workspace(
        name="Another Workspace",
        slug="test-workspace", # duplicate
        owner_id=owner.id,
    )
    async_db.add(ws2)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()
