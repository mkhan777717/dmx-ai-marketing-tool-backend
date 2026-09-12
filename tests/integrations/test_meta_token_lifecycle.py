from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.facebook.connector import FacebookConnector
from app.integrations.connectors.facebook.exceptions import FacebookApiError
from app.integrations.connectors.facebook.sync import FacebookSyncEngine
from app.integrations.connectors.instagram.connector import InstagramConnector
from app.integrations.connectors.instagram.sync import InstagramSyncEngine
from app.integrations.exceptions import OAuthTokenError


class MockResponse:
    def __init__(self, json_data, status_code, text=""):
        self._json = json_data
        self.status_code = status_code
        self.text = text or str(json_data)

    def json(self):
        if self._json is None:
            raise ValueError("No JSON object could be decoded")
        return self._json


# --- FACEBOOK TESTS ---


@pytest.mark.asyncio
async def test_facebook_valid_token():
    engine = FacebookSyncEngine("valid_token")
    mock_resp = MockResponse({"id": "123", "name": "Jane"}, 200)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        profile = await engine.fetch_profile()
        assert profile["id"] == "123"


@pytest.mark.asyncio
async def test_facebook_perform_sync_metric_excludes_profile():
    engine = FacebookSyncEngine("valid_token")

    with (
        patch.object(
            engine, "fetch_profile", new_callable=AsyncMock
        ) as mock_fetch_profile,
        patch.object(engine, "fetch_pages", new_callable=AsyncMock) as mock_fetch_pages,
    ):
        mock_fetch_profile.return_value = {"id": "123", "name": "Jane"}
        mock_fetch_pages.return_value = []  # User has no pages

        result = await engine.perform_sync("full")

        assert result["records_synced"] == 0
        assert result["profile"]["id"] == "123"


@pytest.mark.asyncio
async def test_facebook_invalid_expired_token():
    engine = FacebookSyncEngine("expired_token")
    # Meta returns OAuthException on invalid tokens
    err_json = {
        "error": {
            "message": "Error validating access token: Session has expired",
            "type": "OAuthException",
            "code": 190,
            "error_subcode": 463,
        }
    }
    mock_resp = MockResponse(err_json, 401, text=str(err_json))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(OAuthTokenError) as exc_info:
            await engine.fetch_profile()
        assert "access token is invalid or expired" in str(exc_info.value)
        # Ensure raw token is not leaked
        assert "expired_token" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_facebook_other_api_error_no_leak():
    engine = FacebookSyncEngine("some_token")
    mock_resp = MockResponse(
        {"error": {"message": "Some other error", "type": "OtherException"}}, 400
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(FacebookApiError) as exc_info:
            await engine.fetch_profile()
        # Verify the exception message doesn't leak raw response (which could theoretically contain sensitive info)
        assert "Status: 400" in str(exc_info.value)
        assert "some_token" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_facebook_connector_validate_handles_expired_token():
    connector = FacebookConnector(credentials={}, access_token="expired_token")
    with patch(
        "app.integrations.connectors.facebook.sync.FacebookSyncEngine.fetch_profile",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = OAuthTokenError(
            "Meta access token is invalid or expired."
        )
        is_valid = await connector.validate()
        assert is_valid is False


# --- INSTAGRAM TESTS ---


@pytest.mark.asyncio
async def test_instagram_valid_token():
    engine = InstagramSyncEngine("valid_token")
    mock_resp = MockResponse(
        {
            "data": [
                {
                    "id": "page_123",
                    "name": "My Page",
                    "access_token": "page_tok",
                    "instagram_business_account": {"id": "ig_123"},
                }
            ]
        },
        200,
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        pages = await engine.fetch_pages_with_instagram()
        assert len(pages) == 1
        assert pages[0]["id"] == "page_123"


@pytest.mark.asyncio
async def test_instagram_invalid_expired_token():
    engine = InstagramSyncEngine("expired_token")
    err_json = {
        "error": {
            "message": "Error validating access token: Session has expired",
            "type": "OAuthException",
            "code": 190,
        }
    }
    mock_resp = MockResponse(err_json, 401, text=str(err_json))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        with pytest.raises(OAuthTokenError) as exc_info:
            await engine.fetch_pages_with_instagram()
        assert "access token is invalid or expired" in str(exc_info.value)
        assert "expired_token" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_instagram_connector_validate_handles_expired_token():
    connector = InstagramConnector(credentials={}, access_token="expired_token")
    with patch(
        "app.integrations.connectors.instagram.sync.InstagramSyncEngine.fetch_pages_with_instagram",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = OAuthTokenError(
            "Meta access token is invalid or expired."
        )
        is_valid = await connector.validate()
        assert is_valid is False
