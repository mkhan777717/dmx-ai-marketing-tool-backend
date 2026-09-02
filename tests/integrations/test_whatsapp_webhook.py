import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.constants.enums import PublishStatus
from app.integrations.connectors.whatsapp.webhook import WhatsAppWebhookHandler
from app.integrations.exceptions import WebhookVerificationError
from app.main import app
from app.models.publish_history import PublishHistory
from app.models.social_account import SocialAccount


@pytest.fixture
def webhook_handler():
    return WhatsAppWebhookHandler(client_secret="test_wa_client_secret_999")


@pytest.fixture
def mock_secret_service():
    with patch("app.integrations.webhooks.verifier.secret_service") as mock_secret:
        mock_secret.get_provider_credentials.return_value = {
            "client_id": "wa_client_123",
            "client_secret": "test_wa_client_secret_999",
        }
        yield mock_secret


# ============================================================
# 1. GET VERIFICATION TESTS
# ============================================================


def test_verify_challenge_success(webhook_handler):
    challenge = webhook_handler.verify_challenge(
        mode="subscribe",
        verify_token="my_secret_verify_token",
        challenge="challenge_code_12345",
        expected_verify_token="my_secret_verify_token",
    )
    assert challenge == "challenge_code_12345"


def test_verify_challenge_invalid_token(webhook_handler):
    with pytest.raises(WebhookVerificationError, match="Invalid verify token or mode"):
        webhook_handler.verify_challenge(
            mode="subscribe",
            verify_token="wrong_token",
            challenge="challenge_code_12345",
            expected_verify_token="my_secret_verify_token",
        )


def test_verify_challenge_invalid_mode(webhook_handler):
    with pytest.raises(WebhookVerificationError, match="Invalid verify token or mode"):
        webhook_handler.verify_challenge(
            mode="unsubscribe",
            verify_token="my_secret_verify_token",
            challenge="challenge_code_12345",
            expected_verify_token="my_secret_verify_token",
        )


# ============================================================
# 2. POST HMAC SIGNATURE TESTS
# ============================================================


def test_post_signature_verification_success(webhook_handler):
    payload = b'{"object":"whatsapp_business_account","entry":[]}'
    expected_mac = hmac.new(
        key=b"test_wa_client_secret_999",
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()
    sig_header = f"sha256={expected_mac}"

    assert webhook_handler.verify_signature(payload, sig_header) is True


def test_post_signature_verification_invalid(webhook_handler):
    payload = b'{"object":"whatsapp_business_account","entry":[]}'
    sig_header = "sha256=invalid_mac_hash_code"

    assert webhook_handler.verify_signature(payload, sig_header) is False


def test_post_signature_verification_missing_header(webhook_handler):
    payload = b'{"object":"whatsapp_business_account","entry":[]}'
    assert webhook_handler.verify_signature(payload, "") is False


def test_post_signature_verification_malformed_header(webhook_handler):
    payload = b'{"object":"whatsapp_business_account","entry":[]}'
    assert webhook_handler.verify_signature(payload, "invalid_prefix_hash") is False


# ============================================================
# 3. INCOMING MESSAGE PARSING TESTS
# ============================================================


def test_parse_incoming_text_message(webhook_handler):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba_id_111",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550199",
                                "phone_number_id": "phone_num_id_555",
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Alice Smith"},
                                    "wa_id": "15559998888",
                                }
                            ],
                            "messages": [
                                {
                                    "from": "15559998888",
                                    "id": "wamid.INCOMING_001",
                                    "timestamp": "1700000000",
                                    "text": {"body": "Hello support, I need help"},
                                    "type": "text",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    parsed = webhook_handler.parse_webhook_payload(payload)
    assert parsed["phone_number_id"] == "phone_num_id_555"
    assert len(parsed["messages"]) == 1

    msg = parsed["messages"][0]
    assert msg["message_id"] == "wamid.INCOMING_001"
    assert msg["from"] == "15559998888"
    assert msg["sender_name"] == "Alice Smith"
    assert msg["type"] == "text"
    assert msg["body"] == "Hello support, I need help"


def test_parse_incoming_message_missing_optional_fields(webhook_handler):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "15559998888",
                                    "id": "wamid.INCOMING_002",
                                    "type": "unknown",
                                }
                            ]
                        }
                    }
                ]
            }
        ],
    }

    parsed = webhook_handler.parse_webhook_payload(payload)
    assert len(parsed["messages"]) == 1
    assert parsed["messages"][0]["message_id"] == "wamid.INCOMING_002"
    assert parsed["messages"][0]["body"] is None


# ============================================================
# 4. STATUS EVENT PARSING TESTS
# ============================================================


def test_parse_status_events(webhook_handler):
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone_num_id_555"},
                            "statuses": [
                                {
                                    "id": "wamid.OUTBOUND_001",
                                    "status": "sent",
                                    "timestamp": "1700000100",
                                    "recipient_id": "15550199",
                                },
                                {
                                    "id": "wamid.OUTBOUND_002",
                                    "status": "delivered",
                                    "timestamp": "1700000200",
                                    "recipient_id": "15550199",
                                },
                                {
                                    "id": "wamid.OUTBOUND_003",
                                    "status": "read",
                                    "timestamp": "1700000300",
                                    "recipient_id": "15550199",
                                },
                                {
                                    "id": "wamid.OUTBOUND_004",
                                    "status": "failed",
                                    "timestamp": "1700000400",
                                    "recipient_id": "15550199",
                                    "errors": [
                                        {
                                            "code": 131026,
                                            "title": "Message undeliverable",
                                        }
                                    ],
                                },
                            ],
                        }
                    }
                ]
            }
        ],
    }

    parsed = webhook_handler.parse_webhook_payload(payload)
    statuses = parsed["statuses"]
    assert len(statuses) == 4

    assert statuses[0]["status"] == "sent"
    assert statuses[1]["status"] == "delivered"
    assert statuses[2]["status"] == "read"
    assert statuses[3]["status"] == "failed"
    assert "Code 131026: Message undeliverable" in statuses[3]["error_detail"]


