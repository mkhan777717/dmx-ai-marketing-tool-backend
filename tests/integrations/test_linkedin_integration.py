import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.enums import ApiProvider
from app.integrations.connectors.linkedin.exceptions import (
    LinkedInPublishError,
)
from app.integrations.connectors.linkedin.publisher import LinkedInPublisher
from app.integrations.connectors.linkedin.sync import LinkedInSyncEngine
from app.integrations.oauth.manager import OAuthManager


@pytest.fixture(autouse=True)
def setup_api_version_env():
    import os

    with patch.dict(os.environ, {"LINKEDIN_API_VERSION": "202601"}):
        yield


@pytest.fixture
def mock_credentials():
    return {
        "client_id": "test_linkedin_client_id_123",
        "client_secret": "test_linkedin_client_secret_999",
    }


# ============================================================
# 1. OAUTH & STATE TESTS
# ============================================================


def test_linkedin_oauth_url_generation():
    url = OAuthManager.get_authorization_url(
        provider="linkedin",
        state="state_xyz_123",
        redirect_uri="http://localhost:8000/api/v1/integrations/oauth/callback",
        client_id="test_linkedin_client_id_123",
    )

    assert "https://www.linkedin.com/oauth/v2/authorization" in url
    assert "client_id=test_linkedin_client_id_123" in url
    assert "response_type=code" in url
    assert "state=state_xyz_123" in url
    assert "w_member_social" in url
    assert "w_organization_social" not in url
    assert "rw_organization_admin" not in url


# ============================================================
# 2. ORGANIZATION DISCOVERY & PERSISTENCE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_fetch_organizations_success():
    sync_engine = LinkedInSyncEngine("test_access_token")

    acls_response = {
        "elements": [
            {
                "organizationalTarget": "urn:li:organization:123456",
                "role": "ADMINISTRATOR",
                "state": "APPROVED",
            },
            {
                "organizationalTarget": "urn:li:organization:789012",
                "role": "DIRECTOR",
                "state": "APPROVED",
            },
        ]
    }

    org_details_response = {
        "id": 123456,
        "localizedName": "Acme Marketing Inc.",
    }

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp_1 = MagicMock()
        mock_resp_1.status_code = 200
        mock_resp_1.json.return_value = acls_response

        mock_resp_2 = MagicMock()
        mock_resp_2.status_code = 200
        mock_resp_2.json.return_value = org_details_response

        mock_get.side_effect = [mock_resp_1, mock_resp_2, mock_resp_2]

        orgs = await sync_engine.fetch_organizations()

        assert len(orgs) == 2
        assert orgs[0]["organization_urn"] == "urn:li:organization:123456"
        assert orgs[0]["name"] == "Acme Marketing Inc."
        assert orgs[1]["organization_urn"] == "urn:li:organization:789012"


@pytest.mark.asyncio
async def test_sync_engine_persists_personal_and_company_pages():
    from app.integrations.sync.engine import sync_engine

    mock_workspace_id = str(uuid.uuid4())
    mock_payload = {"workspace_id": mock_workspace_id, "provider": "linkedin"}
    mock_connection = AsyncMock()
    mock_connection.access_token = "conn_token"

    mock_connector = AsyncMock()
    mock_connector.sync.return_value = {
        "profile": {"sub": "person_123", "name": "Alice Member"},
        "organizations": [
            {"organization_urn": "urn:li:organization:888", "name": "Company Alpha"},
            {"organization_urn": "urn:li:organization:999", "name": "Company Beta"},
        ],
    }

    created_accounts = []

    async def mock_create(db, obj_in):
        created_accounts.append(obj_in)

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_connection,
        ),
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch(
            "app.integrations.sync.engine.social_account_repo.get_all", return_value=[]
        ),
        patch(
            "app.integrations.sync.engine.social_account_repo.create",
            side_effect=mock_create,
        ),
        patch(
            "app.integrations.sync.engine.secret_service.decrypt_token",
            return_value="token",
        ),
        patch(
            "app.integrations.sync.engine.secret_service.encrypt_token",
            return_value="enc_token",
        ),
    ):
        await sync_engine.execute_sync_job(AsyncMock(), mock_payload)

        # Should create 1 Personal + 2 Organization SocialAccount records
        assert len(created_accounts) == 3
        assert created_accounts[0]["account_id"] == "urn:li:person:person_123"
        assert created_accounts[1]["account_id"] == "urn:li:organization:888"
        assert created_accounts[1]["name"] == "Company Alpha"
        assert created_accounts[2]["account_id"] == "urn:li:organization:999"
        assert created_accounts[2]["name"] == "Company Beta"


# ============================================================
# 3. DESTINATION ROUTING & PUBLISHING TESTS
# ============================================================


@pytest.mark.asyncio
async def test_publish_to_company_page_text_success():
    publisher = LinkedInPublisher("valid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.headers = {"x-restli-id": "urn:li:share:company_post_101"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        post_id = await publisher.publish_text_post(
            "urn:li:organization:888", "Company announcement"
        )
        assert post_id == "urn:li:share:company_post_101"

        payload = mock_post.call_args.kwargs["json"]
        assert payload["author"] == "urn:li:organization:888"
        assert payload["commentary"] == "Company announcement"


