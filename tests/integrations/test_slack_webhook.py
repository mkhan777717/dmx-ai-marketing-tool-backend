import hashlib
import hmac
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.integrations.webhooks.verifier import WebhookVerifier
from app.main import app


@pytest.fixture
def signing_secret():
    return "test_slack_signing_secret_12345"


def generate_slack_headers(payload_bytes: bytes, secret: str, timestamp: str = None):
    if timestamp is None:
        timestamp = str(int(time.time()))
    sig_basestring = f"v0:{timestamp}:{payload_bytes.decode('utf-8')}"
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=sig_basestring.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return {
        "X-Slack-Signature": f"v0={mac}",
        "X-Slack-Request-Timestamp": timestamp,
    }


# ============================================================
# 1. WEBHOOK VERIFIER UNIT TESTS
# ============================================================


@pytest.mark.asyncio
async def test_slack_webhook_verifier_valid_signature(signing_secret):
    payload = b'{"type": "event_callback"}'
    headers = generate_slack_headers(payload, signing_secret)

    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.side_effect = lambda key, default="": headers.get(
        key, default
    )

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        res = await WebhookVerifier.verify_signature("slack", mock_request, payload)
        assert res is True


@pytest.mark.asyncio
async def test_slack_webhook_verifier_invalid_signature(signing_secret):
    payload = b'{"type": "event_callback"}'
    timestamp = str(int(time.time()))
    headers = {
        "X-Slack-Signature": "v0=invalid_mac_hash",
        "X-Slack-Request-Timestamp": timestamp,
    }

    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.side_effect = lambda key, default="": headers.get(
        key, default
    )

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        res = await WebhookVerifier.verify_signature("slack", mock_request, payload)
        assert res is False


@pytest.mark.asyncio
async def test_slack_webhook_verifier_expired_timestamp(signing_secret):
    payload = b'{"type": "event_callback"}'
    # Timestamp set to 10 minutes in the past
    old_timestamp = str(int(time.time()) - 600)
    headers = generate_slack_headers(payload, signing_secret, timestamp=old_timestamp)

    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.side_effect = lambda key, default="": headers.get(
        key, default
    )

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        res = await WebhookVerifier.verify_signature("slack", mock_request, payload)
        assert res is False


@pytest.mark.asyncio
async def test_slack_webhook_verifier_invalid_timestamp_format(signing_secret):
    payload = b'{"type": "event_callback"}'
    headers = {
        "X-Slack-Signature": "v0=some_mac",
        "X-Slack-Request-Timestamp": "not_an_integer",
    }

    mock_request = MagicMock(spec=Request)
    mock_request.headers.get.side_effect = lambda key, default="": headers.get(
        key, default
    )

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        res = await WebhookVerifier.verify_signature("slack", mock_request, payload)
        assert res is False


# ============================================================
# 2. ENDPOINT API TESTS (url_verification challenge & POST)
# ============================================================


def test_slack_webhook_endpoint_url_verification_challenge(signing_secret):
    import json

    payload_dict = {
        "type": "url_verification",
        "token": "slack_token_xyz",
        "challenge": "challenge_token_999888",
    }
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    slack_headers = generate_slack_headers(payload_bytes, signing_secret)
    slack_headers["Content-Type"] = "application/json"

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        client = TestClient(app)
        res = client.post(
            "/api/v1/integrations/webhooks/slack",
            content=payload_bytes,
            headers=slack_headers,
        )

        assert res.status_code == 200
        assert res.json() == {"challenge": "challenge_token_999888"}


def test_slack_webhook_endpoint_invalid_signature(signing_secret):
    import json

    payload_dict = {"type": "url_verification", "challenge": "ch_123"}
    payload_bytes = json.dumps(payload_dict).encode("utf-8")
    headers = {
        "X-Slack-Signature": "v0=invalid_sig",
        "X-Slack-Request-Timestamp": str(int(time.time())),
        "Content-Type": "application/json",
    }

    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "signing_secret": signing_secret
        }
        client = TestClient(app)
        res = client.post(
            "/api/v1/integrations/webhooks/slack",
            content=payload_bytes,
            headers=headers,
        )

        assert res.status_code == 401
        assert res.json()["detail"] == "Invalid webhook signature"
