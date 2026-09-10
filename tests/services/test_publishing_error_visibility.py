import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.constants.enums import ApiProvider, PublishStatus
from app.integrations.connectors.instagram.exceptions import InstagramPublishError
from app.integrations.connectors.instagram.publisher import InstagramPublisher
from app.integrations.exceptions import IntegrationError
from app.models.campaign_content import CampaignContent
from app.models.publish_history import PublishHistory
from app.models.social_account import SocialAccount
from app.schemas.publishing import PublishRequest
from app.services.publishing import PublishingService
from app.utils.sanitizer import sanitize_sensitive_data


def test_sanitize_sensitive_data_redacts_tokens():
    raw = "Failed with access_token=EAAB123456789 and Bearer secret_token_xyz"
    sanitized = sanitize_sensitive_data(raw)
    assert "EAAB123456789" not in sanitized
    assert "secret_token_xyz" not in sanitized
    assert "access_token=[REDACTED]" in sanitized
    assert "Bearer [REDACTED]" in sanitized


def test_sanitize_sensitive_data_json_style():
    raw = '{"error": "invalid token", "client_secret": "my_secret_key"}'
    sanitized = sanitize_sensitive_data(raw)
    assert "my_secret_key" not in sanitized
    assert "[REDACTED]" in sanitized


def test_instagram_publisher_default_timeout():
    publisher = InstagramPublisher(page_access_token="test_token")
    assert publisher.timeout == 30.0


@pytest.mark.asyncio
async def test_instagram_publisher_catches_read_timeout():
    publisher = InstagramPublisher(page_access_token="test_token", timeout=30.0)
    with patch(
        "httpx.AsyncClient.post",
        side_effect=httpx.ReadTimeout("The read operation timed out"),
    ):
        with pytest.raises(InstagramPublishError) as exc_info:
            await publisher.publish_image_post(
                ig_user_id="ig_123", image_url="https://example.com/image.jpg"
            )
        assert "Failed to create media container (Network error)" in str(exc_info.value)
        assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_publish_content_handles_normal_exception():
    mock_db = AsyncMock()
    workspace_id = uuid.uuid4()
    content_id = uuid.uuid4()
    account_id = uuid.uuid4()

    request = PublishRequest(content_id=content_id, social_account_id=account_id)

    mock_content = AsyncMock(spec=CampaignContent)
    mock_content.id = content_id
    mock_content.workspace_id = workspace_id
    mock_content.campaign_id = uuid.uuid4()

    mock_account = AsyncMock(spec=SocialAccount)
    mock_account.id = account_id
    mock_account.workspace_id = workspace_id
    mock_account.provider = ApiProvider.INSTAGRAM

    mock_history = PublishHistory(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_id=content_id,
        social_account_id=account_id,
        status=PublishStatus.PENDING,
    )

    with (
        patch(
            "app.services.publishing.campaign_content_repo.get_by_id",
            return_value=mock_content,
        ),
        patch(
            "app.services.publishing.social_account_repo.get_by_id",
            return_value=mock_account,
        ),
        patch(
            "app.services.publishing.publish_history_repo.create",
            return_value=mock_history,
        ),
        patch(
            "app.services.publishing.publish_history_repo.update",
            side_effect=lambda db, db_obj, obj_in: AsyncMock(
                **{**db_obj.__dict__, **obj_in}
            ),
        ) as mock_update,
        patch(
            "app.services.publishing.SocialProviderFactory.get_provider"
        ) as mock_get_provider,
    ):
        mock_provider = AsyncMock()
        mock_provider.publish_content.side_effect = IntegrationError(
            "Specific failure message"
        )
        mock_get_provider.return_value = mock_provider

        await PublishingService.publish_content(mock_db, workspace_id, request)

        assert mock_update.called
        obj_in = mock_update.call_args[1]["obj_in"]
        assert obj_in["status"] == PublishStatus.FAILED
        assert "IntegrationError: Specific failure message" in obj_in["error_message"]