@pytest.mark.asyncio
async def test_publish_to_company_page_video_success():
    publisher = LinkedInPublisher("valid_token")

    init_resp = MagicMock()
    init_resp.status_code = 200
    init_resp.json.return_value = {
        "value": {
            "video": "urn:li:video:777",
            "uploadInstructions": [{"uploadUrl": "https://upload.linkedin.com/video"}],
        }
    }

    upload_resp = MagicMock()
    upload_resp.status_code = 201

    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.headers = {"x-restli-id": "urn:li:share:video_post_202"}

    with (
        patch("httpx.AsyncClient.post", side_effect=[init_resp, post_resp]),
        patch("httpx.AsyncClient.put", return_value=upload_resp),
    ):

        post_id = await publisher.publish_video_post(
            author_urn="urn:li:organization:888",
            text="Check out our new product video",
            video_binary=b"video_data_stream",
            mime_type="video/mp4",
            title="Product Launch",
        )

        assert post_id == "urn:li:share:video_post_202"


# ============================================================
# 4. ERROR HANDLING & SECURITY TESTS
# ============================================================


@pytest.mark.asyncio
async def test_forbidden_error_403_unauthorized_organization():
    publisher = LinkedInPublisher("valid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "User does not have ADMINISTRATOR role on this organization"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(
            LinkedInPublishError, match="Forbidden: Insufficient permissions"
        ):
            await publisher.publish_text_post(
                "urn:li:organization:unauthorized_123", "Forbidden post"
            )


@pytest.mark.asyncio
async def test_rate_limit_error_429():
    publisher = LinkedInPublisher("valid_token")

    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.text = "Rate limit exceeded"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(LinkedInPublishError) as exc_info:
            await publisher.publish_text_post("urn:li:person:123", "Too many requests")

        assert exc_info.value.status_code == 429


def test_security_access_token_never_in_exceptions():
    secret_token = "SECRET_LINKEDIN_BEARER_TOKEN_99999"
    publisher = LinkedInPublisher(secret_token)

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = f"Invalid payload sent with Bearer {secret_token}"

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(LinkedInPublishError) as exc_info:
            import asyncio

            asyncio.run(
                publisher.publish_text_post("urn:li:person:123", "Security test")
            )

        err_msg = str(exc_info.value)
        assert secret_token not in err_msg
        assert "[REDACTED TOKEN ERROR]" in err_msg


# ============================================================
# 5. OAUTH CALLBACK ROUTE TESTS
# ============================================================


def test_oauth_callback_success():
    from fastapi.testclient import TestClient

    from app.main import app

    ws_id = str(uuid.uuid4())
    state = OAuthManager.generate_state(ws_id, "linkedin")

    with (
        patch(
            "app.integrations.oauth.service.integration_service.connect_provider",
            new_callable=AsyncMock,
        ) as mock_connect,
        patch(
            "app.integrations.sync.engine.sync_engine.execute_sync_job",
            new_callable=AsyncMock,
        ),
    ):
        client = TestClient(app)
        res = client.get(
            "/api/v1/integrations/oauth/callback",
            params={"code": "valid_auth_code_123", "state": state},
        )

        assert res.status_code == 200
        assert res.json()["success"] is True
        assert "linkedin" in res.json()["message"].lower()
        mock_connect.assert_called_once()


def test_oauth_callback_error_returned_from_linkedin():
    from fastapi.testclient import TestClient

    from app.main import app

    ws_id = str(uuid.uuid4())
    state = OAuthManager.generate_state(ws_id, "linkedin")

    client = TestClient(app)
    res = client.get(
        "/api/v1/integrations/oauth/callback",
        params={
            "error": "user_cancelled_login",
            "error_description": "User cancelled the authorization flow",
            "state": state,
        },
    )

    assert res.status_code == 400
    assert "OAuth authorization failed" in res.json()["detail"]
    assert "User cancelled the authorization flow" in res.json()["detail"]


def test_oauth_callback_missing_code_and_error():
    from fastapi.testclient import TestClient

    from app.main import app

    ws_id = str(uuid.uuid4())
    state = OAuthManager.generate_state(ws_id, "linkedin")

    client = TestClient(app)
    res = client.get(
        "/api/v1/integrations/oauth/callback",
        params={"state": state},
    )

    assert res.status_code == 400
    assert "Missing authorization code" in res.json()["detail"]


def test_oauth_callback_invalid_state():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    res = client.get(
        "/api/v1/integrations/oauth/callback",
        params={"code": "valid_code", "state": "invalid_or_forged_state_token"},
    )

    assert res.status_code == 400
    assert "Invalid or expired state" in res.json()["detail"]


@pytest.mark.asyncio
async def test_linkedin_oauth_persists_social_account_and_lists_in_api():
    ws_id = uuid.uuid4()
    mock_db = AsyncMock()

    mock_token_data = {
        "access_token": "live_linkedin_access_token_123",
        "refresh_token": None,
        "expires_at": None,
    }

    mock_profile_data = {
        "sub": "linkedin_member_sub_999",
        "name": "Jane Developer",
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
        patch(
            "app.repositories.social_account.social_account_repo.get_all",
            new_callable=AsyncMock,
        ) as mock_get_all,
        patch(
            "app.repositories.social_account.social_account_repo.create",
            new_callable=AsyncMock,
        ) as mock_create_soc,
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
        ) as mock_get_conn,
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.create",
            new_callable=AsyncMock,
        ),
    ):
        mock_exchange.return_value = mock_token_data
        mock_fetch.return_value = mock_profile_data
        mock_get_all.return_value = []
        mock_get_conn.return_value = None

        from app.integrations.oauth.service import integration_service

        await integration_service.connect_provider(
            mock_db, ws_id, "linkedin", "test_auth_code_555"
        )

        mock_create_soc.assert_called_once()
        create_args = mock_create_soc.call_args.kwargs["obj_in"]

        assert create_args["workspace_id"] == ws_id
        assert create_args["provider"] == ApiProvider.LINKEDIN
        assert create_args["account_id"] == "urn:li:person:linkedin_member_sub_999"
        assert create_args["name"] == "Jane Developer"
        assert create_args["is_active"] is True
