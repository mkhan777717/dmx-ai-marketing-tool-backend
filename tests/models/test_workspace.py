import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import WorkspaceStatus
from app.models.user import User
from app.models.workspace import Workspace


@pytest.mark.asyncio
async def test_workspace_creation_and_relationships(async_db: AsyncSession):
    # Create owner
    owner = User(
        email=f"owner_{uuid.uuid4()}@example.com", supabase_user_id=uuid.uuid4()
    )
    async_db.add(owner)
    await async_db.commit()
    await async_db.refresh(owner)

    # Test model creation and relationship
    ws = Workspace(
        name="Test Workspace",
        slug=f"test-workspace-{uuid.uuid4()}",
        owner_id=owner.id,
        created_by=owner.id,
        status=WorkspaceStatus.ACTIVE,
    )
    async_db.add(ws)
    await async_db.commit()
    await async_db.refresh(ws)

    assert ws.id is not None
    assert ws.slug.startswith("test-workspace-")
    assert ws.owner_id == owner.id

    # Test slug uniqueness
    ws2 = Workspace(
        name="Another Workspace",
        slug="test-workspace",  # duplicate
        owner_id=owner.id,
    )
    async_db.add(ws2)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()
