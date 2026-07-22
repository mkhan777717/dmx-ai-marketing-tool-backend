import pytest
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.organization import Organization
from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.notification import Notification

from app.constants.enums import ApiProvider

from app.repositories.api_key import api_key_repo
from app.repositories.audit_log import audit_log_repo
from app.repositories.notification import notification_repo


@pytest.fixture
async def setup_db_2f(async_db: AsyncSession):
    user = User(
        email="test2f@test.com",
        supabase_user_id=uuid.uuid4(),
    )

    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)

    organization = Organization(
        name="Test Organization",
        slug="test-org",
    )

    async_db.add(organization)
    await async_db.commit()
    await async_db.refresh(organization)

    return {
        "user": user,
        "organization": organization,
    }


@pytest.mark.asyncio
async def test_api_key_encryption(async_db: AsyncSession, setup_db_2f):
    organization_id = setup_db_2f["organization"].id

    api_key_data = {
        "organization_id": organization_id,
        "provider": ApiProvider.OPENAI,
        "key_name": "Test Key",
        "secret": "sk-1234567890abcdef",
    }

    key = await api_key_repo.create_api_key(async_db, api_key_data)

    assert key.id is not None
    assert key.encrypted_secret != "sk-1234567890abcdef"

    decrypted = api_key_repo.decrypt_secret(key.encrypted_secret)

    assert decrypted == "sk-1234567890abcdef"


@pytest.mark.asyncio
async def test_audit_log_jsonb(async_db: AsyncSession, setup_db_2f):
    organization_id = setup_db_2f["organization"].id

    log = AuditLog(
        organization_id=organization_id,
        action="UPDATE",
        resource="campaign",
        old_values={"status": "draft"},
        new_values={"status": "published"},
    )

    async_db.add(log)
    await async_db.commit()
    await async_db.refresh(log)

    assert log.old_values["status"] == "draft"

    logs = await audit_log_repo.get_by_organization(
        async_db,
        organization_id,
    )

    assert len(logs) == 1


@pytest.mark.asyncio
async def test_notification_read(async_db: AsyncSession, setup_db_2f):
    user_id = setup_db_2f["user"].id
    organization_id = setup_db_2f["organization"].id

    notification = Notification(
        organization_id=organization_id,
        user_id=user_id,
        title="Welcome",
        body="Welcome to the platform",
        data={"link": "/dashboard"},
    )

    async_db.add(notification)
    await async_db.commit()

    unread = await notification_repo.get_unread_for_user(
        async_db,
        user_id,
    )

    assert len(unread) == 1

    await notification_repo.mark_as_read(
        async_db,
        unread[0].id,
    )

    unread_after = await notification_repo.get_unread_for_user(
        async_db,
        user_id,
    )

    assert len(unread_after) == 0