import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.mixins import get_utc_now
from app.models.workspace import Workspace
from app.models.user_preference import UserPreference
from app.constants.enums import WorkspaceStatus

@pytest.mark.asyncio
async def test_user_creation_and_soft_delete(async_db: AsyncSession):
    # Test model creation
    user = User(
        email=f"test_{uuid.uuid4()}@example.com",
        supabase_user_id=uuid.uuid4(),
        first_name="Test",
        last_name="User"
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    
    assert user.id is not None
    assert user.email.startswith("test_")
    assert user.created_at is not None
    assert user.deleted_at is None
    
    # Test unique email constraint
    user_id = user.id
    user2 = User(
        email="test@example.com", # duplicate
        supabase_user_id=uuid.uuid4()
    )
    async_db.add(user2)
    with pytest.raises(IntegrityError):
        await async_db.commit()
    await async_db.rollback()

    # Test soft delete
    user = await async_db.get(User, user_id)
    user.deleted_at = get_utc_now()
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    assert user.deleted_at is not None

@pytest.mark.asyncio
async def test_user_preferences_jsonb(async_db: AsyncSession):
    user = User(email=f"test2_{uuid.uuid4()}@example.com", supabase_user_id=uuid.uuid4())
    async_db.add(user)
    await async_db.commit()
    
    pref = UserPreference(
        user_id=user.id,
        notification_preferences={"email": True, "sms": False},
        ai_preferences={"model": "gpt-4"}
    )
    async_db.add(pref)
    await async_db.commit()
    await async_db.refresh(pref)
    
    assert pref.notification_preferences["email"] is True
    assert pref.ai_preferences["model"] == "gpt-4"
