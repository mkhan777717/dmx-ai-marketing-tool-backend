import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.constants.enums import AssetType
from app.integrations.connectors.instagram.exceptions import (
    InstagramAuthError,
)
from app.integrations.exceptions import IntegrationError
from app.models.asset import Asset
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.instagram_provider import InstagramProvider


@pytest.fixture
def provider():
    return InstagramProvider()


@pytest.fixture
def account():
    return SocialAccount(
        id=uuid.uuid4(), account_id="ig_12345", access_token="encrypted_token"
    )


@pytest.fixture
def mock_secret_service():
    with (
        patch("app.integrations.secrets.service.secret_service") as mock_secret,
        patch("app.integrations.webhooks.verifier.secret_service", mock_secret),
    ):
        mock_secret.decrypt_token.side_effect = lambda t: f"decrypted_{t}" if t else ""
        mock_secret.get_provider_credentials.return_value = {
            "client_id": "client_123",
            "client_secret": "secret_456",
        }
        yield mock_secret


@pytest.fixture
def mock_publisher():
    with patch(
        "app.integrations.connectors.instagram.publisher.InstagramPublisher"
    ) as mock_pub_class:
        mock_instance = AsyncMock()
        mock_pub_class.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_get_account_info_success(provider, mock_secret_service):
    mock_sync_result = {
        "instagram_accounts": [
            {
                "id": "ig_999",
                "username": "ig_business",
                "name": "IG Business Profile",
                "profile_picture_url": "http://example.com/pic.jpg",
                "linked_page_id": "page_999",
                "page_access_token": "page_token_999",
            }
        ]
    }

    with patch(
        "app.integrations.connectors.instagram.sync.InstagramSyncEngine.perform_sync",
        new_callable=AsyncMock,
    ) as mock_sync:
        mock_sync.return_value = mock_sync_result

        result = await provider.get_account_info("enc_access_token")

        assert result["account_id"] == "ig_999"
        assert result["name"] == "IG Business Profile"
        assert result["username"] == "ig_business"
        assert result["profile_picture_url"] == "http://example.com/pic.jpg"
        assert result["linked_page_id"] == "page_999"
        assert result["page_access_token"] == "page_token_999"


@pytest.mark.asyncio
async def test_get_account_info_missing_token(provider):
    with pytest.raises(InstagramAuthError, match="Access token is required"):
        await provider.get_account_info("")


@pytest.mark.asyncio
async def test_get_account_info_no_ig_accounts(provider, mock_secret_service):
    with patch(
        "app.integrations.connectors.instagram.sync.InstagramSyncEngine.perform_sync",
        new_callable=AsyncMock,
    ) as mock_sync:
        mock_sync.return_value = {"instagram_accounts": []}

        with pytest.raises(
            InstagramAuthError, match="No linked Instagram Business Account found"
        ):
            await provider.get_account_info("enc_access_token")


@pytest.mark.asyncio
async def test_publish_content_video_success(
    provider, account, mock_secret_service, mock_publisher
):
    video_asset = Asset(
        id=uuid.uuid4(), asset_type=AssetType.VIDEO, public_url="http://video.com/1.mp4"
    )
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Video Post",
        body="Check out this Video!",
        assets=[video_asset],
    )

    mock_publisher.publish_video_post.return_value = {"id": "ig_video_post_123"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "ig_video_post_123"
    mock_publisher.publish_video_post.assert_called_once_with(
        ig_user_id="ig_12345",
        video_url="http://video.com/1.mp4",
        caption="Check out this Video!",
    )


@pytest.mark.asyncio
async def test_publish_content_video_missing_url(
    provider, account, mock_secret_service, mock_publisher
):
    video_asset = Asset(id=uuid.uuid4(), asset_type=AssetType.VIDEO, public_url=None)
    content = CampaignContent(
        id=uuid.uuid4(), title="Video Post", body="No URL Video", assets=[video_asset]
    )

    with pytest.raises(IntegrationError, match="video asset missing public_url"):
        await provider.publish_content(account, content)


@pytest.mark.asyncio
async def test_publish_content_missing_token(provider, mock_secret_service):
    acc_no_token = SocialAccount(
        id=uuid.uuid4(), account_id="ig_123", access_token=None
    )
    content = CampaignContent(id=uuid.uuid4(), title="T", body="B", assets=[])

    with pytest.raises(IntegrationError, match="No access token available"):
        await provider.publish_content(acc_no_token, content)


@pytest.mark.asyncio
async def test_webhook_verifier_instagram_route(mock_secret_service):
    import hashlib
    import hmac
    from unittest.mock import MagicMock

    from app.integrations.webhooks.verifier import WebhookVerifier

    payload = b'{"object": "instagram"}'
    mac = hmac.new(b"secret_456", payload, hashlib.sha256).hexdigest()

    mock_request = MagicMock()
    mock_request.headers.get.side_effect = lambda h, default="": {
        "X-Hub-Signature-256": f"sha256={mac}"
    }.get(h, default)

    valid = await WebhookVerifier.verify_signature("instagram", mock_request, payload)
    assert valid is True

    # Test invalid signature
    mock_request_invalid = MagicMock()
    mock_request_invalid.headers.get.side_effect = lambda h, default="": {
        "X-Hub-Signature-256": "sha256=invalid_sig"
    }.get(h, default)

    invalid = await WebhookVerifier.verify_signature(
        "instagram", mock_request_invalid, payload
    )
    assert invalid is False
