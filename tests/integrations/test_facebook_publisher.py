import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.connectors.facebook.publisher import FacebookPublisher
from app.integrations.connectors.facebook.exceptions import FacebookPublishError


@pytest.fixture
def publisher():
    return FacebookPublisher(access_token="test_token")


@pytest.mark.asyncio
async def test_publish_text_post_success(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123_456"}
        mock_post.return_value = mock_response

        result = await publisher.publish_text_post(page_id="123", message="Hello world")

        assert result == {"id": "123_456"}
        mock_post.assert_called_once_with(
            f"{publisher.BASE_URL}/123/feed",
            data={"message": "Hello world", "access_token": "test_token"},
        )


@pytest.mark.asyncio
async def test_publish_text_post_error(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with pytest.raises(FacebookPublishError, match="Failed to publish text post"):
            await publisher.publish_text_post(page_id="123", message="Hello world")


@pytest.mark.asyncio
async def test_publish_image_post_success(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123_456", "post_id": "999"}
        mock_post.return_value = mock_response

        result = await publisher.publish_image_post(
            page_id="123",
            message="Look at this image",
            image_url="http://example.com/image.jpg",
        )

        assert result == {"id": "123_456", "post_id": "999"}
        mock_post.assert_called_once_with(
            f"{publisher.BASE_URL}/123/photos",
            data={
                "caption": "Look at this image",
                "url": "http://example.com/image.jpg",
                "access_token": "test_token",
            },
        )


@pytest.mark.asyncio
async def test_publish_image_post_error(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        with pytest.raises(FacebookPublishError, match="Failed to publish image post"):
            await publisher.publish_image_post(
                page_id="123",
                message="Look at this image",
                image_url="http://example.com/image.jpg",
            )


@pytest.mark.asyncio
async def test_publish_video_post_success(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "789_101"}
        mock_post.return_value = mock_response

        result = await publisher.publish_video_post(
            page_id="123",
            title="My Video",
            description="A great video",
            file_url="http://example.com/video.mp4",
        )

        assert result == {"id": "789_101"}
        mock_post.assert_called_once_with(
            f"{publisher.BASE_URL}/123/videos",
            data={
                "title": "My Video",
                "description": "A great video",
                "file_url": "http://example.com/video.mp4",
                "access_token": "test_token",
            },
        )


@pytest.mark.asyncio
async def test_publish_video_post_error(publisher):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(FacebookPublishError, match="Failed to publish video post"):
            await publisher.publish_video_post(
                page_id="123",
                title="My Video",
                description="A great video",
                file_url="http://example.com/video.mp4",
            )
