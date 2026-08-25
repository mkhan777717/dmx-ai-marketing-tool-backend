import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.constants.enums import ApiProvider
from app.integrations.oauth.models import ConnectionStatus
from app.integrations.sync.engine import sync_engine


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def workspace_id():
    return uuid.uuid4()


@pytest.fixture
def integration_connection(workspace_id):
    mock_conn = AsyncMock()
    mock_conn.workspace_id = workspace_id
    mock_conn.provider = "twitter"
    mock_conn.status = ConnectionStatus.CONNECTED
    mock_conn.access_token = "encrypted_access_token"
    mock_conn.refresh_token = "encrypted_refresh_token"
    mock_conn.expires_at = datetime.now(timezone.utc)
    return mock_conn


@pytest.fixture
def mock_twitter_connector():
    connector = AsyncMock()
    connector.sync.return_value = {
        "profile": {"id": "12345", "username": "testuser", "name": "Test User"},
        "records_synced": 1,
    }
    return connector


@pytest.mark.asyncio
@patch("app.integrations.sync.engine.social_account_repo")
@patch("app.integrations.sync.engine.secret_service")
@patch("app.integrations.sync.engine.integration_service")
@patch("app.integrations.sync.engine.integration_connection_repo")
async def test_twitter_sync_creates_social_account(
    mock_conn_repo,
    mock_int_service,
    mock_secret_service,
    mock_sa_repo,
    mock_db_session,
    workspace_id,
    integration_connection,
    mock_twitter_connector,
):
    """Test successful social account creation from Twitter sync."""
    mock_conn_repo.get_by_workspace_and_provider = AsyncMock(
        return_value=integration_connection
    )
    mock_int_service.get_connector_instance = AsyncMock(
        return_value=mock_twitter_connector
    )

    mock_sa_repo.get_all = AsyncMock(return_value=[])
    mock_sa_repo.create = AsyncMock()

    # Mock encryption/decryption
    mock_secret_service.decrypt_token.side_effect = lambda x: x.replace(
        "encrypted_", "decrypted_"
    )
    mock_secret_service.encrypt_token.side_effect = lambda x: x.replace(
        "decrypted_", "re_encrypted_"
    )

    payload = {"workspace_id": str(workspace_id), "provider": "twitter"}

    await sync_engine.execute_sync_job(mock_db_session, payload)

    mock_sa_repo.get_all.assert_called_once()
    mock_sa_repo.create.assert_called_once()

    created_obj = mock_sa_repo.create.call_args[1]["obj_in"]
    assert created_obj["workspace_id"] == workspace_id
    assert created_obj["provider"] == ApiProvider.TWITTER
    assert created_obj["account_id"] == "12345"
    assert created_obj["name"] == "testuser"
    assert created_obj["access_token"] == "re_encrypted_access_token"
    assert created_obj["refresh_token"] == "re_encrypted_refresh_token"
    assert created_obj["expires_at"] == integration_connection.expires_at
    assert created_obj["is_active"] is True


@pytest.mark.asyncio
@patch("app.integrations.sync.engine.social_account_repo")
@patch("app.integrations.sync.engine.secret_service")
@patch("app.integrations.sync.engine.integration_service")
@patch("app.integrations.sync.engine.integration_connection_repo")
async def test_twitter_sync_updates_existing_social_account(
    mock_conn_repo,
    mock_int_service,
    mock_secret_service,
    mock_sa_repo,
    mock_db_session,
    workspace_id,
    integration_connection,
    mock_twitter_connector,
):
    """Test successful social account update from Twitter sync."""
    mock_conn_repo.get_by_workspace_and_provider = AsyncMock(
        return_value=integration_connection
    )
    mock_int_service.get_connector_instance = AsyncMock(
        return_value=mock_twitter_connector
    )

    existing_account = AsyncMock()
    mock_sa_repo.get_all = AsyncMock(return_value=[existing_account])
    mock_sa_repo.update = AsyncMock()
    mock_sa_repo.create = AsyncMock()

    mock_secret_service.decrypt_token.side_effect = lambda x: f"dec_{x}"
    mock_secret_service.encrypt_token.side_effect = lambda x: f"enc_{x}"

    payload = {"workspace_id": str(workspace_id), "provider": "twitter"}

    await sync_engine.execute_sync_job(mock_db_session, payload)

    mock_sa_repo.get_all.assert_called_once()
    mock_sa_repo.update.assert_called_once()
    mock_sa_repo.create.assert_not_called()

    updated_obj = mock_sa_repo.update.call_args[1]["obj_in"]
    assert updated_obj["name"] == "testuser"
    assert updated_obj["access_token"] == "enc_dec_encrypted_access_token"
    assert updated_obj["refresh_token"] == "enc_dec_encrypted_refresh_token"
    assert updated_obj["is_active"] is True


@pytest.mark.asyncio
@patch("app.integrations.sync.engine.social_account_repo")
@patch("app.integrations.sync.engine.integration_service")
@patch("app.integrations.sync.engine.integration_connection_repo")
async def test_twitter_sync_missing_id_handled_safely(
    mock_conn_repo,
    mock_int_service,
    mock_sa_repo,
    mock_db_session,
    workspace_id,
    integration_connection,
):
    """Test that missing ID in profile doesn't crash or create bad data."""
    mock_conn_repo.get_by_workspace_and_provider = AsyncMock(
        return_value=integration_connection
    )

    mock_connector = AsyncMock()
    mock_connector.sync = AsyncMock(
        return_value={
            "profile": {"username": "testuser"},
            "records_synced": 0,
        }
    )
    mock_int_service.get_connector_instance = AsyncMock(return_value=mock_connector)

    mock_sa_repo.get_all = AsyncMock()
    mock_sa_repo.create = AsyncMock()
    mock_sa_repo.update = AsyncMock()

    payload = {"workspace_id": str(workspace_id), "provider": "twitter"}

    await sync_engine.execute_sync_job(mock_db_session, payload)

    mock_sa_repo.get_all.assert_not_called()
    mock_sa_repo.create.assert_not_called()
    mock_sa_repo.update.assert_not_called()
