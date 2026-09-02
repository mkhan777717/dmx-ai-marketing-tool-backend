from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.connectors.instagram.exceptions import InstagramPublishError
from app.integrations.connectors.instagram.publisher import InstagramPublisher


@pytest.fixture
def publisher():
    return InstagramPublisher(
        page_access_token="test_page_access_token",
        max_attempts=3,
        poll_interval=0.01,
    )


@pytest.mark.asyncio
async def test_polling_finishes_immediately(publisher):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status_code": "FINISHED", "id": "creation_123"}
    mock_client.get.return_value = mock_response

    result = await publisher.wait_for_container_ready(
        "creation_123", client=mock_client
    )
    assert result is True
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_polling_in_progress_then_finished(publisher):
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    resp_in_progress = MagicMock()
    resp_in_progress.status_code = 200
    resp_in_progress.json.return_value = {"status_code": "IN_PROGRESS"}

    resp_finished = MagicMock()
    resp_finished.status_code = 200
    resp_finished.json.return_value = {"status_code": "FINISHED"}

    mock_client.get.side_effect = [resp_in_progress, resp_finished]

    result = await publisher.wait_for_container_ready(
        "creation_123", client=mock_client
    )
    assert result is True
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_polling_error_status(publisher):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status_code": "ERROR",
        "status": "Video processing failed due to unsupported codec.",
    }
    mock_client.get.return_value = mock_response

    with pytest.raises(
        InstagramPublishError, match="processing failed with status 'ERROR'"
    ):
        await publisher.wait_for_container_ready("creation_123", client=mock_client)


@pytest.mark.asyncio
async def test_polling_timeout(publisher):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status_code": "IN_PROGRESS"}
    mock_client.get.return_value = mock_response

    with pytest.raises(
        InstagramPublishError, match="processing timed out after 3 attempts"
    ):
        await publisher.wait_for_container_ready(
            "creation_123", client=mock_client, max_attempts=3
        )

    assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_polling_http_error(publisher):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Meta API Server Error"
    mock_client.get.return_value = mock_response

    with pytest.raises(InstagramPublishError, match="Status Code 500"):
        await publisher.wait_for_container_ready("creation_123", client=mock_client)


@pytest.mark.asyncio
async def test_polling_missing_creation_id_and_token(publisher):
    with pytest.raises(InstagramPublishError, match="creation ID is required"):
        await publisher.wait_for_container_ready("")

    no_token_pub = InstagramPublisher(page_access_token="")
    with pytest.raises(InstagramPublishError, match="Page access token is required"):
        await no_token_pub.wait_for_container_ready("creation_123")


@pytest.mark.asyncio
async def test_image_publishing_uses_container_polling(publisher):
    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "creation_img_123"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status_code": "FINISHED"}

    publish_resp = MagicMock()
    publish_resp.status_code = 200
    publish_resp.json.return_value = {"id": "post_img_999"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [container_resp, publish_resp]
        mock_client.get.return_value = status_resp

        res = await publisher.publish_image_post(
            ig_user_id="ig_123",
            image_url="http://image.com/pic.jpg",
            caption="Image Caption",
        )

        assert res["id"] == "post_img_999"
        mock_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_video_publishing_uses_container_polling(publisher):
    container_resp = MagicMock()
    container_resp.status_code = 200
    container_resp.json.return_value = {"id": "creation_vid_123"}

    status_resp = MagicMock()
    status_resp.status_code = 200
    status_resp.json.return_value = {"status_code": "FINISHED"}

    publish_resp = MagicMock()
    publish_resp.status_code = 200
    publish_resp.json.return_value = {"id": "post_vid_999"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = [container_resp, publish_resp]
        mock_client.get.return_value = status_resp

        res = await publisher.publish_video_post(
            ig_user_id="ig_123",
            video_url="http://video.com/file.mp4",
            caption="Video Caption",
        )

        assert res["id"] == "post_vid_999"
        mock_client.get.assert_called_once()
