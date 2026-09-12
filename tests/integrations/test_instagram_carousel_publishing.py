import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.enums import AssetType
from app.integrations.connectors.instagram.connector import InstagramConnector
from app.integrations.connectors.instagram.exceptions import InstagramPublishError
from app.integrations.connectors.instagram.publisher import InstagramPublisher
from app.models.asset import Asset
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.instagram_provider import InstagramProvider


@pytest.fixture
def publisher():
    return InstagramPublisher(
        page_access_token="test_page_access_token",
        max_attempts=3,
        poll_interval=0.01,
    )


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
async def test_carousel_image_only_success(publisher):
    # 2 child image creation responses, 1 parent creation response, 1 publish response
    c1_resp = MagicMock(status_code=200, json=lambda: {"id": "child_img_1"})
    c2_resp = MagicMock(status_code=200, json=lambda: {"id": "child_img_2"})
    parent_resp = MagicMock(status_code=200, json=lambda: {"id": "parent_carousel_999"})
    publish_resp = MagicMock(status_code=200, json=lambda: {"id": "post_carousel_1000"})

    status_resp = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [c1_resp, c2_resp, parent_resp, publish_resp]
        mock_client.get.return_value = status_resp

        items = ["http://example.com/img1.jpg", "http://example.com/img2.jpg"]
        res = await publisher.publish_carousel_post(
            "ig_123", items=items, caption="Carousel Caption"
        )

        assert res["id"] == "post_carousel_1000"

        # Verify POST call sequences and payloads
        post_calls = mock_client.post.call_args_list
        assert len(post_calls) == 4

        # Child 1 payload
        _, c1_kwargs = post_calls[0]
        assert c1_kwargs["data"]["is_carousel_item"] == "true"
        assert c1_kwargs["data"]["image_url"] == "http://example.com/img1.jpg"

        # Child 2 payload
        _, c2_kwargs = post_calls[1]
        assert c2_kwargs["data"]["is_carousel_item"] == "true"
        assert c2_kwargs["data"]["image_url"] == "http://example.com/img2.jpg"

        # Parent carousel payload
        _, p_kwargs = post_calls[2]
        assert p_kwargs["data"]["media_type"] == "CAROUSEL"
        assert p_kwargs["data"]["children"] == "child_img_1,child_img_2"
        assert p_kwargs["data"]["caption"] == "Carousel Caption"

        # Publish payload
        _, pub_kwargs = post_calls[3]
        assert pub_kwargs["data"]["creation_id"] == "parent_carousel_999"


@pytest.mark.asyncio
async def test_carousel_mixed_image_and_video_success(publisher):
    c1_resp = MagicMock(status_code=200, json=lambda: {"id": "child_img_1"})
    c2_resp = MagicMock(status_code=200, json=lambda: {"id": "child_vid_2"})
    parent_resp = MagicMock(status_code=200, json=lambda: {"id": "parent_carousel_888"})
    publish_resp = MagicMock(status_code=200, json=lambda: {"id": "post_carousel_777"})

    status_resp = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [c1_resp, c2_resp, parent_resp, publish_resp]
        mock_client.get.return_value = status_resp

        items = [
            {"media_type": "IMAGE", "url": "http://example.com/img1.jpg"},
            {"media_type": "VIDEO", "url": "http://example.com/vid1.mp4"},
        ]
        res = await publisher.publish_carousel_post(
            "ig_123", items=items, caption="Mixed Carousel"
        )

        assert res["id"] == "post_carousel_777"

        post_calls = mock_client.post.call_args_list
        assert post_calls[0][1]["data"]["image_url"] == "http://example.com/img1.jpg"
        assert post_calls[1][1]["data"]["media_type"] == "VIDEO"
        assert post_calls[1][1]["data"]["video_url"] == "http://example.com/vid1.mp4"
        assert post_calls[2][1]["data"]["children"] == "child_img_1,child_vid_2"


@pytest.mark.asyncio
async def test_carousel_missing_token():
    pub = InstagramPublisher(page_access_token="")
    with pytest.raises(InstagramPublishError, match="Page access token is required"):
        await pub.publish_carousel_post(
            "ig_123", items=["http://a.com", "http://b.com"]
        )


@pytest.mark.asyncio
async def test_carousel_missing_account_id(publisher):
    with pytest.raises(InstagramPublishError, match="Instagram user ID is required"):
        await publisher.publish_carousel_post(
            "", items=["http://a.com", "http://b.com"]
        )


@pytest.mark.asyncio
async def test_carousel_invalid_item_counts(publisher):
    # Less than 2 items
    with pytest.raises(InstagramPublishError, match="requires between 2 and 10 items"):
        await publisher.publish_carousel_post("ig_123", items=["http://a.com"])

    # More than 10 items
    with pytest.raises(InstagramPublishError, match="requires between 2 and 10 items"):
        await publisher.publish_carousel_post(
            "ig_123", items=[f"http://img{i}.com" for i in range(11)]
        )


