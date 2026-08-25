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
        "sub": "12345",
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

    with (
        patch.dict("os.environ", {"LINKEDIN_API_VERSION": "202401"}),
        patch(
            "app.integrations.connectors.linkedin.publisher.LinkedInPublisher.publish_text_post",
            new_callable=AsyncMock,
        ) as mock_pub,
    ):
        mock_pub.return_value = "urn:li:post:123"
        result = await connector.publish("urn:li:person:123", "Hello LinkedIn!")
        assert result == "urn:li:post:123"


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


@pytest.mark.asyncio
async def test_connect_missing_sub_fails(linkedin_connector):
    from app.integrations.connectors.linkedin.exceptions import LinkedInAuthError

    mock_token_response = {
        "access_token": "mock_access",
        "refresh_token": "mock_refresh",
        "expires_at": datetime.now(timezone.utc),
    }

    mock_profile_response = {
        # 'sub' is missing intentionally
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

        with pytest.raises(
            LinkedInAuthError, match="missing the required 'sub' identifier"
        ):
            await linkedin_connector.connect("dummy_code")


@pytest.mark.asyncio
async def test_publisher_posts_api_success():
    from app.integrations.connectors.linkedin.publisher import LinkedInPublisher

    with patch.dict("os.environ", {"LINKEDIN_API_VERSION": "202401"}):
        publisher = LinkedInPublisher("mock_token")

    class MockResponse:
        status_code = 201
        headers = {"x-restli-id": "urn:li:post:999"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MockResponse()

        result = await publisher.publish_text_post("urn:li:person:123", "Test content")

        assert result == "urn:li:post:999"

        # Verify URL, headers, and payload
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.linkedin.com/rest/posts"

        assert kwargs["headers"]["Authorization"] == "Bearer mock_token"
        assert kwargs["headers"]["X-Restli-Protocol-Version"] == "2.0.0"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert "LinkedIn-Version" in kwargs["headers"]

        assert kwargs["json"]["author"] == "urn:li:person:123"
        assert kwargs["json"]["lifecycleState"] == "PUBLISHED"
        assert kwargs["json"]["commentary"] == "Test content"
        assert kwargs["json"]["visibility"] == "PUBLIC"


@pytest.mark.asyncio
async def test_publisher_posts_api_missing_id():
    from app.integrations.connectors.linkedin.exceptions import LinkedInPublishError
    from app.integrations.connectors.linkedin.publisher import LinkedInPublisher

    with patch.dict("os.environ", {"LINKEDIN_API_VERSION": "202401"}):
        publisher = LinkedInPublisher("mock_token")

    class MockResponse:
        status_code = 201
        headers = {}  # Missing x-restli-id

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MockResponse()

        with pytest.raises(LinkedInPublishError, match="'x-restli-id' was missing"):
            await publisher.publish_text_post("urn:li:person:123", "Test content")


@pytest.mark.asyncio
async def test_publisher_posts_api_failure():
    from app.integrations.connectors.linkedin.exceptions import LinkedInPublishError
    from app.integrations.connectors.linkedin.publisher import LinkedInPublisher

    with patch.dict("os.environ", {"LINKEDIN_API_VERSION": "202401"}):
        publisher = LinkedInPublisher("mock_token")

    class MockResponse:
        status_code = 400
        text = "Bad Request"

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MockResponse()

        with pytest.raises(
            LinkedInPublishError, match="Failed to publish text post: Bad Request"
        ):
            await publisher.publish_text_post("urn:li:person:123", "Test content")


def test_missing_env_var_raises_error():
    import os

    from app.integrations.connectors.linkedin.publisher import LinkedInPublisher
    from app.integrations.exceptions import IntegrationError

    with patch.dict(os.environ, clear=True):
        if "LINKEDIN_API_VERSION" in os.environ:
            del os.environ["LINKEDIN_API_VERSION"]
        with pytest.raises(
            IntegrationError, match="is not configured in the environment"
        ):
            LinkedInPublisher("mock_token")


def test_invalid_env_var_raises_error():
    import os

    from app.integrations.connectors.linkedin.publisher import LinkedInPublisher
    from app.integrations.exceptions import IntegrationError

    with patch.dict(os.environ, {"LINKEDIN_API_VERSION": "latest"}):
        with pytest.raises(IntegrationError, match="must be in YYYYMM format"):
            LinkedInPublisher("mock_token")


@pytest.mark.asyncio
async def test_linkedin_sync_creates_social_account():
    import uuid

    from app.constants.enums import ApiProvider
    from app.integrations.sync.engine import sync_engine

    mock_workspace_id = str(uuid.uuid4())
    mock_payload = {"workspace_id": mock_workspace_id, "provider": "linkedin"}
    mock_connection = AsyncMock()
    mock_connection.access_token = "conn_token"
    mock_connector = AsyncMock()
    mock_connector.sync.return_value = {
        "profile": {
            "sub": "sync_sub_123",
            "localizedFirstName": "Sync",
            "localizedLastName": "User",
        }
    }

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
        patch("app.integrations.sync.engine.social_account_repo.create") as mock_create,
        patch(
            "app.integrations.sync.engine.secret_service.decrypt_token",
            return_value="decrypted",
        ),
        patch(
            "app.integrations.sync.engine.secret_service.encrypt_token",
            return_value="encrypted_token",
        ),
    ):
        await sync_engine.execute_sync_job(AsyncMock(), mock_payload)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs["obj_in"]
        assert call_kwargs["provider"] == ApiProvider.LINKEDIN
        assert call_kwargs["account_id"] == "urn:li:person:sync_sub_123"
        assert call_kwargs["name"] == "Sync User"
        assert call_kwargs["access_token"] == "encrypted_token"
        assert call_kwargs["is_active"] is True


@pytest.mark.asyncio
async def test_linkedin_sync_updates_existing_social_account():
    import uuid

    from app.integrations.sync.engine import sync_engine

    mock_workspace_id = str(uuid.uuid4())
    mock_payload = {"workspace_id": mock_workspace_id, "provider": "linkedin"}
    mock_connection = AsyncMock()
    mock_connection.access_token = "conn_token"
    mock_connector = AsyncMock()
    mock_connector.sync.return_value = {"profile": {"sub": "sync_sub_123"}}
    mock_existing_account = AsyncMock()

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
            "app.integrations.sync.engine.social_account_repo.get_all",
            return_value=[mock_existing_account],
        ),
        patch("app.integrations.sync.engine.social_account_repo.update") as mock_update,
        patch(
            "app.integrations.sync.engine.secret_service.decrypt_token",
            return_value="decrypted",
        ),
        patch(
            "app.integrations.sync.engine.secret_service.encrypt_token",
            return_value="encrypted_token",
        ),
    ):
        await sync_engine.execute_sync_job(AsyncMock(), mock_payload)

        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args.kwargs["obj_in"]
        assert call_kwargs["access_token"] == "encrypted_token"


