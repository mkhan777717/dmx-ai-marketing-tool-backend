import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_user, get_current_workspace
from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace


@pytest.fixture
def mock_workspace_id():
    return uuid.uuid4()


@pytest.fixture
def mock_user_id():
    return uuid.uuid4()


@pytest.fixture
def override_auth_deps(mock_user_id, mock_workspace_id):
    def override_get_current_user():
        user = User(id=mock_user_id, email="test@example.com")
        return user

    def override_get_current_workspace():
        ws = Workspace(id=mock_workspace_id, name="Test Workspace")
        return ws

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_workspace] = override_get_current_workspace

    with (
        patch(
            "app.api.dependencies.auth.workspace_member_repo.get_member",
            return_value=None,
        ),
        patch(
            "app.api.dependencies.auth.workspace_repo.get_by_id",
            return_value=Workspace(id=mock_workspace_id, owner_id=mock_user_id),
        ),
    ):
        yield

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_ga4_report_success(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "ga4_properties": [
                {
                    "property_id": "987654",
                    "property_name": "properties/987654",
                    "display_name": "Main GA4 Property",
                }
            ]
        },
    )

    mock_report = {
        "property_id": "987654",
        "property_name": "properties/987654",
        "dimension_headers": ["date"],
        "metric_headers": [{"name": "activeUsers", "type": "TYPE_INTEGER"}],
        "rows": [{"dimension_values": ["20260901"], "metric_values": ["150"]}],
        "row_count": 1,
    }

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_conn,
        ),
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="dec_token",
        ),
        patch(
            "app.integrations.connectors.google.analytics.GoogleAnalyticsService.get_report",
            new_callable=AsyncMock,
            return_value=mock_report,
        ),
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/ga4/report?property_id=987654"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["property_id"] == "987654"
        assert data["data"]["rows"][0]["metric_values"] == ["150"]


@pytest.mark.asyncio
async def test_get_ga4_report_connection_missing_404(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=None,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/ga4/report?property_id=987654"
        )

        assert response.status_code == 404
        assert "Google integration connection not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_ga4_report_no_persisted_properties_400(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"ga4_properties": []},
    )

    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=mock_conn,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/ga4/report?property_id=987654"
        )

        assert response.status_code == 400
        assert "No GA4 properties discovered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_ga4_report_unauthorized_property_403(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "ga4_properties": [
                {
                    "property_id": "111111",
                    "property_name": "properties/111111",
                    "display_name": "Other Property",
                }
            ]
        },
    )

    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=mock_conn,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/ga4/report?property_id=987654"
        )

        assert response.status_code == 403
        assert "does not belong to this workspace" in response.json()["detail"]
