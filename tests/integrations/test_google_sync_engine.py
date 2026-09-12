import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
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


@pytest.mark.asyncio
async def test_youtube_sync_creates_social_account(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {
        "business_accounts": [],
        "youtube_channels": [
            {
                "channel_id": "UC_youtube_123",
                "title": "Test YouTube Channel",
                "custom_url": "@testchannel",
                "thumbnail_url": "https://example.com/thumb.jpg",
                "description": "Channel description",
            }
        ],
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
        await SyncEngine.execute_sync_job(mock_db, payload)

        assert mock_get_all.call_count == 1
        assert mock_create.call_count == 1
        assert mock_update.call_count == 0

        create_args = mock_create.call_args.kwargs["obj_in"]
        assert create_args["provider"] == ApiProvider.YOUTUBE
        assert create_args["account_id"] == "UC_youtube_123"
        assert create_args["name"] == "Test YouTube Channel"
        assert create_args["workspace_id"] == workspace_id
        assert create_args["access_token"] == "encrypted_again"
        assert create_args["is_active"] is True


@pytest.mark.asyncio
async def test_youtube_sync_updates_existing_social_account(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "youtube",
    }

    sync_result = {
        "youtube_channels": [
            {
                "channel_id": "UC_youtube_123",
                "title": "Updated YouTube Title",
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

        update_args = mock_update.call_args.kwargs["obj_in"]
        assert update_args["name"] == "Updated YouTube Title"
        assert update_args["access_token"] == "encrypted_again"
        assert update_args["is_active"] is True


@pytest.mark.asyncio
async def test_youtube_sync_empty_channels_creates_nothing(
    mock_db, workspace_id, mock_connection
):
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "youtube",
    }

    sync_result = {"youtube_channels": []}

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
            "app.repositories.social_account.social_account_repo.get_all"
        ) as mock_get_all,
        patch(
            "app.repositories.social_account.social_account_repo.create"
        ) as mock_create,
    ):
        await SyncEngine.execute_sync_job(mock_db, payload)

        assert mock_get_all.call_count == 0
        assert mock_create.call_count == 0


@pytest.mark.asyncio
async def test_google_sync_persists_ga4_properties(
    mock_db, workspace_id, mock_connection
):
    mock_connection.metadata_info = {"existing_setting": "enabled"}
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {
        "ga4_properties": [
            {
                "property_id": "987654",
                "property_name": "properties/987654",
                "display_name": "Main GA4 Property",
                "account_id": "12345",
                "account_name": "Test Company",
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
            "app.integrations.oauth.repository.integration_connection_repo.update"
        ) as mock_conn_update,
    ):
        result = await SyncEngine.execute_sync_job(mock_db, payload)

        assert result == sync_result
        assert mock_conn_update.call_count == 1

        update_kwargs = mock_conn_update.call_args.kwargs["obj_in"]
        assert "metadata_info" in update_kwargs
        meta = update_kwargs["metadata_info"]
        assert meta["existing_setting"] == "enabled"  # Preserves existing metadata
        assert len(meta["ga4_properties"]) == 1
        assert meta["ga4_properties"][0]["property_id"] == "987654"
        assert meta["ga4_properties"][0]["display_name"] == "Main GA4 Property"


@pytest.mark.asyncio
async def test_google_sync_zero_ga4_properties_handles_cleanly(
    mock_db, workspace_id, mock_connection
):
    mock_connection.metadata_info = None
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {"ga4_properties": []}

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
            "app.integrations.oauth.repository.integration_connection_repo.update"
        ) as mock_conn_update,
    ):
        result = await SyncEngine.execute_sync_job(mock_db, payload)

        assert result == sync_result
        assert mock_conn_update.call_count == 1

        update_kwargs = mock_conn_update.call_args.kwargs["obj_in"]
        assert update_kwargs["metadata_info"]["ga4_properties"] == []


@pytest.mark.asyncio
async def test_google_sync_persists_google_ads_customers(
    mock_db, workspace_id, mock_connection
):
    mock_connection.metadata_info = {
        "author_id": "user123",
        "ga4_properties": [{"property_id": "987654"}],
    }
    payload = {
        "workspace_id": str(workspace_id),
        "provider": "google",
    }

    sync_result = {
        "google_ads_customers": [
            {
                "customer_id": "1234567890",
                "resource_name": "customers/1234567890",
                "descriptive_name": "Customer 1234567890",
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
            "app.integrations.oauth.repository.integration_connection_repo.update"
        ) as mock_conn_update,
    ):
        result = await SyncEngine.execute_sync_job(mock_db, payload)

        assert result == sync_result
        assert mock_conn_update.call_count == 1

        update_kwargs = mock_conn_update.call_args.kwargs["obj_in"]
        assert "metadata_info" in update_kwargs
        meta = update_kwargs["metadata_info"]
        # Verify existing keys preserved
        assert meta["author_id"] == "user123"
        assert meta["ga4_properties"] == [{"property_id": "987654"}]
        # Verify google_ads_customers persisted
        assert len(meta["google_ads_customers"]) == 1
        assert meta["google_ads_customers"][0]["customer_id"] == "1234567890"
        assert (
            meta["google_ads_customers"][0]["resource_name"] == "customers/1234567890"
        )
