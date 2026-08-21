import pytest
import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.sync.engine import SyncEngine
from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
from app.integrations.exceptions import OAuthTokenError
from app.integrations.connectors.facebook.exceptions import FacebookApiError
from app.integrations.oauth.service import integration_service


@pytest.mark.asyncio
async def test_sync_engine_marks_expired_on_oauth_error():
    db_mock = AsyncMock(spec=AsyncSession)
    workspace_id = uuid.uuid4()
    provider = "facebook"

    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        provider=provider,
        status=ConnectionStatus.CONNECTED,
        access_token="some_token",
    )

    payload = {
        "workspace_id": str(workspace_id),
        "provider": provider,
        "sync_type": "full",
    }

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
        ) as mock_get_conn,
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            new_callable=AsyncMock,
        ) as mock_get_connector,
        patch(
            "app.integrations.sync.engine.integration_connection_repo.update",
            new_callable=AsyncMock,
        ) as mock_update,
    ):

        mock_get_conn.return_value = mock_conn

        mock_connector = AsyncMock()
        mock_connector.sync.side_effect = OAuthTokenError(
            "Meta access token is invalid or expired."
        )
        mock_get_connector.return_value = mock_connector

        with pytest.raises(OAuthTokenError):
            await SyncEngine.execute_sync_job(db_mock, payload)

        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        assert kwargs["obj_in"]["status"] == ConnectionStatus.EXPIRED


@pytest.mark.asyncio
async def test_sync_engine_does_not_mark_expired_on_generic_error():
    db_mock = AsyncMock(spec=AsyncSession)
    workspace_id = uuid.uuid4()
    provider = "instagram"

    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        provider=provider,
        status=ConnectionStatus.CONNECTED,
        access_token="some_token",
    )

    payload = {
        "workspace_id": str(workspace_id),
        "provider": provider,
        "sync_type": "full",
    }

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
        ) as mock_get_conn,
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            new_callable=AsyncMock,
        ) as mock_get_connector,
        patch(
            "app.integrations.sync.engine.integration_connection_repo.update",
            new_callable=AsyncMock,
        ) as mock_update,
    ):

        mock_get_conn.return_value = mock_conn

        mock_connector = AsyncMock()
        mock_connector.sync.side_effect = FacebookApiError("Rate Limit Exceeded")
        mock_get_connector.return_value = mock_connector

        with pytest.raises(FacebookApiError):
            await SyncEngine.execute_sync_job(db_mock, payload)

        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_reconnect_restores_expired_connection():
    db_mock = AsyncMock(spec=AsyncSession)
    workspace_id = uuid.uuid4()
    provider = "facebook"

    # Simulate an existing connection that is currently EXPIRED
    expired_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        provider=provider,
        status=ConnectionStatus.EXPIRED,
        access_token="old_token",
    )

    with (
        patch(
            "app.integrations.oauth.service.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
        ) as mock_get_conn,
        patch(
            "app.integrations.oauth.service.integration_connection_repo.update",
            new_callable=AsyncMock,
        ) as mock_update,
        patch("app.integrations.oauth.service.ConnectorFactory.create"),
        patch("app.integrations.oauth.service.get_circuit_breaker") as mock_breaker,
        patch(
            "app.integrations.oauth.service.secret_service.encrypt_token",
            return_value="enc_new_tok",
        ),
    ):

        mock_get_conn.return_value = expired_conn

        # Mock connector and breaker behavior for successful OAuth
        mock_breaker.return_value.call = AsyncMock(
            return_value={"access_token": "new_token", "expires_at": None}
        )

        mock_update.return_value = expired_conn  # return mock obj

        await integration_service.connect_provider(
            db_mock, workspace_id, provider, auth_code="dummy_code"
        )

        # Verify it updated the existing connection and restored status
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        assert kwargs["obj_in"]["status"] == ConnectionStatus.CONNECTED
        assert kwargs["obj_in"]["access_token"] == "enc_new_tok"
