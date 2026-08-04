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
def mock_campaign_id():
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
async def test_generate_ai_content(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id
):
    payload = {
        "prompt": "Write a launch post for a new feature.",
        "content_type": "SOCIAL_POST",
        "language": "en",
        "provider": "MOCK",
    }

    response = await async_client.post(
        f"/api/v1/workspaces/{mock_workspace_id}/ai/generate", json=payload
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content_type"] == "SOCIAL_POST"
    assert "mock generated content" in data["body"]
    assert data["provider_used"] == "MOCK"


@pytest.mark.asyncio
async def test_create_campaign_content(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id, mock_campaign_id
):
    with patch(
        "app.api.v1.endpoints.campaign_content.AIContentService.create_campaign_content"
    ) as mock_create:
        from datetime import datetime, timezone

        from app.constants.enums import ContentStatus, ContentType
        from app.models.campaign_content import CampaignContent

        mock_content = CampaignContent(
            id=uuid.uuid4(),
            campaign_id=mock_campaign_id,
            title="Generated Draft",
            content_type=ContentType.SOCIAL_POST,
            status=ContentStatus.DRAFT,
            language="en",
            version=1,
            is_current=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        mock_create.return_value = mock_content

        payload = {
            "campaign_id": str(mock_campaign_id),
            "title": "Generated Draft",
            "content_type": "SOCIAL_POST",
        }

        response = await async_client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/campaigns/{mock_campaign_id}/contents",
            json=payload,
        )

        assert response.status_code == 201
        assert response.json()["data"]["title"] == "Generated Draft"
        assert response.json()["data"]["version"] == 1


@pytest.mark.asyncio
async def test_list_campaign_contents(
    async_client: AsyncClient, override_auth_deps, mock_workspace_id, mock_campaign_id
):
    with patch(
        "app.api.v1.endpoints.campaign_content.AIContentService.get_campaign_contents"
    ) as mock_list:
        mock_list.return_value = []
        response = await async_client.get(
            f"/api/v1/workspaces/{mock_workspace_id}/campaigns/{mock_campaign_id}/contents"
        )
        assert response.status_code == 200
        assert response.json()["data"] == []
