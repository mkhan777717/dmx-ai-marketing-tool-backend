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
async def test_get_search_console_report_success(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_site_url = "https://example.com/"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "search_console_sites": [
                {
                    "site_url": test_site_url,
                    "permission_level": "siteOwner",
                }
            ]
        },
    )

    mock_report = {
        "site_url": test_site_url,
        "start_date": "2026-08-01",
        "end_date": "2026-09-01",
        "dimensions": ["query"],
        "rows": [
            {
                "keys": ["dmx ai marketing"],
                "clicks": 150,
                "impressions": 4000,
                "ctr": 0.0375,
                "position": 1.8,
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
            "app.integrations.connectors.google.search_console.GoogleSearchConsoleService.get_search_analytics",
            new_callable=AsyncMock,
            return_value=mock_report,
        ) as mock_get_analytics,
    ):
        import urllib.parse

        encoded_url = urllib.parse.quote(test_site_url, safe="")
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url={encoded_url}&start_date=2026-08-01&end_date=2026-09-01"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["site_url"] == test_site_url
        assert data["data"]["rows"][0]["keys"] == ["dmx ai marketing"]
        assert data["data"]["rows"][0]["clicks"] == 150

        mock_get_analytics.assert_called_once()
        _, kwargs = mock_get_analytics.call_args
        assert kwargs["site_url"] == test_site_url
        assert kwargs["start_date"] == "2026-08-01"
        assert kwargs["end_date"] == "2026-09-01"


@pytest.mark.asyncio
async def test_get_search_console_report_connection_missing_404(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=None,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url=https://example.com/"
        )

        assert response.status_code == 404
        assert "Google integration connection not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_search_console_report_disconnected_404(
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
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url=https://example.com/"
        )

        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_search_console_report_no_persisted_sites_400(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"search_console_sites": []},
    )

    with patch(
        "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
        return_value=mock_conn,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url=https://example.com/"
        )

        assert response.status_code == 400
        assert "No Search Console sites discovered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_search_console_report_unauthorized_site_403(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={
            "search_console_sites": [
                {
                    "site_url": "https://otherdomain.com/",
                    "permissionLevel": "siteOwner",
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
            "app.integrations.connectors.google.search_console.GoogleSearchConsoleService.get_search_analytics",
            new_callable=AsyncMock,
        ) as mock_get_analytics,
    ):
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url=https://unauthorized.com/"
        )

        assert response.status_code == 403
        assert "does not belong to this workspace" in response.json()["detail"]
        mock_get_analytics.assert_not_called()


@pytest.mark.asyncio
async def test_get_search_console_report_auth_error_401(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_site_url = "https://example.com/"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"search_console_sites": [{"site_url": test_site_url}]},
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
            "app.integrations.connectors.google.search_console.GoogleSearchConsoleService.get_search_analytics",
            new_callable=AsyncMock,
            side_effect=GoogleAuthError("Token expired"),
        ),
    ):
        import urllib.parse

        encoded_url = urllib.parse.quote(test_site_url, safe="")
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url={encoded_url}"
        )

        assert response.status_code == 401
        assert "Token expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_search_console_report_quota_error_429(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    test_site_url = "https://example.com/"
    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        provider="google",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_token",
        metadata_info={"search_console_sites": [{"site_url": test_site_url}]},
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
            "app.integrations.connectors.google.search_console.GoogleSearchConsoleService.get_search_analytics",
            new_callable=AsyncMock,
            side_effect=GoogleQuotaError("Rate limit exceeded"),
        ),
    ):
        import urllib.parse

        encoded_url = urllib.parse.quote(test_site_url, safe="")
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url={encoded_url}"
        )

        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_search_console_report_row_limit_validation(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    response = await async_client.get(
        f"/api/v1/workspaces/{mock_workspace_id}/analytics/search-console/report?site_url=https://example.com/&row_limit=0"
    )
    assert response.status_code == 422  # Validation error (ge=1)
