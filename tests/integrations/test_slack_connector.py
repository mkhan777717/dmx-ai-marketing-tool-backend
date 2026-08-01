import time
from unittest.mock import AsyncMock, patch

import pytest

from app.integrations.connectors.slack.connector import SlackConnector
from app.integrations.connectors.slack.exceptions import SlackApiError


@pytest.fixture
def slack_connector():
    credentials = {
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "signing_secret": "test_signing_secret",
    }
    return SlackConnector(credentials=credentials)


@pytest.mark.asyncio
async def test_connect_success(slack_connector):
    mock_token_response = {
        "access_token": "xoxb-1234",
        "team_id": "T1234",
        "team_name": "Test Team",
        "bot_user_id": "U1234",
        "app_id": "A1234",
    }

    with patch(
        "app.integrations.connectors.slack.oauth.SlackOAuthHandler.exchange_code",
        new_callable=AsyncMock,
    ) as mock_exchange:
        mock_exchange.return_value = mock_token_response

        result = await slack_connector.connect("dummy_code")

        assert result["access_token"] == "xoxb-1234"
        assert result["refresh_token"] is None
        assert result["author_id"] == "U1234"
        assert result["profile_name"] == "Test Team"


@pytest.mark.asyncio
async def test_validate_success():
    connector = SlackConnector(credentials={}, access_token="xoxb-valid")

    with patch(
        "app.integrations.connectors.slack.sync.SlackSyncEngine.verify_auth",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = {"ok": True, "team_id": "T123"}
        is_valid = await connector.validate()
        assert is_valid is True


@pytest.mark.asyncio
async def test_validate_failure():
    connector = SlackConnector(credentials={}, access_token="xoxb-invalid")

    with patch(
        "app.integrations.connectors.slack.sync.SlackSyncEngine.verify_auth",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.side_effect = SlackApiError("invalid_auth")
        is_valid = await connector.validate()
        assert is_valid is False


@pytest.mark.asyncio
async def test_publish_message():
    connector = SlackConnector(credentials={}, access_token="xoxb-valid")

    with patch(
        "app.integrations.connectors.slack.publisher.SlackPublisher.publish_message",
        new_callable=AsyncMock,
    ) as mock_pub:
        mock_pub.return_value = {"ok": True, "ts": "12345.6789", "channel": "C123"}

        result = await connector.publish("C123", "Hello Slack!")
        assert result["ts"] == "12345.6789"
        mock_pub.assert_called_once_with(
            channel_id="C123", text="Hello Slack!", blocks=None, thread_ts=None
        )


def test_webhook_url_verification():
    connector = SlackConnector(credentials={"signing_secret": "secret"})
    payload = {"type": "url_verification", "challenge": "ch_123"}

    result = connector.webhook_handler.verify_challenge(payload)
    assert result == "ch_123"


def test_webhook_signature_verification():
    connector = SlackConnector(credentials={"signing_secret": "secret"})

    timestamp = str(int(time.time()))
    payload = b'{"type": "event_callback"}'

    import hashlib
    import hmac

    sig_basestring = f"v0:{timestamp}:{payload.decode('utf-8')}"
    expected_mac = hmac.new(
        key=b"secret", msg=sig_basestring.encode("utf-8"), digestmod=hashlib.sha256
    ).hexdigest()

    signature_header = f"v0={expected_mac}"

    assert (
        connector.webhook_handler.verify_signature(payload, signature_header, timestamp)
        is True
    )
    assert (
        connector.webhook_handler.verify_signature(payload, "v0=invalid_sig", timestamp)
        is False
    )
    assert (
        connector.webhook_handler.verify_signature(
            payload, signature_header, "1234567890"
        )
        is False
    )  # expired timestamp
