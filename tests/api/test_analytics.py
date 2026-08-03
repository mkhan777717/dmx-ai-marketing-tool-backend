import uuid
from datetime import date
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_user, get_current_workspace
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
async def test_get_dashboard(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.analytics.DashboardService.get_dashboard_overview"
    ) as mock_dash:
        mock_dash.return_value = {
            "workspace_id": mock_workspace_id,
            "date": date.today(),
            "campaign_metrics": {"total_campaigns": 5},
            "ai_metrics": {"total_generations": 10},
            "publishing_metrics": {"published_posts": 3},
            "workspace_metrics": {"members": 2},
        }

        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/dashboard"
        )

        assert response.status_code == 200
        assert response.json()["campaign_metrics"]["total_campaigns"] == 5
        assert response.json()["workspace_id"] == str(mock_workspace_id)


@pytest.mark.asyncio
async def test_get_overview(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.analytics.AnalyticsService.get_latest_snapshot"
    ) as mock_snap:
        from datetime import datetime, timezone

        from app.constants.enums import SnapshotType
        from app.models.analytics_snapshot import AnalyticsSnapshot

        mock_snap.return_value = AnalyticsSnapshot(
            id=uuid.uuid4(),
            workspace_id=mock_workspace_id,
            snapshot_type=SnapshotType.DAILY,
            snapshot_date=date.today(),
            campaign_metrics={"total_campaigns": 5},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/overview"
        )

        assert response.status_code == 200
        assert response.json()["snapshot_type"] == "DAILY"


@pytest.mark.asyncio
async def test_list_campaigns(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.analytics.campaign_analytics_repo.get_by_workspace_id"
    ) as mock_list:
        mock_list.return_value = []
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/campaigns"
        )
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_list_ai_usage(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.analytics.ai_usage_repo.get_by_workspace_id"
    ) as mock_list:
        mock_list.return_value = []
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/analytics/ai"
        )
        assert response.status_code == 200
        assert response.json() == []
