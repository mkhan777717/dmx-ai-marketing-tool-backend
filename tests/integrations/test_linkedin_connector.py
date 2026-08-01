from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.linkedin.connector import LinkedInConnector
from app.integrations.connectors.linkedin.exceptions import LinkedInApiError


@pytest.fixture
def linkedin_connector():
    credentials = {"client_id": "test_client_id", "client_secret": "test_client_secret"}
    return LinkedInConnector(credentials=credentials)


@pytest.mark.asyncio
async def test_connect_success(linkedin_connector):
    mock_token_response = {
        "access_token": "mock_access",
        "refresh_token": "mock_refresh",
        "expires_at": datetime.now(timezone.utc),
    }

    mock_profile_response = {
        "id": "12345",
        "localizedFirstName": "John",
        "localizedLastName": "Doe",
    }

    with (
        patch(
            "app.integrations.connectors.linkedin.oauth.LinkedInOAuthHandler.exchange_code",
            new_callable=AsyncMock,
        ) as mock_exchange,
        patch(
            "app.integrations.connectors.linkedin.sync.LinkedInSyncEngine.fetch_profile",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):

        mock_exchange.return_value = mock_token_response
        mock_fetch.return_value = mock_profile_response

        result = await linkedin_connector.connect("dummy_code")

        assert result["access_token"] == "mock_access"
        assert result["refresh_token"] == "mock_refresh"
        assert result["author_urn"] == "urn:li:person:12345"
        assert result["profile_name"] == "John Doe"


@pytest.mark.asyncio
async def test_validate_success():
    connector = LinkedInConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.linkedin.sync.LinkedInSyncEngine.fetch_profile",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = {"id": "123"}
        is_valid = await connector.validate()
        assert is_valid is True


@pytest.mark.asyncio
async def test_validate_failure():
    connector = LinkedInConnector(credentials={}, access_token="invalid_token")

    with patch(
        "app.integrations.connectors.linkedin.sync.LinkedInSyncEngine.fetch_profile",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = LinkedInApiError("Unauthorized", status_code=401)
        is_valid = await connector.validate()
        assert is_valid is False


@pytest.mark.asyncio
async def test_publish_text_post():
    connector = LinkedInConnector(credentials={}, access_token="valid_token")

    with patch(
        "app.integrations.connectors.linkedin.publisher.LinkedInPublisher.publish_text_post",
        new_callable=AsyncMock,
    ) as mock_pub:
        mock_pub.return_value = {"id": "urn:li:share:123"}
        result = await connector.publish("urn:li:person:123", "Hello LinkedIn!")
        assert result["id"] == "urn:li:share:123"


def test_webhook_verification():
    connector = LinkedInConnector(credentials={"client_secret": "secret"})
    payload = b'{"type": "COMMENT"}'

    import hashlib
    import hmac

    valid_signature = hmac.new(
        key=b"secret", msg=payload, digestmod=hashlib.sha256
    ).hexdigest()

    assert connector.webhook_handler.verify_signature(payload, valid_signature) is True
    assert connector.webhook_handler.verify_signature(payload, "invalid_sig") is False
