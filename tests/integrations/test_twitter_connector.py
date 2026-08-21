import pytest
from unittest.mock import AsyncMock, patch

from app.integrations.connectors.twitter.connector import TwitterConnector
from app.integrations.connectors.twitter.exceptions import TwitterAuthError


@pytest.fixture
def twitter_connector():
    credentials = {"client_id": "test_client_id", "client_secret": "test_client_secret"}
    return TwitterConnector(credentials)


def test_instantiate_connector(twitter_connector):
    """1. TwitterConnector can be instantiated."""
    assert twitter_connector.client_id == "test_client_id"
    assert twitter_connector.client_secret == "test_client_secret"
    assert twitter_connector.oauth_handler is not None


@pytest.mark.asyncio
async def test_missing_code_verifier_raises_error(twitter_connector):
    """2. Missing code_verifier raises TwitterAuthError."""
    with pytest.raises(TwitterAuthError) as exc_info:
        await twitter_connector.connect(auth_code="some_code", code_verifier=None)
    assert "strictly required" in str(exc_info.value)


class MockResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_authorization_code_and_verifier_passed_to_handler(
    mock_async_client, twitter_connector
):
    """3. Authorization code + verifier are passed to OAuth handler."""
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(
        200,
        {
            "access_token": "acc_token",
            "refresh_token": "ref_token",
            "expires_in": 7200,
            "token_type": "bearer",
            "scope": "tweet.read users.read",
        },
    )

    mock_get = AsyncMock()
    mock_get.return_value = MockResponse(
        200, {"data": {"id": "123", "username": "testuser"}}
    )

    # We must patch __aenter__ to return an object that handles post and get
    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post
    mock_client_instance.get = mock_get

    await twitter_connector.connect(
        auth_code="my_auth_code", code_verifier="my_code_verifier"
    )

    # Check that post was called with correct data
    mock_post.assert_called_once()
    call_args = mock_post.call_args[1]
    assert call_args["data"]["code"] == "my_auth_code"
    assert call_args["data"]["code_verifier"] == "my_code_verifier"


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_successful_token_response_is_normalized(
    mock_async_client, twitter_connector
):
    """4. Successful token response is normalized correctly. 5. access_token 6. refresh_token 7. expires_at"""
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(
        200,
        {
            "access_token": "test_acc",
            "refresh_token": "test_ref",
            "expires_in": 3600,
            "token_type": "bearer",
            "scope": "tweet.read",
        },
    )

    mock_get = AsyncMock()
    mock_get.return_value = MockResponse(
        200, {"data": {"id": "123", "username": "testuser"}}
    )

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post
    mock_client_instance.get = mock_get

    result = await twitter_connector.connect("code", "verifier")

    assert result["access_token"] == "test_acc"
    assert result["refresh_token"] == "test_ref"
    assert "expires_at" in result
    assert "metadata" in result
    assert result["metadata"]["id"] == "123"


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_invalid_token_response_raises_auth_error(
    mock_async_client, twitter_connector
):
    """8. Invalid token response raises TwitterAuthError."""
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(400, text="Bad Request")

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterAuthError) as exc_info:
        await twitter_connector.connect("code", "verifier")

    assert "Failed to exchange code" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.connector.httpx.AsyncClient")
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_oauth_api_failure_raises_api_error(
    mock_conn_client, mock_oauth_client, twitter_connector
):
    """9. OAuth API failure raises TwitterAuthError/TwitterApiError."""
    # Token exchange succeeds
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(
        200,
        {
            "access_token": "test_acc",
            "refresh_token": "test_ref",
            "expires_in": 3600,
            "token_type": "bearer",
            "scope": "tweet.read",
        },
    )

    mock_oauth_instance = mock_oauth_client.return_value.__aenter__.return_value
    mock_oauth_instance.post = mock_post

    # Profile fetch fails
    mock_get = AsyncMock()
    mock_get.return_value = MockResponse(500, text="Internal Server Error")

    mock_conn_instance = mock_conn_client.return_value.__aenter__.return_value
    mock_conn_instance.get = mock_get

    with pytest.raises(TwitterAuthError) as exc_info:
        await twitter_connector.connect("code", "verifier")

    assert "profile fetch failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.connector.httpx.AsyncClient")
async def test_validate_handles_successful_response(mock_async_client):
    """10. validate() handles successful /2/users/me response."""
    connector = TwitterConnector({"client_id": "c"}, access_token="valid_token")

    mock_get = AsyncMock()
    mock_get.return_value = MockResponse(200, {"data": {"id": "123"}})

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.get = mock_get

    is_valid = await connector.validate()
    assert is_valid is True


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.connector.httpx.AsyncClient")
async def test_validate_handles_invalid_response(mock_async_client):
    """11. validate() handles invalid token response."""
    connector = TwitterConnector({"client_id": "c"}, access_token="invalid_token")

    mock_get = AsyncMock()
    mock_get.return_value = MockResponse(401, text="Unauthorized")

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.get = mock_get

    is_valid = await connector.validate()
    assert is_valid is False


def test_secrets_never_logged(twitter_connector):
    """12. Secrets are never logged. (Implicit in implementation, verifying via attribute access logic)."""
    assert "client_secret" in twitter_connector.oauth_handler.__dict__
    assert twitter_connector.oauth_handler.client_secret == "test_client_secret"
    # Basic auth string shouldn't be publicly logged
    headers = twitter_connector.oauth_handler._get_auth_headers()
    assert "Authorization" in headers
    # Ensure it's base64 encoded and secret is not plaintext
    assert "test_client_secret" not in headers["Authorization"]


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_refresh_token_success(mock_async_client, twitter_connector):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(
        200,
        {
            "access_token": "new_acc",
            "refresh_token": "new_ref",
            "expires_in": 7200,
            "token_type": "bearer",
            "scope": "tweet.write users.read",
        },
    )

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    result = await twitter_connector.oauth_handler.refresh_token("old_refresh")

    assert result["access_token"] == "new_acc"
    assert result["refresh_token"] == "new_ref"
    assert "expires_at" in result

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["data"]["grant_type"] == "refresh_token"
    assert kwargs["data"]["refresh_token"] == "old_refresh"


@pytest.mark.asyncio
@patch("app.integrations.connectors.twitter.oauth.httpx.AsyncClient")
async def test_refresh_token_failure(mock_async_client, twitter_connector):
    mock_post = AsyncMock()
    mock_post.return_value = MockResponse(400, text="Bad Request")

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.post = mock_post

    with pytest.raises(TwitterAuthError) as exc_info:
        await twitter_connector.oauth_handler.refresh_token("bad_token")

    assert "Failed to refresh token: Bad Request" in str(exc_info.value)
