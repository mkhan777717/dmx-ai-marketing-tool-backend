import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Request, Response

from app.integrations.connectors.linkedin.exceptions import LinkedInPublishError
from app.integrations.connectors.linkedin.publisher import LinkedInPublisher


@pytest.fixture
def publisher():
    with patch.dict(os.environ, {"LINKEDIN_API_VERSION": "202608"}):
        return LinkedInPublisher(access_token="test_token")


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_text_post_success(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response = Response(
        201,
        headers={"x-restli-id": "urn:li:share:123"},
        request=Request("POST", "https://api.linkedin.com/rest/posts"),
    )
    mock_client.post.return_value = response

    result = await publisher.publish_text_post(
        author_urn="urn:li:person:author",
        text="Test post",
    )

    assert result == "urn:li:share:123"

    mock_client.post.assert_called_once_with(
        "https://api.linkedin.com/rest/posts",
        json={
            "author": "urn:li:person:author",
            "lifecycleState": "PUBLISHED",
            "commentary": "Test post",
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
        },
        headers=publisher.headers,
    )


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_text_post_error(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response = Response(
        422,
        text='{"message":"ERROR :: /distribution :: field is required"}',
        request=Request("POST", "https://api.linkedin.com/rest/posts"),
    )
    mock_client.post.return_value = response

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_text_post(
            author_urn="urn:li:person:author",
            text="Test post",
        )

    assert "Failed to publish text post" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_success(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    # We will simulate 3 HTTP calls: POST initialize, PUT binary, POST publish

    # 1. Initialize
    response1 = Response(
        200,
        json={
            "value": {"uploadUrl": "https://upload.url", "image": "urn:li:image:123"}
        },
        request=Request(
            "POST", "https://api.linkedin.com/rest/images?action=initializeUpload"
        ),
    )

    # 2. Upload Binary
    response2 = Response(201, request=Request("PUT", "https://upload.url"))

    # 3. Create Post
    response3 = Response(
        201,
        headers={"x-restli-id": "urn:li:share:123"},
        request=Request("POST", "https://api.linkedin.com/rest/posts"),
    )

    # Configure the mock to return responses in sequence based on method
    async def mock_post(url, **kwargs):
        if "action=initializeUpload" in str(url):
            return response1
        return response3

    async def mock_put(url, **kwargs):
        return response2

    mock_client.post.side_effect = mock_post
    mock_client.put.side_effect = mock_put

    result = await publisher.publish_image_post(
        author_urn="urn:li:person:author",
        text="Test post",
        image_binary=b"fakeimage",
        mime_type="image/jpeg",
    )

    assert result == "urn:li:share:123"

    # Assertions for arguments
    mock_client.post.assert_any_call(
        "https://api.linkedin.com/rest/images?action=initializeUpload",
        json={"initializeUploadRequest": {"owner": "urn:li:person:author"}},
        headers=publisher.headers,
    )

    mock_client.put.assert_called_once_with(
        "https://upload.url",
        content=b"fakeimage",
        headers={"Content-Type": "image/jpeg"},
    )

    mock_client.post.assert_any_call(
        "https://api.linkedin.com/rest/posts",
        json={
            "author": "urn:li:person:author",
            "lifecycleState": "PUBLISHED",
            "commentary": "Test post",
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "content": {"media": {"id": "urn:li:image:123"}},
        },
        headers=publisher.headers,
    )


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_initialize_fails(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_client.post.return_value = Response(
        400, text="Bad Request", request=Request("POST", "url")
    )

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_image_post(
            "urn:li:person:author", "Test", b"fake", "image/jpeg"
        )

    assert "Failed to initialize image upload" in str(exc_info.value)
    mock_client.put.assert_not_called()


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_initialize_missing_fields(
    mock_client_class, publisher
):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_client.post.return_value = Response(
        200, json={"value": {}}, request=Request("POST", "url")
    )

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_image_post(
            "urn:li:person:author", "Test", b"fake", "image/jpeg"
        )

    assert "Invalid response from initializeUpload" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_binary_upload_fails(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response1 = Response(
        200,
        json={
            "value": {"uploadUrl": "https://upload.url", "image": "urn:li:image:123"}
        },
        request=Request("POST", "url"),
    )

    response2 = Response(400, text="Upload Failed", request=Request("PUT", "url"))

    async def mock_post(url, **kwargs):
        return response1

    mock_client.post.side_effect = mock_post
    mock_client.put.return_value = response2

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_image_post(
            "urn:li:person:author", "Test", b"fake", "image/jpeg"
        )

    assert "Failed to upload image binary: Upload Failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_create_post_fails(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response1 = Response(
        200,
        json={
            "value": {"uploadUrl": "https://upload.url", "image": "urn:li:image:123"}
        },
        request=Request("POST", "url"),
    )

    response2 = Response(201, request=Request("PUT", "url"))

    response3 = Response(
        400, text="Content format error", request=Request("POST", "url")
    )

    async def mock_post(url, **kwargs):
        if "action=initializeUpload" in str(url):
            return response1
        return response3

    mock_client.post.side_effect = mock_post
    mock_client.put.return_value = response2

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_image_post(
            "urn:li:person:author", "Test", b"fake", "image/jpeg"
        )

    assert "Failed to publish image post: Content format error" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.linkedin.publisher.httpx.AsyncClient")
async def test_publish_image_post_missing_id(mock_client_class, publisher):
    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    response1 = Response(
        200,
        json={
            "value": {"uploadUrl": "https://upload.url", "image": "urn:li:image:123"}
        },
        request=Request("POST", "url"),
    )

    response2 = Response(201, request=Request("PUT", "url"))

    response3 = Response(201, headers={}, request=Request("POST", "url"))

    async def mock_post(url, **kwargs):
        if "action=initializeUpload" in str(url):
            return response1
        return response3

    mock_client.post.side_effect = mock_post
    mock_client.put.return_value = response2

    with pytest.raises(LinkedInPublishError) as exc_info:
        await publisher.publish_image_post(
            "urn:li:person:author", "Test", b"fake", "image/jpeg"
        )

    assert "missing from headers" in str(exc_info.value)
