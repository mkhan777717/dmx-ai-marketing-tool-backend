import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.constants.enums import ApiProvider
from app.integrations.connectors.slack.exceptions import SlackPublishError
from app.integrations.exceptions import IntegrationError
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.factory import SocialProviderFactory
from app.services.social.slack_provider import SlackProvider


@pytest.fixture
def mock_social_account():
    return SocialAccount(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        provider=ApiProvider.SLACK,
        account_id="C12345678",
        name="#general",
        access_token="enc_xoxb_token",
        is_active=True,
    )


@pytest.fixture
def mock_campaign_content():
    return CampaignContent(
        id=uuid.uuid4(),
        campaign_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        title="Test Slack Content",
        body="Hello Slack Channel!",
        content_type="SOCIAL_POST",
        assets=[],
    )


def test_factory_returns_slack_provider():
    provider = SocialProviderFactory.get_provider(ApiProvider.SLACK)
    assert isinstance(provider, SlackProvider)
    assert provider.provider_name == ApiProvider.SLACK.value


@pytest.mark.asyncio
async def test_slack_provider_publish_text_success(
    mock_social_account, mock_campaign_content
):
    provider = SlackProvider()

    with (
        patch(
            "app.services.social.slack_provider.secret_service.decrypt_token",
            return_value="raw_xoxb_bot_token",
        ) as mock_decrypt,
        patch(
            "app.services.social.slack_provider.SlackPublisher.publish_message",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.return_value = {
            "ok": True,
            "channel": "C12345678",
            "ts": "16382023.000200",
            "message": {"text": "Hello Slack Channel!"},
        }

        post_id = await provider.publish_content(
            mock_social_account, mock_campaign_content
        )

        assert post_id == "16382023.000200"
        mock_decrypt.assert_called_once_with("enc_xoxb_token")
        mock_publish.assert_called_once_with(
            channel_id="C12345678",
            text="Hello Slack Channel!",
        )


@pytest.mark.asyncio
async def test_slack_provider_publish_with_asset_url(
    mock_social_account, mock_campaign_content
):
    provider = SlackProvider()

    mock_asset = AsyncMock()
    mock_asset.public_url = "https://example.com/image.png"
    mock_campaign_content.assets = [mock_asset]

    with (
        patch(
            "app.services.social.slack_provider.secret_service.decrypt_token",
            return_value="raw_xoxb_bot_token",
        ),
        patch(
            "app.services.social.slack_provider.SlackPublisher.publish_message",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.return_value = {
            "ok": True,
            "channel": "C12345678",
            "ts": "16382024.000300",
        }

        post_id = await provider.publish_content(
            mock_social_account, mock_campaign_content
        )

        assert post_id == "16382024.000300"
        mock_publish.assert_called_once_with(
            channel_id="C12345678",
            text="Hello Slack Channel!\nhttps://example.com/image.png",
        )


@pytest.mark.asyncio
async def test_slack_provider_publish_empty_body_raises_error(
    mock_social_account, mock_campaign_content
):
    provider = SlackProvider()
    mock_campaign_content.body = "   "
    mock_campaign_content.assets = []

    with pytest.raises(IntegrationError, match="body is empty"):
        await provider.publish_content(mock_social_account, mock_campaign_content)


@pytest.mark.asyncio
async def test_slack_provider_handles_publish_error(
    mock_social_account, mock_campaign_content
):
    provider = SlackProvider()

    with (
        patch(
            "app.services.social.slack_provider.secret_service.decrypt_token",
            return_value="raw_xoxb_bot_token",
        ),
        patch(
            "app.services.social.slack_provider.SlackPublisher.publish_message",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.side_effect = SlackPublishError(
            "Slack API error: channel_not_found"
        )

        with pytest.raises(IntegrationError, match="Slack publishing failed"):
            await provider.publish_content(mock_social_account, mock_campaign_content)