# ============================================================
# 5. API ROUTE & DB STATUS INTEGRATION TESTS
# ============================================================


@pytest.mark.asyncio
async def test_get_webhook_verification_route_success(mock_secret_service):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "secret_verify_token_999"

        client = TestClient(app)
        res = client.get(
            "/api/v1/integrations/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "secret_verify_token_999",
                "hub.challenge": "echo_challenge_12345",
            },
        )

        assert res.status_code == 200
        assert res.text == "echo_challenge_12345"


@pytest.mark.asyncio
async def test_get_webhook_verification_route_token_mismatch(mock_secret_service):
    with patch("os.getenv") as mock_getenv:
        mock_getenv.return_value = "secret_verify_token_999"

        client = TestClient(app)
        res = client.get(
            "/api/v1/integrations/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "echo_challenge_12345",
            },
        )

        assert res.status_code == 403


@pytest.mark.asyncio
async def test_post_webhook_route_valid_signature_and_status_update(
    mock_secret_service,
):
    payload_dict = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone_num_id_555"},
                            "statuses": [
                                {
                                    "id": "wamid.DELIVERED_001",
                                    "status": "delivered",
                                    "timestamp": "1700000200",
                                    "recipient_id": "15550199",
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }
    import json

    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    mac = hmac.new(
        key=b"test_wa_client_secret_999",
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    sig_header = f"sha256={mac}"

    ws_id = uuid.uuid4()
    social_acc = SocialAccount(
        id=uuid.uuid4(), workspace_id=ws_id, account_id="phone_num_id_555"
    )
    pub_rec = PublishHistory(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        external_post_id="wamid.DELIVERED_001",
        status=PublishStatus.SENT,
    )

    with (
        patch(
            "app.repositories.social_account.social_account_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_acc,
        patch(
            "app.repositories.publish_history.publish_history_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_pub,
        patch(
            "app.repositories.publish_history.publish_history_repo.update",
            new_callable=AsyncMock,
        ) as mock_update_pub,
        patch(
            "app.integrations.webhooks.dispatcher.WebhookDispatcher.dispatch",
            new_callable=AsyncMock,
        ),
    ):

        mock_get_acc.return_value = [social_acc]
        mock_get_pub.return_value = [pub_rec]

        client = TestClient(app)
        res = client.post(
            "/api/v1/integrations/webhooks/whatsapp",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": sig_header,
                "Content-Type": "application/json",
            },
        )

        assert res.status_code == 200
        assert res.json() == {"status": "accepted"}

        # Verify PublishHistory was updated to DELIVERED
        mock_update_pub.assert_called_once()
        _, update_kwargs = mock_update_pub.call_args
        assert update_kwargs["obj_in"]["status"] == PublishStatus.DELIVERED


# ============================================================
# 6. IDEMPOTENCY TESTS
# ============================================================


@pytest.mark.asyncio
async def test_idempotency_read_status_does_not_regress_to_sent(mock_secret_service):
    payload_dict = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone_num_id_555"},
                            "statuses": [
                                {
                                    "id": "wamid.READ_001",
                                    "status": "sent",  # Delayed sent status delivered out of order
                                    "timestamp": "1700000000",
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }
    import json

    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    mac = hmac.new(
        key=b"test_wa_client_secret_999",
        msg=payload_bytes,
        digestmod=hashlib.sha256,
    ).hexdigest()
    sig_header = f"sha256={mac}"

    ws_id = uuid.uuid4()
    social_acc = SocialAccount(
        id=uuid.uuid4(), workspace_id=ws_id, account_id="phone_num_id_555"
    )
    # Record already in READ status
    pub_rec = PublishHistory(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        external_post_id="wamid.READ_001",
        status=PublishStatus.READ,
    )

    with (
        patch(
            "app.repositories.social_account.social_account_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_acc,
        patch(
            "app.repositories.publish_history.publish_history_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_pub,
        patch(
            "app.repositories.publish_history.publish_history_repo.update",
            new_callable=AsyncMock,
        ) as mock_update_pub,
    ):

        mock_get_acc.return_value = [social_acc]
        mock_get_pub.return_value = [pub_rec]

        client = TestClient(app)
        res = client.post(
            "/api/v1/integrations/webhooks/whatsapp",
            content=payload_bytes,
            headers={
                "X-Hub-Signature-256": sig_header,
                "Content-Type": "application/json",
            },
        )

        assert res.status_code == 200

        # Verify update was skipped due to idempotency regression protection
        mock_update_pub.assert_not_called()


# ============================================================
# 7. SECURITY NON-LEAKAGE TESTS
# ============================================================


def test_security_verify_token_and_secrets_never_in_exception():
    handler = WhatsAppWebhookHandler(client_secret="SUPER_SECRET_CLIENT_KEY_999")
    with pytest.raises(WebhookVerificationError) as exc_info:
        handler.verify_challenge(
            mode="subscribe",
            verify_token="wrong_token",
            challenge="ch_123",
            expected_verify_token="CONFIDENTIAL_VERIFY_TOKEN_888",
        )

    assert "SUPER_SECRET_CLIENT_KEY_999" not in str(exc_info.value)
    assert "CONFIDENTIAL_VERIFY_TOKEN_888" not in str(exc_info.value)
