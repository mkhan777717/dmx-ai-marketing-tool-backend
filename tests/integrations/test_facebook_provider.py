import pytest
import uuid
from unittest.mock import AsyncMock, patch

from app.services.social.facebook_provider import FacebookProvider
from app.models.social_account import SocialAccount
from app.models.campaign_content import CampaignContent
from app.models.asset import Asset
from app.constants.enums import AssetType
from app.integrations.exceptions import IntegrationError
from app.integrations.connectors.facebook.exceptions import FacebookPublishError


@pytest.fixture
def provider():
    return FacebookProvider()


@pytest.fixture
def account():
    return SocialAccount(
        id=uuid.uuid4(), account_id="page_123", access_token="encrypted_token"
    )


@pytest.fixture
def mock_secret_service():
    with patch("app.integrations.secrets.service.secret_service") as mock_secret:
        mock_secret.decrypt_token.return_value = "decrypted_token"
        yield mock_secret


@pytest.fixture
def mock_publisher():
    with patch(
        "app.integrations.connectors.facebook.publisher.FacebookPublisher"
    ) as mock_pub_class:
        mock_instance = AsyncMock()
        mock_pub_class.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_publish_content_text_only(
    provider, account, mock_secret_service, mock_publisher
):
    content = CampaignContent(
        id=uuid.uuid4(), title="Test Title", body="Hello Text", assets=[]
    )

    mock_publisher.publish_text_post.return_value = {"id": "post_123"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "post_123"
    mock_publisher.publish_text_post.assert_called_once_with(
        page_id="page_123", message="Hello Text"
    )


@pytest.mark.asyncio
async def test_publish_content_image(
    provider, account, mock_secret_service, mock_publisher
):
    image_asset = Asset(
        id=uuid.uuid4(), asset_type=AssetType.IMAGE, public_url="http://image.com/1.jpg"
    )

    content = CampaignContent(
        id=uuid.uuid4(), title="Test Title", body="Hello Image", assets=[image_asset]
    )

    mock_publisher.publish_image_post.return_value = {"id": "post_456"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "post_456"
    mock_publisher.publish_image_post.assert_called_once_with(
        page_id="page_123", message="Hello Image", image_url="http://image.com/1.jpg"
    )


@pytest.mark.asyncio
async def test_publish_content_video(
    provider, account, mock_secret_service, mock_publisher
):
    video_asset = Asset(
        id=uuid.uuid4(), asset_type=AssetType.VIDEO, public_url="http://video.com/1.mp4"
    )

    content = CampaignContent(
        id=uuid.uuid4(),
        title="My Video Title",
        body="Hello Video",
        assets=[video_asset],
    )

    mock_publisher.publish_video_post.return_value = {"id": "post_789"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "post_789"
    mock_publisher.publish_video_post.assert_called_once_with(
        page_id="page_123",
        title="My Video Title",
        description="Hello Video",
        file_url="http://video.com/1.mp4",
    )


@pytest.mark.asyncio
async def test_publish_content_multiple_assets_rejected(
    provider, account, mock_secret_service, mock_publisher
):
    asset1 = Asset(id=uuid.uuid4(), asset_type=AssetType.IMAGE, public_url="url1")
    asset2 = Asset(id=uuid.uuid4(), asset_type=AssetType.IMAGE, public_url="url2")

    content = CampaignContent(
        id=uuid.uuid4(), title="Test Title", body="Two Images", assets=[asset1, asset2]
    )

    with pytest.raises(
        IntegrationError, match="Facebook currently only supports up to 1 asset for MVP"
    ):
        await provider.publish_content(account, content)


@pytest.mark.asyncio
async def test_publish_content_missing_public_url(
    provider, account, mock_secret_service, mock_publisher
):
    asset = Asset(id=uuid.uuid4(), asset_type=AssetType.IMAGE, public_url=None)

    content = CampaignContent(
        id=uuid.uuid4(), title="Test Title", body="No URL Image", assets=[asset]
    )

    with pytest.raises(IntegrationError, match="missing public_url"):
        await provider.publish_content(account, content)


@pytest.mark.asyncio
async def test_publish_content_missing_post_id(
    provider, account, mock_secret_service, mock_publisher
):
    content = CampaignContent(
        id=uuid.uuid4(), title="Test Title", body="Hello", assets=[]
    )

    mock_publisher.publish_text_post.return_value = {"something_else": "123"}

    with pytest.raises(
        FacebookPublishError, match="Meta API did not return a valid post ID"
    ):
        await provider.publish_content(account, content)
