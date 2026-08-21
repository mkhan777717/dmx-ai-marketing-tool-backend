import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ApiProvider
from app.integrations.sync.engine import SyncEngine


@pytest.fixture
def mock_db():
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def workspace_id():
    return uuid.uuid4()


@pytest.fixture
def mock_connection():
    from app.integrations.oauth.models import IntegrationConnection

    conn = MagicMock(spec=IntegrationConnection)
    conn.access_token = "encrypted_access"
    conn.refresh_token = "encrypted_refresh"
    conn.expires_at = None
    return conn


@pytest.mark.asyncio
async def test_google_sync_creates_social_accounts(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
        "sync_type": "full",
    }

    sync_result = {
        "business_accounts": [
            {
                "account_id": "111",
                "account_name": "Test Account 1",
                "locations": [
                    {
                        "location_id": "222",
                        "location_name": "Location 222",
                    },
                    {
                        "location_id": "333",
                        "location_name": "Location 333",
                    },
                ],
            }
        ]
    }

    mock_connector = AsyncMock()
    mock_connector.sync.return_value = sync_result

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_connection,
        ),
        patch(
            "app.integrations.oauth.service.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted",
        ),
        patch(
            "app.integrations.secrets.service.secret_service.encrypt_token",
            return_value="encrypted_again",
        ),
        patch(
            "app.repositories.social_account.social_account_repo.get_all",
            return_value=[],
        ) as mock_get_all,
        patch(
            "app.repositories.social_account.social_account_repo.create"
        ) as mock_create,
        patch(
            "app.repositories.social_account.social_account_repo.update"
        ) as mock_update,
    ):

        result = await SyncEngine.execute_sync_job(mock_db, payload)

        assert result == sync_result
        assert mock_get_all.call_count == 2
        assert mock_create.call_count == 2
        assert mock_update.call_count == 0

        # Verify the created accounts use the proper resource name format
        create_calls = mock_create.call_args_list
        created_obj_1 = create_calls[0].kwargs["obj_in"]
        assert created_obj_1["account_id"] == "accounts/111/locations/222"
        assert created_obj_1["name"] == "Location 222"
        assert created_obj_1["provider"] == ApiProvider.GOOGLE
        assert created_obj_1["workspace_id"] == workspace_id
        assert created_obj_1["access_token"] == "encrypted_again"


@pytest.mark.asyncio
async def test_google_sync_updates_existing_social_accounts(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {
        "business_accounts": [
            {
                "account_id": "111",
                "locations": [
                    {
                        "location_id": "222",
                        "location_name": "Updated Location Name",
                    }
                ],
            }
        ]
    }

    mock_connector = AsyncMock()
    mock_connector.sync.return_value = sync_result

    existing_account = MagicMock()

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_connection,
        ),
        patch(
            "app.integrations.oauth.service.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted",
        ),
        patch(
            "app.integrations.secrets.service.secret_service.encrypt_token",
            return_value="encrypted_again",
        ),
        patch(
            "app.repositories.social_account.social_account_repo.get_all",
            return_value=[existing_account],
        ) as mock_get_all,
        patch(
            "app.repositories.social_account.social_account_repo.create"
        ) as mock_create,
        patch(
            "app.repositories.social_account.social_account_repo.update"
        ) as mock_update,
    ):

        await SyncEngine.execute_sync_job(mock_db, payload)

        assert mock_get_all.call_count == 1
        assert mock_create.call_count == 0
        assert mock_update.call_count == 1

        update_calls = mock_update.call_args_list
        updated_obj = update_calls[0].kwargs["obj_in"]
        assert updated_obj["name"] == "Updated Location Name"
        assert updated_obj["access_token"] == "encrypted_again"
        assert updated_obj["is_active"] is True


@pytest.mark.asyncio
async def test_google_sync_missing_location_id_handled_safely(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {
        "business_accounts": [
            {
                "account_id": "111",
                "locations": [
                    {
                        "location_name": "Missing ID",
                        # no location_id
                    }
                ],
            }
        ]
    }

    mock_connector = AsyncMock()
    mock_connector.sync.return_value = sync_result

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_connection,
        ),
        patch(
            "app.integrations.oauth.service.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch("app.integrations.secrets.service.secret_service.decrypt_token"),
        patch("app.integrations.secrets.service.secret_service.encrypt_token"),
        patch(
            "app.repositories.social_account.social_account_repo.get_all"
        ) as mock_get_all,
        patch(
            "app.repositories.social_account.social_account_repo.create"
        ) as mock_create,
    ):

        await SyncEngine.execute_sync_job(mock_db, payload)

        # Should skip creating or querying if location_id is missing
        assert mock_get_all.call_count == 0
        assert mock_create.call_count == 0
