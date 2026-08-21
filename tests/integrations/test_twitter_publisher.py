from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.twitter.exceptions import (
    TwitterAuthError,
    TwitterPublishError,
)
from app.integrations.connectors.twitter.publisher import TwitterPublisher


class MockResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


@pytest.fixture
def publisher():
    return TwitterPublisher(access_token="valid_token")


def test_publisher_requires_token():
    with pytest.raises(TwitterAuthError) as exc_info:
        TwitterPublisher(access_token="")
    assert "Missing access token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_publish_empty_raises_error(publisher):
    with pytest.raises(TwitterPublishError) as exc_info:
        await publisher.publish_post(text="   ")
    assert "Tweet must contain either text or media" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_publish_success(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(
        201, {"data": {"id": "12345", "text": "Hello world"}}
    )

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    post_id = await publisher.publish_post("Hello world", media_ids=["img1"])

    assert post_id == "12345"

    # Verify request
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "https://api.twitter.com/2/tweets"
    assert kwargs["headers"]["Authorization"] == "Bearer valid_token"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["json"]["text"] == "Hello world"
    assert kwargs["json"]["media"]["media_ids"] == ["img1"]


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_publish_missing_id_raises_error(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(201, {"data": {"text": "Hello world"}})

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterPublishError) as exc_info:
        await publisher.publish_post("Hello world")
    assert "missing tweet ID" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_publish_unauthorized(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(401, text="Unauthorized")

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterAuthError) as exc_info:
        await publisher.publish_post("Hello world")
    assert "missing or expired" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_publish_api_error(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(400, text="Bad Request")

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterPublishError) as exc_info:
        await publisher.publish_post("Hello world")
    assert "Twitter API error (400)" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_publish_malformed_json(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(200, text="Not JSON")

    def mock_json():
        raise ValueError("Invalid JSON")

    mock_post.return_value.json = mock_json

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterPublishError) as exc_info:
        await publisher.publish_post("Hello world")
    assert "Malformed JSON response" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_upload_media_success(mock_async_client, publisher):
    mock_post = AsyncMock()

    def side_effect(url, **kwargs):
        if "initialize" in url:
            return MockResponse(202, {"data": {"id": "111222"}})
        elif "append" in url:
            return MockResponse(204, {})
        elif "finalize" in url:
            return MockResponse(
                201,
                {"data": {"id": "111222", "processing_info": {"state": "succeeded"}}},
            )
        return MockResponse(404, {})

    mock_post.side_effect = side_effect

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post
    # GET is not called because state is succeeded immediately

    media_id = await publisher.upload_media(b"fake_bytes", "image/png", 10)
    assert media_id == "111222"
    assert mock_post.call_count == 3


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.publisher.httpx.AsyncClient")
async def test_upload_media_streaming_success(mock_async_client, publisher):
    mock_post = AsyncMock()
    mock_get = AsyncMock()

    def post_side_effect(url, **kwargs):
        if "initialize" in url:
            return MockResponse(202, {"data": {"id": "333444"}})
        elif "append" in url:
            return MockResponse(204, {})
        elif "finalize" in url:
            return MockResponse(
                201,
                {
                    "data": {
                        "id": "333444",
                        "processing_info": {
                            "state": "in_progress",
                            "check_after_secs": 0.01,
                        },
                    }
                },
            )
        return MockResponse(404, {})

    mock_post.side_effect = post_side_effect

    get_calls = 0

    def get_side_effect(url, **kwargs):
        nonlocal get_calls
        get_calls += 1
        if "status" in url:
            if get_calls == 1:
                return MockResponse(
                    200,
                    {
                        "data": {
                            "processing_info": {
                                "state": "in_progress",
                                "check_after_secs": 0.01,
                            }
                        }
                    },
                )
            else:
                return MockResponse(
                    200, {"data": {"processing_info": {"state": "succeeded"}}}
                )
        return MockResponse(404, {})

    mock_get.side_effect = get_side_effect

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post
    mock_client_instance.get = mock_get

    async def stream_generator():
        yield b"chunk1"
        yield b"chunk2"

    media_id = await publisher.upload_media(stream_generator(), "video/mp4", 12)
    assert media_id == "333444"
    assert mock_post.call_count == 4  # INIT, APPEND, APPEND, FINALIZE
    assert mock_get.call_count == 2  # STATUS, STATUS