@pytest.mark.asyncio
async def test_carousel_invalid_media_url_or_type(publisher):
    # Empty URL string
    with pytest.raises(InstagramPublishError, match="empty image URL"):
        await publisher.publish_carousel_post("ig_123", items=["http://a.com", "   "])

    # Unsupported media type
    with pytest.raises(InstagramPublishError, match="unsupported media_type 'AUDIO'"):
        await publisher.publish_carousel_post(
            "ig_123",
            items=[
                {"media_type": "IMAGE", "url": "http://a.com"},
                {"media_type": "AUDIO", "url": "http://b.com"},
            ],
        )


@pytest.mark.asyncio
async def test_carousel_child_container_creation_failure(publisher):
    c1_resp = MagicMock(status_code=400, text="Bad Request: Image download failed")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = c1_resp

        with pytest.raises(
            InstagramPublishError,
            match="Failed to create child media container for item 1",
        ):
            await publisher.publish_carousel_post(
                "ig_123", items=["http://a.com", "http://b.com"]
            )


@pytest.mark.asyncio
async def test_carousel_child_processing_error(publisher):
    c1_resp = MagicMock(status_code=200, json=lambda: {"id": "child_err"})
    status_err = MagicMock(
        status_code=200,
        json=lambda: {
            "status_code": "ERROR",
            "status": "Child aspect ratio not supported",
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = c1_resp
        mock_client.get.return_value = status_err

        with pytest.raises(
            InstagramPublishError, match="processing failed with status 'ERROR'"
        ):
            await publisher.publish_carousel_post(
                "ig_123", items=["http://a.com", "http://b.com"]
            )


@pytest.mark.asyncio
async def test_carousel_parent_processing_error(publisher):
    c1_resp = MagicMock(status_code=200, json=lambda: {"id": "c1"})
    c2_resp = MagicMock(status_code=200, json=lambda: {"id": "c2"})
    parent_resp = MagicMock(status_code=200, json=lambda: {"id": "parent_err"})

    status_ok = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})
    status_err = MagicMock(status_code=200, json=lambda: {"status_code": "ERROR"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [c1_resp, c2_resp, parent_resp]
        mock_client.get.side_effect = [status_ok, status_ok, status_err]

        with pytest.raises(
            InstagramPublishError, match="processing failed with status 'ERROR'"
        ):
            await publisher.publish_carousel_post(
                "ig_123", items=["http://a.com", "http://b.com"]
            )


@pytest.mark.asyncio
async def test_carousel_media_publish_failure(publisher):
    c1_resp = MagicMock(status_code=200, json=lambda: {"id": "c1"})
    c2_resp = MagicMock(status_code=200, json=lambda: {"id": "c2"})
    parent_resp = MagicMock(status_code=200, json=lambda: {"id": "p1"})
    pub_fail_resp = MagicMock(status_code=500, text="Internal Server Error")

    status_ok = MagicMock(status_code=200, json=lambda: {"status_code": "FINISHED"})

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [c1_resp, c2_resp, parent_resp, pub_fail_resp]
        mock_client.get.return_value = status_ok

        with pytest.raises(
            InstagramPublishError, match="Failed to publish Carousel media container"
        ):
            await publisher.publish_carousel_post(
                "ig_123", items=["http://a.com", "http://b.com"]
            )


@pytest.mark.asyncio
async def test_provider_routes_multi_asset_to_carousel(
    provider, account, mock_secret_service, mock_publisher
):
    asset1 = Asset(
        id=uuid.uuid4(), asset_type=AssetType.IMAGE, public_url="http://a.com/1.jpg"
    )
    asset2 = Asset(
        id=uuid.uuid4(), asset_type=AssetType.VIDEO, public_url="http://a.com/2.mp4"
    )

    content = CampaignContent(
        id=uuid.uuid4(),
        title="Carousel Title",
        body="Carousel Body",
        assets=[asset1, asset2],
    )

    mock_publisher.publish_carousel_post.return_value = {"id": "post_carousel_555"}

    post_id = await provider.publish_content(account, content)

    assert post_id == "post_carousel_555"
    mock_publisher.publish_carousel_post.assert_called_once_with(
        ig_user_id="ig_12345",
        items=[
            {"media_type": "IMAGE", "url": "http://a.com/1.jpg"},
            {"media_type": "VIDEO", "url": "http://a.com/2.mp4"},
        ],
        caption="Carousel Body",
    )


@pytest.mark.asyncio
async def test_connector_publish_carousel():
    credentials = {"client_id": "test_id", "client_secret": "test_sec"}
    connector = InstagramConnector(credentials=credentials, access_token="tok_123")

    with patch(
        "app.integrations.connectors.instagram.publisher.InstagramPublisher.publish_carousel_post",
        new_callable=AsyncMock,
    ) as mock_car:
        mock_car.return_value = {"id": "ig_carousel_222"}

        res = await connector.publish(
            page_id="ig_1234",
            content="Carousel Content",
            page_access_token="page_tok",
            image_urls=["http://a.com/1.jpg", "http://a.com/2.jpg"],
        )

        assert res["id"] == "ig_carousel_222"
        mock_car.assert_called_once_with(
            "ig_1234",
            items=["http://a.com/1.jpg", "http://a.com/2.jpg"],
            caption="Carousel Content",
        )
