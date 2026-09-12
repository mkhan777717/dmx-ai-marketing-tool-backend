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
async def test_slack_connector_sync_signature_with_provider_kwarg():
    connector = SlackConnector(credentials={}, access_token="xoxb-valid")

    mock_sync_result = {"identity": {"ok": True}, "channels": [], "records_synced": 0}
    with patch(
        "app.integrations.connectors.slack.sync.SlackSyncEngine.perform_sync",
        new_callable=AsyncMock,
        return_value=mock_sync_result,
    ) as mock_perform:
        res = await connector.sync(sync_type="full", provider="slack")
        assert res == mock_sync_result
        mock_perform.assert_called_once_with("full")


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


@pytest.mark.asyncio
async def test_slack_sync_engine_persistence():
    import uuid

    from app.constants.enums import ApiProvider
    from app.integrations.oauth.models import ConnectionStatus, IntegrationConnection
    from app.integrations.sync.engine import SyncEngine

    db_mock = AsyncMock()
    workspace_id = uuid.uuid4()

    mock_conn = IntegrationConnection(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        provider="slack",
        status=ConnectionStatus.CONNECTED,
        access_token="enc_bot_token",
    )

    payload = {
        "workspace_id": str(workspace_id),
        "provider": "slack",
        "sync_type": "full",
    }

    mock_sync_result = {
        "identity": {"ok": True, "team": "Test Workspace"},
        "channels": [
            {"id": "C12345", "name": "general", "is_private": False},
            {"id": "C67890", "name": "random", "is_private": False},
        ],
        "records_synced": 3,
    }

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            new_callable=AsyncMock,
        ) as mock_get_connector,
        patch(
            "app.integrations.sync.engine.secret_service.decrypt_token",
            return_value="raw_xoxb_token",
        ),
        patch(
            "app.integrations.sync.engine.secret_service.encrypt_token",
            return_value="re_enc_token",
        ),
        patch(
            "app.integrations.sync.engine.social_account_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_accounts,
        patch(
            "app.integrations.sync.engine.social_account_repo.create",
            new_callable=AsyncMock,
        ) as mock_create_account,
        patch(
            "app.integrations.sync.engine.social_account_repo.update",
            new_callable=AsyncMock,
        ) as mock_update_account,
    ):
        mock_connector = AsyncMock()
        mock_connector.sync = AsyncMock(return_value=mock_sync_result)
        mock_get_connector.return_value = mock_connector

        # Scenario 1: Initial Sync (accounts do not exist yet)
        mock_get_accounts.return_value = []

        res = await SyncEngine.execute_sync_job(db_mock, payload)

        assert res["records_synced"] == 3
        assert mock_create_account.call_count == 2
        assert mock_update_account.call_count == 0

        first_call = mock_create_account.call_args_list[0][1]["obj_in"]
        assert first_call["workspace_id"] == workspace_id
        assert first_call["provider"] == ApiProvider.SLACK
        assert first_call["account_id"] == "C12345"
        assert first_call["name"] == "general"
        assert first_call["access_token"] == "re_enc_token"
        assert first_call["is_active"] is True

        second_call = mock_create_account.call_args_list[1][1]["obj_in"]
        assert second_call["account_id"] == "C67890"
        assert second_call["name"] == "random"

        # Scenario 2: Repeated Sync (accounts already exist -> idempotent update)
        mock_create_account.reset_mock()
        mock_update_account.reset_mock()
        existing_acc = AsyncMock()
        mock_get_accounts.return_value = [existing_acc]

        await SyncEngine.execute_sync_job(db_mock, payload)

        assert mock_create_account.call_count == 0
        assert mock_update_account.call_count == 2


# ============================================================
# SLACK OAUTH EDGE CASES & URL ENCODING TESTS
# ============================================================


@pytest.mark.asyncio
async def test_slack_oauth_exchange_success_with_optional_fields_missing():
    from unittest.mock import MagicMock

    from app.integrations.connectors.slack.oauth import SlackOAuthHandler

    handler = SlackOAuthHandler(client_id="cid", client_secret="csecret")
    mock_response = {
        "ok": True,
        "access_token": "xoxb-optional-test",
        "team": {"id": "T_OPTIONAL", "name": "Optional Team"},
        # Omitted: is_enterprise_install, app_id, bot_user_id, authed_user
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.json.return_value = mock_response
        mock_post.return_value = mock_http_resp

        res = await handler.exchange_code("auth_code_123")

        assert res["access_token"] == "xoxb-optional-test"
        assert res["team_id"] == "T_OPTIONAL"
        assert res["team_name"] == "Optional Team"
        assert res["bot_user_id"] == "bot"


@pytest.mark.asyncio
async def test_slack_oauth_exchange_non_2xx_error():
    from unittest.mock import MagicMock

    from app.integrations.connectors.slack.exceptions import SlackAuthError
    from app.integrations.connectors.slack.oauth import SlackOAuthHandler

    handler = SlackOAuthHandler(client_id="cid", client_secret="csecret")

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 400
        mock_http_resp.text = '{"error": "invalid_client_credentials"}'
        mock_post.return_value = mock_http_resp

        with pytest.raises(
            SlackAuthError, match="HTTP error during code exchange \\(400\\)"
        ) as exc_info:
            await handler.exchange_code("auth_code_123")

        assert '{"error": "invalid_client_credentials"}' in str(exc_info.value)


@pytest.mark.asyncio
async def test_slack_oauth_exchange_malformed_response_pydantic_error():
    from unittest.mock import MagicMock

    from app.integrations.connectors.slack.exceptions import SlackAuthError
    from app.integrations.connectors.slack.oauth import SlackOAuthHandler

    handler = SlackOAuthHandler(client_id="cid", client_secret="csecret")
    # Response is ok=True but missing required access_token and team
    malformed_response = {"ok": True}

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_http_resp = MagicMock()
        mock_http_resp.status_code = 200
        mock_http_resp.json.return_value = malformed_response
        mock_post.return_value = mock_http_resp

        with pytest.raises(
            SlackAuthError, match="Invalid response format from Slack OAuth"
        ):
            await handler.exchange_code("auth_code_123")


def test_slack_authorization_url_encoding():
    from app.integrations.oauth.manager import OAuthManager

    url = OAuthManager.get_authorization_url(
        provider="slack",
        state="state_test_xyz",
        redirect_uri="http://localhost:8000/api/v1/integrations/oauth/callback",
        client_id="client_slack_999",
    )

    assert "https://slack.com/oauth/v2/authorize?" in url
    assert "client_id=client_slack_999" in url
    assert "state=state_test_xyz" in url
    # Verify redirect_uri and scope are properly URL encoded
    assert (
        "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fintegrations%2Foauth%2Fcallback"
        in url
    )
    assert "scope=chat%3Awrite%2Cchannels%3Aread%2Cgroups%3Aread" in url
