from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.integrations.connectors.google.business_profile import (
    GoogleBusinessProfilePublisher,
)
from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)


@pytest.fixture
def publisher():
    return GoogleBusinessProfilePublisher(access_token="test_token")


@pytest.mark.asyncio
async def test_publish_post_success(publisher):
    account_id = "accounts/123/locations/456"
    text = "Hello Google!"

    expected_payload = {
        "languageCode": "en-US",
        "summary": text,
        "topicType": "STANDARD",
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "accounts/123/locations/456/localPosts/789"
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await publisher.publish_post(account_id, text)

        mock_post.assert_called_once_with(
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/localPosts",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            },
            json=expected_payload,
        )
        assert result == "accounts/123/locations/456/localPosts/789"


@pytest.mark.asyncio
async def test_publish_post_with_image_success(publisher):
    account_id = "accounts/123/locations/456"
    text = "Hello Google with Image!"
    image_url = "https://example.com/image.jpg"

    expected_payload = {
        "languageCode": "en-US",
        "summary": text,
        "topicType": "STANDARD",
        "media": [
            {
                "mediaFormat": "PHOTO",
                "sourceUrl": image_url,
            }
        ],
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "name": "accounts/123/locations/456/localPosts/789"
    }

    with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await publisher.publish_post(account_id, text, image_url=image_url)

        mock_post.assert_called_once_with(
            "https://mybusiness.googleapis.com/v4/accounts/123/locations/456/localPosts",
            headers={
                "Authorization": "Bearer test_token",
                "Content-Type": "application/json",
            },
            json=expected_payload,
        )
        assert result == "accounts/123/locations/456/localPosts/789"


@pytest.mark.asyncio
async def test_publish_post_missing_name(publisher):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {}  # missing name

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(GoogleApiError, match="missing 'name' identifier"):
            await publisher.publish_post("accounts/1/locations/2", "text")


@pytest.mark.asyncio
async def test_publish_post_401(publisher):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(GoogleAuthError, match="invalid or expired"):
            await publisher.publish_post("accounts/1/locations/2", "text")


@pytest.mark.asyncio
async def test_publish_post_403(publisher):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(GoogleAuthError, match="Forbidden"):
            await publisher.publish_post("accounts/1/locations/2", "text")


@pytest.mark.asyncio
async def test_publish_post_429(publisher):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(GoogleQuotaError, match="rate limit exceeded"):
            await publisher.publish_post("accounts/1/locations/2", "text")


@pytest.mark.asyncio
async def test_publish_post_500(publisher):
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("httpx.AsyncClient.post", return_value=mock_response):
        with pytest.raises(GoogleApiError) as exc_info:
            await publisher.publish_post("accounts/1/locations/2", "text")

        assert exc_info.value.status_code == 500
        assert "Google API returned error 500" in str(exc_info.value)
        # Verify token isn't in error
        assert "test_token" not in str(exc_info.value)
