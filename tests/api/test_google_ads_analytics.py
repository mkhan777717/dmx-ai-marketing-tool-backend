import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_user, get_current_workspace
from app.integrations.connectors.google.exceptions import (
    GoogleAuthError,
    GoogleQuotaError,
)
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
async def test_get_google_ads_report_success(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_customer_id = "1234567890"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "google_ads_customers": [
                {
                    "customer_id": test_customer_id,
                    "resource_name": f"customers/{test_customer_id}",
                    "descriptive_name": f"Customer {test_customer_id}",
                }
            ]
        },
    )

    mock_report = {
        "customer_id": test_customer_id,
        "resource_name": f"customers/{test_customer_id}",
        "query": "SELECT campaign.id FROM campaign",
        "rows": [
            {
                "campaign_id": "101",
                "campaign_name": "Spring Sale",
                "status": "ENABLED",
                "impressions": 1000,
                "clicks": 50,
                "cost_micros": 5000000,
                "cost": 5.0,
            }
        ],
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
            "app.integrations.connectors.google.ads.GoogleAdsService.get_report",
            new_callable=AsyncMock,
            return_value=mock_report,
        ) as mock_get_report,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id={test_customer_id}&start_date=2026-08-01&end_date=2026-09-01"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["customer_id"] == test_customer_id
        assert data["data"]["rows"][0]["campaign_name"] == "Spring Sale"
        assert data["data"]["rows"][0]["cost"] == 5.0

        mock_get_report.assert_called_once()
        _, kwargs = mock_get_report.call_args
        assert kwargs["customer_id"] == test_customer_id
        assert kwargs["start_date"] == "2026-08-01"
        assert kwargs["end_date"] == "2026-09-01"


@pytest.mark.asyncio
async def test_get_google_ads_report_uses_metadata_login_customer_id(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_client_id = "8109628125"
    test_manager_id = "6774894805"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "google_ads_customers": [
                {
                    "customer_id": test_client_id,
                    "resource_name": f"customers/{test_client_id}",
                    "descriptive_name": "NEW DMX Test Client",
                    "login_customer_id": test_manager_id,
                }
            ]
        },
    )

    mock_report = {
        "customer_id": test_client_id,
        "resource_name": f"customers/{test_client_id}",
        "query": "SELECT campaign.id FROM campaign",
        "rows": [],
        "row_count": 0,
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
            "app.integrations.connectors.google.ads.GoogleAdsService.get_report",
            new_callable=AsyncMock,
            return_value=mock_report,
        ) as mock_get_report,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id={test_client_id}"
        )

        assert response.status_code == 200
        mock_get_report.assert_called_once()
        _, kwargs = mock_get_report.call_args
        assert kwargs["login_customer_id"] == test_manager_id


@pytest.mark.asyncio
async def test_get_google_ads_report_connection_missing_404(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=None,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id=1234567890"
        )

        assert response.status_code == 404
        assert "Google integration connection not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_google_ads_report_disconnected_404(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.DISCONNECTED,
        access_token="enc_token",
    )

    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=mock_conn,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id=1234567890"
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_google_ads_report_no_persisted_customers_400(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"google_ads_customers": []},
    )

    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=mock_conn,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id=1234567890"
        )

        assert response.status_code == 400
        assert "No Google Ads customers discovered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_google_ads_report_unauthorized_customer_403(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "google_ads_customers": [
                {
                    "customer_id": "9999999999",
                    "resource_name": "customers/9999999999",
                }
            ]
        },
    )

    with (
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_conn,
        ),
        patch(
            "app.integrations.connectors.google.ads.GoogleAdsService.get_report",
            new_callable=AsyncMock,
        ) as mock_get_report,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id=1234567890"
        )

        assert response.status_code == 403
        assert "does not belong to this workspace" in response.json()["detail"]
        mock_get_report.assert_not_called()


@pytest.mark.asyncio
async def test_get_google_ads_report_auth_error_401(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_customer_id = "1234567890"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"google_ads_customers": [{"customer_id": test_customer_id}]},
    )

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
            "app.integrations.connectors.google.ads.GoogleAdsService.get_report",
            new_callable=AsyncMock,
            side_effect=GoogleAuthError("Token expired"),
        ),
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id={test_customer_id}"
        )

        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_google_ads_report_quota_error_429(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_customer_id = "1234567890"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"google_ads_customers": [{"customer_id": test_customer_id}]},
    )

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
            "app.integrations.connectors.google.ads.GoogleAdsService.get_report",
            new_callable=AsyncMock,
            side_effect=GoogleQuotaError("Rate limit exceeded"),
        ),
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/google-ads/report?customer_id={test_customer_id}"
        )

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
