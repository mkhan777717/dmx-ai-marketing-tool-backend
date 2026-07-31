import uuid
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
def mock_notification_id():
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

    with patch(
        "app.api.dependencies.auth.workspace_member_repo.get_member", return_value=None
    ), patch(
        "app.api.dependencies.auth.workspace_repo.get_by_id",
        return_value=Workspace(id=mock_workspace_id, owner_id=mock_user_id),
    ):
        yield

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_notifications(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.notifications.NotificationService.get_unread"
    ) as mock_get:
        mock_get.return_value = []
        response = await async_client.get(
            f"/api/v1/notifications?workspace_id={mock_workspace_id}"
        )
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_mark_notification_as_read(
    async_client: AsyncClient,
    override_auth_deps,
    mock_notification_id,
    mock_user_id,
    mock_workspace_id,
):
    with patch(
        "app.api.v1.endpoints.notifications.NotificationService.get_by_id"
    ) as mock_get, patch(
        "app.api.v1.endpoints.notifications.NotificationService.mark_as_read"
    ) as mock_mark:

        class MockNotification:
            id = mock_notification_id
            workspace_id = mock_workspace_id
            user_id = mock_user_id
            read_at = None
            title = "Test"
            body = "Body"
            type = "SYSTEM"
            priority = "NORMAL"
            data = None
            created_at = "2023-01-01T00:00:00Z"

        mock_get.return_value = MockNotification()

        class MockResponse:
            id = mock_notification_id
            workspace_id = mock_workspace_id
            user_id = mock_user_id
            read_at = "2023-01-01T00:00:00Z"
            title = "Test"
            body = "Body"
            type = "SYSTEM"
            priority = "NORMAL"
            data = None
            created_at = "2023-01-01T00:00:00Z"

        mock_mark.return_value = MockResponse()

        response = await async_client.patch(
            f"/api/v1/notifications/{mock_notification_id}/read?workspace_id={mock_workspace_id}"
        )

        assert response.status_code == 200


@pytest.mark.asyncio
async def test_mark_all_read(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.notifications.NotificationService.mark_all_as_read"
    ) as mock_mark_all:
        mock_mark_all.return_value = 5
        response = await async_client.patch(
            f"/api/v1/notifications/read-all?workspace_id={mock_workspace_id}"
        )
        assert response.status_code == 200
        assert "5 notifications" in response.json()["message"]
