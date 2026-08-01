from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.facebook.connector import FacebookConnector
from app.integrations.connectors.facebook.exceptions import FacebookApiError


@pytest.fixture
def facebook_connector():
    credentials = {"client_id": "test_client_id", "client_secret": "test_client_secret"}
    return FacebookConnector(credentials=credentials)


@pytest.mark.asyncio
async def test_connect_success(facebook_connector):
    mock_token_response = {
        "access_token": "long_lived_token",
        "refresh_token": None,
        "expires_at": datetime.now(timezone.utc),
    }

    mock_profile_response = {"id": "fb_12345", "name": "Jane Doe"}

    with (
        patch(
            "app.integrations.connectors.facebook.oauth.FacebookOAuthHandler.exchange_code",
            new_callable=AsyncMock,
        ) as mock_exchange,
        patch(
            "app.integrations.connectors.facebook.sync.FacebookSyncEngine.fetch_profile",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):

        mock_exchange.return_value = mock_token_response
        mock_fetch.return_value = mock_profile_response

        result = await facebook_connector.connect("dummy_code")

        assert result["access_token"] == "long_lived_token"
        assert result["refresh_token"] is None
        assert result["author_id"] == "fb_12345"
        assert result["profile_name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_validate_success():
    connector = FacebookConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.facebook.sync.FacebookSyncEngine.fetch_profile",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = {"id": "123"}
        is_valid = await connector.validate()
        assert is_valid is True


@pytest.mark.asyncio
async def test_validate_failure():
    connector = FacebookConnector(credentials={}, access_token="invalid_token")

    with patch(
        "app.integrations.connectors.facebook.sync.FacebookSyncEngine.fetch_profile",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = FacebookApiError("Unauthorized", status_code=401)
        is_valid = await connector.validate()
        assert is_valid is False


@pytest.mark.asyncio
async def test_publish_text_post():
    connector = FacebookConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.facebook.publisher.FacebookPublisher.publish_text_post",
        new_callable=AsyncMock,
    ) as mock_pub:
        mock_pub.return_value = {"id": "post_1234"}
        result = await connector.publish(
            "page_123", "Hello Facebook!", "page_access_token_123"
        )
        assert result["id"] == "post_1234"


def test_webhook_verification():
    connector = FacebookConnector(credentials={"client_secret": "secret"})
    payload = b'{"object": "page"}'

    import hashlib
    import hmac

    expected_mac = hmac.new(
        key=b"secret", msg=payload, digestmod=hashlib.sha256
    ).hexdigest()

    signature_header = f"sha256={expected_mac}"

    assert connector.webhook_handler.verify_signature(payload, signature_header) is True
    assert (
        connector.webhook_handler.verify_signature(payload, "sha256=invalid_sig")
        is False
    )
    assert (
        connector.webhook_handler.verify_signature(payload, "invalid_format") is False
    )
