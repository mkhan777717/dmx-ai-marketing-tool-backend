from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.instagram.connector import InstagramConnector
from app.integrations.connectors.instagram.exceptions import InstagramApiError


@pytest.fixture
def instagram_connector():
    credentials = {"client_id": "test_client_id", "client_secret": "test_client_secret"}
    return InstagramConnector(credentials=credentials)


@pytest.mark.asyncio
async def test_connect_success(instagram_connector):
    mock_token_response = {
        "access_token": "long_lived_token",
        "refresh_token": None,
        "expires_at": datetime.now(timezone.utc),
    }

    # Mocking the complex discovery process
    mock_sync_response = {
        "instagram_accounts": [
            {
                "id": "ig_12345",
                "username": "test_business",
                "name": "Test Business",
                "profile_picture_url": "https://example.com/pic.jpg",
                "linked_page_id": "page_123",
                "page_access_token": "page_token_123",
            }
        ],
        "records_synced": 1,
    }

    with (
        patch(
            "app.integrations.connectors.instagram.oauth.InstagramOAuthHandler.exchange_code",
            new_callable=AsyncMock,
        ) as mock_exchange,
        patch(
            "app.integrations.connectors.instagram.sync.InstagramSyncEngine.perform_sync",
            new_callable=AsyncMock,
        ) as mock_sync,
    ):
        mock_exchange.return_value = mock_token_response
        mock_sync.return_value = mock_sync_response

        result = await instagram_connector.connect("dummy_code")

        assert result["access_token"] == "long_lived_token"
        assert result["refresh_token"] is None
        assert result["author_id"] == "ig_12345"
        assert result["profile_name"] == "test_business"


@pytest.mark.asyncio
async def test_validate_success():
    connector = InstagramConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.instagram.sync.InstagramSyncEngine.fetch_pages_with_instagram",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [{"id": "page_1"}]
        is_valid = await connector.validate()
        assert is_valid is True


@pytest.mark.asyncio
async def test_validate_failure():
    connector = InstagramConnector(credentials={}, access_token="invalid_token")

    with patch(
        "app.integrations.connectors.instagram.sync.InstagramSyncEngine.fetch_pages_with_instagram",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = InstagramApiError("Unauthorized", status_code=401)
        is_valid = await connector.validate()
        assert is_valid is False


@pytest.mark.asyncio
async def test_publish_image_post():
    connector = InstagramConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.instagram.publisher.InstagramPublisher.publish_image_post",
        new_callable=AsyncMock,
    ) as mock_pub:
        mock_pub.return_value = {"id": "ig_post_1234"}
        # page_id is effectively the ig_user_id for Instagram
        result = await connector.publish(
            "ig_1234",
            "Hello IG!",
            "page_access_token_123",
            image_url="http://image.com/pic.jpg",
        )
        assert result["id"] == "ig_post_1234"


def test_webhook_verification():
    connector = InstagramConnector(credentials={"client_secret": "secret"})
    payload = b'{"object": "instagram"}'

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
