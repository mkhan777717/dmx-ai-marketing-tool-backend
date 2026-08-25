from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)
from app.integrations.connectors.google.youtube import YouTubePublisher


@pytest.fixture
def publisher():
    return YouTubePublisher(access_token="test_token")


@pytest.fixture
def valid_asset():
    return {
        "asset_url": "https://example.com/video.mp4",
        "title": "My Test Video",
        "description": "Test Description",
        "file_size": 1000,
        "mime_type": "video/mp4",
    }


@pytest.mark.asyncio
async def test_upload_video_success(publisher, valid_asset):
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 200
    mock_post_resp.headers = {"Location": "https://upload.youtube.com/location"}

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200

    async def mock_aiter_bytes(*args, **kwargs):
        yield b"chunk1"
        yield b"chunk2"

    mock_stream_resp.aiter_bytes = mock_aiter_bytes

    mock_put_resp = MagicMock(spec=httpx.Response)
    mock_put_resp.status_code = 200
    mock_put_resp.json.return_value = {"id": "yt_video_123"}

    # We need to mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.put = AsyncMock(return_value=mock_put_resp)
        mock_client.stream.return_value.__aenter__.return_value = mock_stream_resp

        result = await publisher.upload_video(**valid_asset)

        assert result == "yt_video_123"

        # Verify initialization request
        mock_client.post.assert_called_once()
        args, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_token"
        assert kwargs["headers"]["X-Upload-Content-Length"] == "1000"
        assert kwargs["json"]["snippet"]["title"] == "My Test Video"

        # Verify PUT request
        mock_client.put.assert_called_once()
        put_args, put_kwargs = mock_client.put.call_args
        assert put_args[0] == "https://upload.youtube.com/location"
        assert put_kwargs["headers"]["Content-Length"] == "1000"
        assert put_kwargs["headers"]["Content-Range"] == "bytes 0-999/1000"


@pytest.mark.asyncio
async def test_upload_video_initialization_fails(publisher, valid_asset):
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 401

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_post_resp)

        with pytest.raises(GoogleAuthError, match="invalid or expired"):
            await publisher.upload_video(**valid_asset)


@pytest.mark.asyncio
async def test_upload_video_missing_location(publisher, valid_asset):
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 200
    mock_post_resp.headers = {}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.post = AsyncMock(return_value=mock_post_resp)

        with pytest.raises(GoogleApiError, match="missing Location header"):
            await publisher.upload_video(**valid_asset)


@pytest.mark.asyncio
async def test_upload_video_put_fails_with_quota(publisher, valid_asset):
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 200
    mock_post_resp.headers = {"Location": "https://upload.youtube.com/location"}

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200

    async def mock_aiter_bytes(*args, **kwargs):
        yield b"chunk1"

    mock_stream_resp.aiter_bytes = mock_aiter_bytes

    mock_put_resp_429 = MagicMock(spec=httpx.Response)
    mock_put_resp_429.status_code = 429

    mock_status_resp = MagicMock(spec=httpx.Response)
    mock_status_resp.status_code = 429

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.stream.return_value.__aenter__.return_value = mock_stream_resp
        # Return 429 for the upload put, and 429 for the recovery put
        mock_client.put = AsyncMock(
            side_effect=[
                mock_put_resp_429,
                mock_status_resp,
                mock_put_resp_429,
                mock_status_resp,
                mock_put_resp_429,
                mock_status_resp,
            ]
        )

        with pytest.raises(GoogleQuotaError, match="YouTube rate limit exceeded"):
            await publisher.upload_video(**valid_asset)


@pytest.mark.asyncio
async def test_upload_video_resumes_on_308(publisher, valid_asset):
    mock_post_resp = MagicMock(spec=httpx.Response)
    mock_post_resp.status_code = 200
    mock_post_resp.headers = {"Location": "https://upload.youtube.com/location"}

    mock_stream_resp = MagicMock()
    mock_stream_resp.status_code = 200

    async def mock_aiter_bytes(*args, **kwargs):
        yield b"chunk1"

    mock_stream_resp.aiter_bytes = mock_aiter_bytes

    # First PUT returns 308 Resume Incomplete
    mock_put_resp_308 = MagicMock(spec=httpx.Response)
    mock_put_resp_308.status_code = 308
    mock_put_resp_308.headers = {"Range": "bytes=0-499"}

    # Second PUT returns 200 OK
    mock_put_resp_200 = MagicMock(spec=httpx.Response)
    mock_put_resp_200.status_code = 200
    mock_put_resp_200.json.return_value = {"id": "yt_video_456"}

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_client.post = AsyncMock(return_value=mock_post_resp)
        mock_client.stream.return_value.__aenter__.return_value = mock_stream_resp
        mock_client.put = AsyncMock(side_effect=[mock_put_resp_308, mock_put_resp_200])

        result = await publisher.upload_video(**valid_asset)
        assert result == "yt_video_456"

        # Verify 2 PUTs were made
        assert mock_client.put.call_count == 2
        args2, kwargs2 = mock_client.put.call_args_list[1]
        assert kwargs2["headers"]["Content-Range"] == "bytes 500-999/1000"
