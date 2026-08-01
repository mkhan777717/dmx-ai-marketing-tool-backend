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
def mock_content_id():
    return uuid.uuid4()


@pytest.fixture
def mock_account_id():
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
async def test_connect_social_account(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.social_accounts.SocialAccountService.connect_account"
    ) as mock_connect:
        from datetime import datetime, timezone

        from app.constants.enums import ApiProvider
        from app.models.social_account import SocialAccount

        mock_acc = SocialAccount(
            id=uuid.uuid4(),
            workspace_id=mock_workspace_id,
            provider=ApiProvider.MOCK,
            account_id="mock_acc_123",
            name="Mock Social Account",
            access_token="mock_token",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_connect.return_value = mock_acc

        payload = {"provider": "MOCK", "oauth_code": "dummy_auth_code"}

        response = await async_client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/social-accounts/connect",
            json=payload,
        )

        assert response.status_code == 201
        assert response.json()["provider"] == "MOCK"
        assert response.json()["account_id"] == "mock_acc_123"


@pytest.mark.asyncio
async def test_publish_content(
    async_client: AsyncClient,
    override_auth_deps,
    mock_workspace_id,
    mock_content_id,
    mock_account_id,
):
    with patch(
        "app.api.v1.endpoints.publishing.PublishingService.publish_content"
    ) as mock_publish:
        from datetime import datetime, timezone

        from app.constants.enums import PublishStatus
        from app.models.publish_history import PublishHistory

        mock_history = PublishHistory(
            id=uuid.uuid4(),
            workspace_id=mock_workspace_id,
            content_id=mock_content_id,
            social_account_id=mock_account_id,
            status=PublishStatus.PUBLISHED,
            external_post_id="ext_post_123",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_publish.return_value = mock_history

        payload = {
            "content_id": str(mock_content_id),
            "social_account_id": str(mock_account_id),
        }

        response = await async_client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/publishing/publish", json=payload
        )

        assert response.status_code == 200
        assert response.json()["status"] == "PUBLISHED"
        assert response.json()["external_post_id"] == "ext_post_123"


@pytest.mark.asyncio
async def test_list_social_accounts(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.social_accounts.SocialAccountService.get_accounts"
    ) as mock_list:
        mock_list.return_value = []
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/social-accounts"
        )
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_list_publish_history(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    with patch(
        "app.api.v1.endpoints.publishing.PublishingService.get_publish_history"
    ) as mock_list:
        mock_list.return_value = []
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/publishing/history"
        )
        assert response.status_code == 200
        assert response.json() == []
