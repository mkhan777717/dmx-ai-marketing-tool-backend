import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime, timezone, timedelta

from app.services.campaign_scheduler import campaign_scheduler_service
from app.schemas.campaign_schedule import CampaignScheduleCreate
from app.constants.enums import ScheduleStatus

@pytest.fixture
def mock_campaign_id():
    return uuid.uuid4()

@pytest.fixture
def mock_workspace_id():
    return uuid.uuid4()

@pytest.fixture
def mock_user_id():
    return uuid.uuid4()

@pytest.mark.asyncio
@patch("app.services.campaign_scheduler.campaign_schedule_repo")
@patch("app.services.campaign_scheduler.audit_log_repo")
async def test_schedule_campaign_new(mock_audit_repo, mock_schedule_repo, mock_campaign_id, mock_workspace_id, mock_user_id):
    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = "DRAFT"
    mock_db.execute.return_value = mock_db_result
    
    mock_audit_repo.create = AsyncMock()
    mock_schedule_repo.get_by_campaign_id = AsyncMock(return_value=None)
    
    mock_created = AsyncMock()
    mock_created.id = uuid.uuid4()
    mock_created.status = ScheduleStatus.SCHEDULED
    mock_schedule_repo.create = AsyncMock(return_value=mock_created)
    
    schedule_data = CampaignScheduleCreate(publish_date=datetime.now(timezone.utc) + timedelta(minutes=5), timezone="UTC")
    
    result = await campaign_scheduler_service.schedule_campaign(
        mock_db, mock_campaign_id, schedule_data, mock_workspace_id, mock_user_id
    )
    
    mock_schedule_repo.create.assert_called_once()
    mock_audit_repo.create.assert_called_once()
    assert result.status == ScheduleStatus.SCHEDULED

@pytest.mark.asyncio
@patch("app.services.campaign_scheduler.campaign_schedule_repo")
@patch("app.services.campaign_scheduler.audit_log_repo")
async def test_pause_schedule(mock_audit_repo, mock_schedule_repo, mock_campaign_id, mock_workspace_id, mock_user_id):
    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.scalar_one_or_none.return_value = "DRAFT"
    mock_db.execute.return_value = mock_db_result
    
    mock_audit_repo.create = AsyncMock()
    
    mock_existing = AsyncMock()
    mock_existing.status = ScheduleStatus.SCHEDULED
    mock_schedule_repo.get_by_campaign_id = AsyncMock(return_value=mock_existing)
    
    mock_updated = AsyncMock()
    mock_updated.status = ScheduleStatus.PAUSED
    mock_schedule_repo.update = AsyncMock(return_value=mock_updated)
    
    result = await campaign_scheduler_service.pause_schedule(
        mock_db, mock_campaign_id, mock_workspace_id, mock_user_id
    )
    
    mock_schedule_repo.update.assert_called_once()
    mock_audit_repo.create.assert_called_once()
    assert result.status == ScheduleStatus.PAUSED