@pytest.mark.asyncio
async def test_linkedin_sync_missing_connection_token_handled_safely():
    import uuid

    from app.integrations.sync.engine import sync_engine

    mock_workspace_id = str(uuid.uuid4())
    mock_payload = {"workspace_id": mock_workspace_id, "provider": "linkedin"}
    mock_connection = AsyncMock()
    mock_connection.access_token = None
    mock_connector = AsyncMock()
    mock_connector.sync.return_value = {"profile": {"sub": "sync_sub_123"}}

    with (
        patch(
            "app.integrations.sync.engine.integration_connection_repo.get_by_workspace_and_provider",
            return_value=mock_connection,
        ),
        patch(
            "app.integrations.sync.engine.integration_service.get_connector_instance",
            return_value=mock_connector,
        ),
        patch("app.integrations.sync.engine.logger.warning") as mock_warning,
        patch("app.integrations.sync.engine.social_account_repo.create") as mock_create,
    ):
        await sync_engine.execute_sync_job(AsyncMock(), mock_payload)

        mock_warning.assert_called_with(
            f"IntegrationConnection for LinkedIn workspace {mock_workspace_id} missing access token."
        )
        mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_linkedin_provider_publish_success():
    from app.models.campaign_content import CampaignContent
    from app.models.social_account import SocialAccount
    from app.services.social.linkedin_provider import LinkedInProvider

    provider = LinkedInProvider()
    account = SocialAccount(
        account_id="urn:li:person:123", access_token="encrypted_token"
    )
    content = CampaignContent(body="Test LinkedIn Post")

    with (
        patch.dict("os.environ", {"LINKEDIN_API_VERSION": "202401"}),
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted_token",
        ) as mock_decrypt,
        patch(
            "app.integrations.connectors.linkedin.publisher.LinkedInPublisher.publish_text_post",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.return_value = "urn:li:post:555"

        result = await provider.publish_content(account, content)

        assert result == "urn:li:post:555"
        mock_decrypt.assert_called_with("encrypted_token")
        mock_publish.assert_called_with(
            author_urn="urn:li:person:123", text="Test LinkedIn Post"
        )


@pytest.mark.asyncio
async def test_linkedin_provider_missing_token_raises_error():
    from app.integrations.exceptions import IntegrationError
    from app.models.campaign_content import CampaignContent
    from app.models.social_account import SocialAccount
    from app.services.social.linkedin_provider import LinkedInProvider

    provider = LinkedInProvider()
    account = SocialAccount(account_id="urn:li:person:123", access_token=None)
    content = CampaignContent(body="Test Post")

    with pytest.raises(
        IntegrationError, match="LinkedIn SocialAccount missing access token"
    ):
        await provider.publish_content(account, content)


@pytest.mark.asyncio
async def test_linkedin_provider_empty_body_raises_error():
    from app.integrations.exceptions import IntegrationError
    from app.models.campaign_content import CampaignContent
    from app.models.social_account import SocialAccount
    from app.services.social.linkedin_provider import LinkedInProvider

    provider = LinkedInProvider()
    account = SocialAccount(account_id="urn:li:person:123", access_token="token")
    content = CampaignContent(body="   ")

    with pytest.raises(
        IntegrationError,
        match="LinkedIn text publishing requires non-empty body content",
    ):
        await provider.publish_content(account, content)


@pytest.mark.asyncio
async def test_linkedin_provider_invalid_urn_raises_error():
    from app.integrations.exceptions import IntegrationError
    from app.models.campaign_content import CampaignContent
    from app.models.social_account import SocialAccount
    from app.services.social.linkedin_provider import LinkedInProvider

    provider = LinkedInProvider()
    account = SocialAccount(account_id="123", access_token="token")
    content = CampaignContent(body="Test")

    with pytest.raises(IntegrationError, match="Invalid LinkedIn author URN: 123"):
        await provider.publish_content(account, content)
