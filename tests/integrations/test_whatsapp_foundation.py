import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.enums import ApiProvider
from app.integrations.connectors.whatsapp.connector import WhatsAppConnector
from app.integrations.connectors.whatsapp.exceptions import (
    WhatsAppApiError,
)
from app.integrations.connectors.whatsapp.oauth import WhatsAppOAuthHandler
from app.integrations.connectors.whatsapp.sync import WhatsAppSyncEngine
from app.integrations.exceptions import OAuthTokenError
from app.integrations.oauth.manager import OAuthManager
from app.integrations.oauth.service import IntegrationService
from app.integrations.registry import ConnectorFactory, ConnectorRegistry
from app.integrations.secrets.service import secret_service
from app.models.social_account import SocialAccount
from app.services.social.factory import SocialProviderFactory
from app.services.social.whatsapp_provider import WhatsAppProvider


@pytest.fixture
def mock_secret_service():
    with patch("app.integrations.secrets.service.secret_service") as mock_secret:
        mock_secret.decrypt_token.side_effect = lambda t: f"decrypted_{t}" if t else ""
        mock_secret.encrypt_token.side_effect = lambda t: f"encrypted_{t}" if t else ""
        mock_secret.get_provider_credentials.return_value = {
            "client_id": "wa_client_123",
            "client_secret": "wa_secret_456",
        }
        yield mock_secret


# 1. WhatsApp Enum Test
def test_whatsapp_enum_value():
    assert ApiProvider.WHATSAPP.value == "WHATSAPP"


# 2. Credential Resolution Test
def test_whatsapp_credential_resolution_fallback():
    # Test that get_provider_credentials("whatsapp") falls back to FACEBOOK_CLIENT_ID if WHATSAPP_CLIENT_ID is not set
    with patch.object(secret_service.adapter, "get_secret") as mock_get:

        def secret_side(key):
            if key == "FACEBOOK_CLIENT_ID":
                return "meta_app_id_999"
            if key == "FACEBOOK_CLIENT_SECRET":
                return "meta_app_sec_888"
            return None

        mock_get.side_effect = secret_side
        creds = secret_service.get_provider_credentials("whatsapp")
        assert creds["client_id"] == "meta_app_id_999"
        assert creds["client_secret"] == "meta_app_sec_888"


# 3. Authorization URL Generation Test
def test_whatsapp_authorization_url_generation():
    state = OAuthManager.generate_state("ws_123", "whatsapp")
    url = OAuthManager.get_authorization_url(
        provider="whatsapp",
        state=state,
        redirect_uri="http://localhost:8000/callback",
        client_id="app_123",
    )
    assert "https://www.facebook.com/" in url
    assert "client_id=app_123" in url
    assert "whatsapp_business_management" in url
    assert "whatsapp_business_messaging" in url


# 4. OAuth State Handling Test
def test_whatsapp_oauth_state_handling():
    state = OAuthManager.generate_state("ws_999", "whatsapp")
    val = OAuthManager.validate_state(state)
    assert val is not None
    assert val["workspace_id"] == "ws_999"
    assert val["provider"] == "whatsapp"

    # Single-use state check
    assert OAuthManager.validate_state(state) is None


# 5. Successful Token Exchange Test
@pytest.mark.asyncio
async def test_whatsapp_token_exchange_success():
    handler = WhatsAppOAuthHandler(client_id="cid", client_secret="csec")

    short_token_resp = MagicMock(
        status_code=200, json=lambda: {"access_token": "short_tok_123"}
    )
    long_token_resp = MagicMock(
        status_code=200,
        json=lambda: {"access_token": "long_tok_456", "expires_in": 5184000},
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [short_token_resp, long_token_resp]

        res = await handler.exchange_code("auth_code_777")
        assert res["access_token"] == "long_tok_456"
        assert res["refresh_token"] is None
        assert res["expires_at"] is not None


# 6. WABA Discovery Success Test
@pytest.mark.asyncio
async def test_waba_discovery_success():
    engine = WhatsAppSyncEngine(access_token="tok_123")

    debug_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "data": {
                "granular_scopes": [
                    {
                        "scope": "whatsapp_business_management",
                        "target_ids": ["waba_id_001"],
                    }
                ]
            }
        },
    )
    b_resp = MagicMock(status_code=200, json=lambda: {"data": []})
    waba_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "id": "waba_id_001",
            "name": "My Business WABA",
            "currency": "USD",
            "timezone_id": "UTC",
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [debug_resp, b_resp, waba_resp]

        wabas = await engine.fetch_wabas()
        assert len(wabas) == 1
        assert wabas[0]["id"] == "waba_id_001"
        assert wabas[0]["name"] == "My Business WABA"


