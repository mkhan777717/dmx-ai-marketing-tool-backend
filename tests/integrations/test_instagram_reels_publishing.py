import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.enums import AssetType
from app.integrations.connectors.instagram.connector import InstagramConnector
from app.integrations.connectors.instagram.exceptions import InstagramPublishError
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
async def test_reels_publish_http_flow():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(
        page_access_token="tok_123", max_attempts=3, poll_interval=0.01
    )

    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "reels_container_999"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status_code": "FINISHED"}

    publish_resp = MagicMock()
    publish_resp.status_code = 200
    publish_resp.json.return_value = {"id": "reels_post_1000"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [container_resp, publish_resp]
        mock_client.get.return_value = status_resp

        res = await pub.publish_reels_post(
            ig_user_id="ig_555",
            video_url="http://video.com/reel.mp4",
            caption="Check out my Reel!",
        )

        assert res["id"] == "reels_post_1000"

        # Verify container creation call parameters
        post_calls = mock_client.post.call_args_list
        assert len(post_calls) == 2

        # 1. Container creation verification
        container_url, container_kwargs = post_calls[0]
        assert "ig_555/media" in container_url[0]
        assert container_kwargs["data"]["media_type"] == "REELS"
        assert container_kwargs["data"]["video_url"] == "http://video.com/reel.mp4"
        assert container_kwargs["data"]["caption"] == "Check out my Reel!"
        assert container_kwargs["data"]["access_token"] == "tok_123"

        # 2. Status polling verification
        mock_client.get.assert_called_once()
        get_url, get_kwargs = mock_client.get.call_args
        assert "reels_container_999" in get_url[0]

        # 3. Media publish verification
        publish_url, publish_kwargs = post_calls[1]
        assert "ig_555/media_publish" in publish_url[0]
        assert publish_kwargs["data"]["creation_id"] == "reels_container_999"


@pytest.mark.asyncio
async def test_reels_publish_missing_token():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="")
    with pytest.raises(InstagramPublishError, match="Page access token is required"):
        await pub.publish_reels_post(
            ig_user_id="ig_123", video_url="http://video.com/file.mp4"
        )


@pytest.mark.asyncio
async def test_reels_publish_missing_account_id():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="tok_123")
    with pytest.raises(InstagramPublishError, match="Instagram user ID is required"):
        await pub.publish_reels_post(
            ig_user_id="", video_url="http://video.com/file.mp4"
        )


@pytest.mark.asyncio
async def test_reels_publish_missing_video_url():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="tok_123")
    with pytest.raises(InstagramPublishError, match="Video URL is required"):
        await pub.publish_reels_post(ig_user_id="ig_123", video_url="")


@pytest.mark.asyncio
async def test_reels_publish_container_creation_http_failure():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="tok_123")

    fail_resp = MagicMock()
    fail_resp.status_code = 400
    fail_resp.text = "Bad Request: Invalid video aspect ratio"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(
            InstagramPublishError, match="Failed to create Reels media container"
        ):
            await pub.publish_reels_post(
                ig_user_id="ig_123", video_url="http://video.com/file.mp4"
            )


@pytest.mark.asyncio
async def test_reels_publish_container_error_status():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="tok_123")

    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "creation_reels_err"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {
        "status_code": "ERROR",
        "status": "Video processing failed",
    }

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = container_resp
        mock_client.get.return_value = status_resp

        with pytest.raises(
            InstagramPublishError, match="processing failed with status 'ERROR'"
        ):
            await pub.publish_reels_post(
                ig_user_id="ig_123", video_url="http://video.com/file.mp4"
            )


@pytest.mark.asyncio
async def test_reels_publish_container_timeout():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(
        page_access_token="tok_123", max_attempts=2, poll_interval=0.01
    )

    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "creation_reels_timeout"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status_code": "IN_PROGRESS"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = container_resp
        mock_client.get.return_value = status_resp

        with pytest.raises(
            InstagramPublishError, match="processing timed out after 2 attempts"
        ):
            await pub.publish_reels_post(
                ig_user_id="ig_123", video_url="http://video.com/file.mp4"
            )


@pytest.mark.asyncio
async def test_reels_publish_media_publish_failure():
    from app.integrations.connectors.instagram.publisher import InstagramPublisher

    pub = InstagramPublisher(page_access_token="tok_123")

    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "creation_reels_ok"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status_code": "FINISHED"}

    pub_fail_resp = MagicMock()
    pub_fail_resp.status_code = 500
    pub_fail_resp.text = "Internal Server Error"

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [container_resp, pub_fail_resp]
        mock_client.get.return_value = status_resp

        with pytest.raises(
            InstagramPublishError, match="Failed to publish Reels media container"
        ):
            await pub.publish_reels_post(
                ig_user_id="ig_123", video_url="http://video.com/file.mp4"
            )


@pytest.mark.asyncio
async def test_provider_routes_to_reels(
    provider, account, mock_secret_service, mock_publisher
):
    video_asset = Asset(
        id=uuid.uuid4(),
        asset_type=AssetType.VIDEO,
        public_url="http://video.com/reel.mp4",
    )
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Reels Post",
        body="My Reel Caption",
        assets=[video_asset],
        metadata_={"is_reel": True},
    )

    mock_publisher.publish_reels_post.return_value = {"id": "ig_reel_post_999"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "ig_reel_post_999"
    mock_publisher.publish_reels_post.assert_called_once_with(
        ig_user_id="ig_12345",
        video_url="http://video.com/reel.mp4",
        caption="My Reel Caption",
    )


@pytest.mark.asyncio
async def test_connector_publish_reels():
    credentials = {"client_id": "test_id", "client_secret": "test_sec"}
    connector = InstagramConnector(credentials=credentials, access_token="tok_123")

    with patch(
        "app.integrations.connectors.instagram.publisher.InstagramPublisher.publish_reels_post",
        new_callable=AsyncMock,
    ) as mock_reels:
        mock_reels.return_value = {"id": "ig_reel_111"}

        res = await connector.publish(
            page_id="ig_1234",
            content="Reel Content",
            page_access_token="page_tok",
            video_url="http://video.com/reel.mp4",
            is_reel=True,
        )

        assert res["id"] == "ig_reel_111"
        mock_reels.assert_called_once_with(
            "ig_1234", video_url="http://video.com/reel.mp4", caption="Reel Content"
        )