@pytest.mark.asyncio
async def test_publish_content_handles_empty_exception_str():
    mock_db = AsyncMock()
    workspace_id = uuid.uuid4()
    content_id = uuid.uuid4()
    account_id = uuid.uuid4()

    request = PublishRequest(content_id=content_id, social_account_id=account_id)

    mock_content = AsyncMock(spec=CampaignContent)
    mock_content.id = content_id
    mock_content.workspace_id = workspace_id
    mock_content.campaign_id = uuid.uuid4()

    mock_account = AsyncMock(spec=SocialAccount)
    mock_account.id = account_id
    mock_account.workspace_id = workspace_id
    mock_account.provider = ApiProvider.INSTAGRAM

    mock_history = PublishHistory(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_id=content_id,
        social_account_id=account_id,
        status=PublishStatus.PENDING,
    )

    with (
        patch(
            "app.services.publishing.campaign_content_repo.get_by_id",
            return_value=mock_content,
        ),
        patch(
            "app.services.publishing.social_account_repo.get_by_id",
            return_value=mock_account,
        ),
        patch(
            "app.services.publishing.publish_history_repo.create",
            return_value=mock_history,
        ),
        patch(
            "app.services.publishing.publish_history_repo.update",
            side_effect=lambda db, db_obj, obj_in: AsyncMock(
                **{**db_obj.__dict__, **obj_in}
            ),
        ) as mock_update,
        patch(
            "app.services.publishing.SocialProviderFactory.get_provider"
        ) as mock_get_provider,
    ):
        mock_provider = AsyncMock()
        # Exception raised without args has str(e) == ""
        mock_provider.publish_content.side_effect = IntegrationError()
        mock_get_provider.return_value = mock_provider

        await PublishingService.publish_content(mock_db, workspace_id, request)

        assert mock_update.called
        obj_in = mock_update.call_args[1]["obj_in"]
        assert obj_in["status"] == PublishStatus.FAILED
        assert (
            obj_in["error_message"]
            == "IntegrationError: Publishing failed due to an unhandled error"
        )


@pytest.mark.asyncio
async def test_publish_content_sanitizes_tokens_in_error_message():
    mock_db = AsyncMock()
    workspace_id = uuid.uuid4()
    content_id = uuid.uuid4()
    account_id = uuid.uuid4()

    request = PublishRequest(content_id=content_id, social_account_id=account_id)

    mock_content = AsyncMock(spec=CampaignContent)
    mock_content.id = content_id
    mock_content.workspace_id = workspace_id
    mock_content.campaign_id = uuid.uuid4()

    mock_account = AsyncMock(spec=SocialAccount)
    mock_account.id = account_id
    mock_account.workspace_id = workspace_id
    mock_account.provider = ApiProvider.INSTAGRAM

    mock_history = PublishHistory(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_id=content_id,
        social_account_id=account_id,
        status=PublishStatus.PENDING,
    )

    with (
        patch(
            "app.services.publishing.campaign_content_repo.get_by_id",
            return_value=mock_content,
        ),
        patch(
            "app.services.publishing.social_account_repo.get_by_id",
            return_value=mock_account,
        ),
        patch(
            "app.services.publishing.publish_history_repo.create",
            return_value=mock_history,
        ),
        patch(
            "app.services.publishing.publish_history_repo.update",
            side_effect=lambda db, db_obj, obj_in: AsyncMock(
                **{**db_obj.__dict__, **obj_in}
            ),
        ) as mock_update,
        patch(
            "app.services.publishing.SocialProviderFactory.get_provider"
        ) as mock_get_provider,
    ):
        mock_provider = AsyncMock()
        mock_provider.publish_content.side_effect = InstagramPublishError(
            "Failed request with access_token=SECRET_TOKEN_12345"
        )
        mock_get_provider.return_value = mock_provider

        await PublishingService.publish_content(mock_db, workspace_id, request)

        obj_in = mock_update.call_args[1]["obj_in"]
        assert obj_in["status"] == PublishStatus.FAILED
        assert "SECRET_TOKEN_12345" not in obj_in["error_message"]
        assert "access_token=[REDACTED]" in obj_in["error_message"]