# 7. No WABA Found Test
@pytest.mark.asyncio
async def test_waba_discovery_empty():
    engine = WhatsAppSyncEngine(access_token="tok_123")
    empty_resp = MagicMock(status_code=200, json=lambda: {"data": []})
    me_resp = MagicMock(
        status_code=200, json=lambda: {"id": "user_123", "name": "Test User"}
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = [empty_resp, empty_resp, me_resp]

        wabas = await engine.fetch_wabas()
        assert len(wabas) == 0


# 8. WABA API Failure Test
@pytest.mark.asyncio
async def test_waba_discovery_api_failure():
    engine = WhatsAppSyncEngine(access_token="tok_123")
    fail_resp = MagicMock(
        status_code=401,
        json=lambda: {
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
            }
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = fail_resp

        with pytest.raises(OAuthTokenError, match="invalid or expired"):
            await engine.fetch_wabas()


# 9. Phone Number Discovery Success Test
@pytest.mark.asyncio
async def test_phone_number_discovery_success():
    engine = WhatsAppSyncEngine(access_token="tok_123")

    pn_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "data": [
                {
                    "id": "phone_num_id_999",
                    "display_phone_number": "+1 555-0199",
                    "verified_name": "Acme Support",
                    "code_verification_status": "VERIFIED",
                    "quality_rating": "GREEN",
                }
            ]
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = pn_resp

        numbers = await engine.fetch_phone_numbers("waba_id_001")
        assert len(numbers) == 1
        assert numbers[0]["id"] == "phone_num_id_999"
        assert numbers[0]["display_phone_number"] == "+1 555-0199"
        assert numbers[0]["verified_name"] == "Acme Support"


# 10. Connector Registration Test
def test_whatsapp_connector_registration():
    connector_cls = ConnectorRegistry.get_connector("whatsapp")
    assert connector_cls == WhatsAppConnector

    connector = ConnectorFactory.create(
        "whatsapp",
        credentials={"client_id": "c", "client_secret": "s"},
        access_token="tok",
    )
    assert isinstance(connector, WhatsAppConnector)
    capabilities = connector.get_capabilities()
    assert capabilities.can_sync is True
    assert capabilities.can_webhook is True


# 11. SocialProviderFactory Registration Test
def test_whatsapp_provider_factory():
    provider = SocialProviderFactory.get_provider(ApiProvider.WHATSAPP)
    assert isinstance(provider, WhatsAppProvider)


# 12. Provider Get Account Info Test
@pytest.mark.asyncio
async def test_whatsapp_provider_get_account_info(mock_secret_service):
    account = SocialAccount(
        id=uuid.uuid4(), account_id="phone_num_id_999", access_token="enc_tok_123"
    )

    provider = WhatsAppProvider()

    with patch(
        "app.integrations.connectors.whatsapp.sync.WhatsAppSyncEngine.fetch_wabas_with_phone_numbers",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [
            {
                "phone_number_id": "phone_num_id_999",
                "waba_id": "waba_111",
                "display_phone_number": "+1 555-0199",
                "verified_name": "Acme Support",
                "quality_rating": "GREEN",
            }
        ]

        info = await provider.get_account_info(account)
        assert info["account_id"] == "phone_num_id_999"
        assert info["waba_id"] == "waba_111"
        assert info["display_phone_number"] == "+1 555-0199"
        assert info["verified_name"] == "Acme Support"
        assert info["status"] == "connected"


# 13. Expired Token Error Test
@pytest.mark.asyncio
async def test_whatsapp_expired_token_handling():
    engine = WhatsAppSyncEngine(access_token="expired_tok")

    err_resp = MagicMock(
        status_code=401,
        json=lambda: {
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
            }
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = err_resp

        with pytest.raises(OAuthTokenError) as exc_info:
            await engine.fetch_wabas()

        assert "access token is invalid or expired" in str(exc_info.value)
        # Secret non-leakage check
        assert "expired_tok" not in str(exc_info.value)


# 14. Single-Use Auth Code Exchange Exactly Once Test
@pytest.mark.asyncio
async def test_whatsapp_oauth_code_exchanged_exactly_once():
    db = AsyncMock()
    ws_id = uuid.uuid4()

    mock_connector = AsyncMock()
    mock_connector.connect.return_value = {
        "access_token": "valid_whatsapp_tok",
        "refresh_token": None,
        "expires_at": None,
        "waba_info": {},
    }

    with (
        patch(
            "app.integrations.oauth.service.ConnectorFactory.create",
            return_value=mock_connector,
        ),
        patch(
            "app.integrations.oauth.service.integration_connection_repo.get_by_workspace_and_provider",
            return_value=None,
        ),
        patch(
            "app.integrations.oauth.service.integration_connection_repo.create",
            new_callable=AsyncMock,
        ),
        patch(
            "app.repositories.social_account.social_account_repo",
            new_callable=AsyncMock,
        ),
        patch(
            "app.integrations.oauth.service.secret_service.encrypt_token",
            return_value="enc_tok",
        ),
    ):

        await IntegrationService.connect_provider(
            db=db,
            workspace_id=ws_id,
            provider="whatsapp",
            auth_code="fresh_auth_code_12345",
            redirect_uri="http://localhost:8000/api/v1/integrations/oauth/callback",
        )

        # Proves connector.connect (and code exchange) was called EXACTLY ONCE
        assert mock_connector.connect.call_count == 1
        call_args, call_kwargs = mock_connector.connect.call_args
        assert call_args[0] == "fresh_auth_code_12345"
        assert (
            call_kwargs.get("redirect_uri")
            == "http://localhost:8000/api/v1/integrations/oauth/callback"
        )


# 15. Graceful Post-Exchange Discovery Warning Test
@pytest.mark.asyncio
async def test_whatsapp_connect_gracefully_handles_post_exchange_waba_error():
    handler = WhatsAppOAuthHandler(client_id="cid", client_secret="csec")

    with (
        patch.object(handler, "exchange_code", new_callable=AsyncMock) as mock_exchange,
        patch(
            "app.integrations.connectors.whatsapp.connector.WhatsAppSyncEngine"
        ) as mock_sync_cls,
    ):

        mock_exchange.return_value = {
            "access_token": "valid_token_777",
            "refresh_token": None,
            "expires_at": None,
        }

        mock_sync = AsyncMock()
        mock_sync.perform_sync.side_effect = Exception(
            "Meta Graph WABA API temporary error"
        )
        mock_sync_cls.return_value = mock_sync

        connector = WhatsAppConnector(
            credentials={"client_id": "cid", "client_secret": "csec"}
        )
        connector.oauth_handler = handler

        result = await connector.connect("single_use_auth_code_999")

        # Code exchange called exactly once
        assert mock_exchange.call_count == 1
        # Access token is retained and connection succeeds despite WABA warning
        assert result["access_token"] == "valid_token_777"
        assert "warning" in result["waba_info"]


# 16. Meta OAuthException Code 190 vs Code 100 Discrimination Tests
@pytest.mark.asyncio
async def test_whatsapp_oauth_exception_code_190_raises_oauth_token_error():
    engine = WhatsAppSyncEngine(access_token="tok_190")
    err_resp = MagicMock(
        status_code=400,
        json=lambda: {
            "error": {
                "message": "Error validating access token: Session has expired",
                "type": "OAuthException",
                "code": 190,
            }
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = err_resp

        with pytest.raises(OAuthTokenError) as exc_info:
            await engine.fetch_wabas()

        assert "access token is invalid or expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_whatsapp_oauth_exception_code_100_raises_whatsapp_api_error_not_expired():
    from app.integrations.oauth.models import ConnectionStatus
    from app.integrations.sync.engine import sync_engine

    engine = WhatsAppSyncEngine(access_token="valid_tok_code_100")
    err_resp = MagicMock(
        status_code=400,
        json=lambda: {
            "error": {
                "message": "(#100) Tried accessing nonexisting field (whatsapp_business_accounts)",
                "type": "OAuthException",
                "code": 100,
            }
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = err_resp

        # 1. Direct engine call raises WhatsAppApiError, NOT OAuthTokenError
        with pytest.raises(WhatsAppApiError) as exc_info:
            await engine.fetch_wabas()

        assert "(Code 100)" in str(exc_info.value)
        assert "(#100) Tried accessing nonexisting field" in str(exc_info.value)
        assert not isinstance(exc_info.value, OAuthTokenError)

    # 2. IntegrationConnection status is NOT set to EXPIRED when execute_sync_job runs with Code 100
    mock_conn = MagicMock()
    mock_conn.status = ConnectionStatus.CONNECTED
    mock_conn.provider = "whatsapp"

    mock_connector = AsyncMock()
    mock_connector.sync.side_effect = WhatsAppApiError(
        "Failed to fetch WABAs (Code 100): (#100) Tried accessing nonexisting field",
        status_code=400,
    )

    db = AsyncMock()
    ws_id = uuid.uuid4()

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_conn,
        ),
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch(
            "app.integrations.sync.engine.integration_connection_repo.update",
            new_callable=AsyncMock,
        ) as mock_update_conn,
    ):

        with pytest.raises(WhatsAppApiError):
            await sync_engine.execute_sync_job(
                db, {"workspace_id": str(ws_id), "provider": "whatsapp"}
            )

        # Connection status was NOT updated to EXPIRED
        mock_update_conn.assert_not_called()
        assert mock_conn.status == ConnectionStatus.CONNECTED


@pytest.mark.asyncio
async def test_whatsapp_sync_successful_token_validation():
    engine = WhatsAppSyncEngine(access_token="valid_tok_200")
    success_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "data": [
                {
                    "id": "waba_123",
                    "name": "Test WABA",
                    "currency": "USD",
                    "timezone_id": "1",
                }
            ]
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = success_resp

        wabas = await engine.fetch_wabas()
        assert len(wabas) == 1
        assert wabas[0]["id"] == "waba_123"
        assert wabas[0]["name"] == "Test WABA"
