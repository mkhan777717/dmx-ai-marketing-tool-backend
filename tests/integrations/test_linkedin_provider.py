import os
import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone

from app.integrations.connectors.linkedin.exceptions import LinkedInAuthError
from app.integrations.exceptions import IntegrationError
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.linkedin_provider import LinkedInProvider


@pytest.fixture
def provider():
    return LinkedInProvider()


@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(os.environ, {"LINKEDIN_API_VERSION": "202608"}):
        yield


@pytest.fixture
def account():
    acc = SocialAccount()
    acc.id = uuid.uuid4()
    acc.workspace_id = uuid.uuid4()
    acc.account_id = "urn:li:person:12345"
    acc.access_token = "encrypted_token"
    # Valid token by default
    acc.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return acc


@pytest.fixture
def content():
    c = CampaignContent()
    c.id = uuid.uuid4()
    c.body = "Hello LinkedIn!"
    return c


@pytest.mark.asyncio
async def test_provider_missing_token_raises_error(provider, account, content):
    account.access_token = None
    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)
    assert "missing access token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_empty_body_raises_error(provider, account, content):
    content.body = "   "
    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)
    assert "non-empty body content" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_invalid_urn_raises_error(provider, account, content):
    account.account_id = "12345"
    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)
    assert "Invalid LinkedIn author URN" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
async def test_valid_token_does_not_refresh(
    mock_publisher_class, mock_secret_service, provider, account, content
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_text_post.return_value = "urn:li:share:12345"
    mock_publisher_class.return_value = mock_publisher_instance

    post_id = await provider.publish_content(account, content)

    assert post_id == "urn:li:share:12345"
    mock_secret_service.decrypt_token.assert_called_once_with("encrypted_token")
    mock_publisher_class.assert_called_once_with(access_token="decrypted_token")
    mock_publisher_instance.publish_text_post.assert_called_once_with(
        author_urn="urn:li:person:12345", text="Hello LinkedIn!"
    )


@pytest.mark.asyncio
async def test_missing_refresh_token_raises_error(provider, account, content):
    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    account.refresh_token = None
    with pytest.raises(LinkedInAuthError) as exc_info:
        await provider.publish_content(account, content)
    assert "no refresh token available" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.integration_connection_repo")
@patch("app.services.social.linkedin_provider.social_account_repo")
@patch("app.services.social.linkedin_provider.AsyncSessionLocal")
@patch("app.services.social.linkedin_provider.LinkedInOAuthHandler")
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
async def test_near_expiry_token_refreshes_and_persists(
    mock_publisher_class,
    mock_secret_service,
    mock_oauth_class,
    mock_async_session_local,
    mock_soc_repo,
    mock_repo,
    provider,
    account,
    content,
):
    # Expiring in 2 minutes
    account.expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    account.refresh_token = "old_enc_refresh"

    mock_secret_service.decrypt_token.side_effect = lambda x: f"dec_{x}"
    mock_secret_service.encrypt_token.side_effect = lambda x: f"enc_{x}"
    mock_secret_service.get_provider_credentials.return_value = {
        "client_id": "id",
        "client_secret": "sec",
    }

    mock_oauth_instance = AsyncMock()
    mock_oauth_instance.refresh_token.return_value = {
        "access_token": "new_acc",
        "refresh_token": "new_ref",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_text_post.return_value = "post123"
    mock_publisher_class.return_value = mock_publisher_instance

    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session

    mock_conn = MagicMock()
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=mock_conn)
    mock_soc_account = MagicMock()
    mock_soc_repo.get_by_id = AsyncMock(return_value=mock_soc_account)

    post_id = await provider.publish_content(account, content)

    assert post_id == "post123"
    mock_session.commit.assert_awaited_once()

    # Verify both records were updated
    assert mock_conn.access_token == "enc_new_acc"
    assert mock_conn.refresh_token == "enc_new_ref"
    assert mock_conn.expires_at.tzinfo is None  # Connection uses naive DB datetime

    assert mock_soc_account.access_token == "enc_new_acc"
    assert mock_soc_account.refresh_token == "enc_new_ref"
    assert mock_soc_account.expires_at.tzinfo == timezone.utc

    # Verify in-memory account updated
    assert account.access_token == "enc_new_acc"
    assert account.refresh_token == "enc_new_ref"


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.integration_connection_repo")
@patch("app.services.social.linkedin_provider.social_account_repo")
@patch("app.services.social.linkedin_provider.AsyncSessionLocal")
@patch("app.services.social.linkedin_provider.LinkedInOAuthHandler")
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
async def test_refresh_response_without_refresh_token_preserves_old(
    mock_publisher_class,
    mock_secret_service,
    mock_oauth_class,
    mock_async_session_local,
    mock_soc_repo,
    mock_repo,
    provider,
    account,
    content,
):
    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    account.refresh_token = "old_enc_refresh"

    mock_secret_service.decrypt_token.side_effect = lambda x: f"dec_{x}"
    mock_secret_service.encrypt_token.side_effect = lambda x: f"enc_{x}"
    mock_secret_service.get_provider_credentials.return_value = {}

    mock_oauth_instance = AsyncMock()
    # Missing refresh_token in response
    mock_oauth_instance.refresh_token.return_value = {
        "access_token": "new_acc",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_text_post.return_value = "post123"
    mock_publisher_class.return_value = mock_publisher_instance

    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_conn = MagicMock()
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=mock_conn)
    mock_soc_account = MagicMock()
    mock_soc_repo.get_by_id = AsyncMock(return_value=mock_soc_account)

    await provider.publish_content(account, content)

    # The existing refresh token should be preserved
    assert mock_conn.refresh_token == "old_enc_refresh"
    assert account.refresh_token == "old_enc_refresh"


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.integration_connection_repo")
@patch("app.services.social.linkedin_provider.social_account_repo")
@patch("app.services.social.linkedin_provider.AsyncSessionLocal")
@patch("app.services.social.linkedin_provider.LinkedInOAuthHandler")
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
async def test_db_commit_failure_rolls_back_and_aborts(
    mock_publisher_class,
    mock_secret_service,
    mock_oauth_class,
    mock_async_session_local,
    mock_soc_repo,
    mock_repo,
    provider,
    account,
    content,
):
    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    old_acc_token = account.access_token
    account.refresh_token = "old_enc_refresh"

    mock_secret_service.decrypt_token.side_effect = lambda x: f"dec_{x}"
    mock_secret_service.encrypt_token.side_effect = lambda x: f"enc_{x}"
    mock_secret_service.get_provider_credentials.return_value = {}

    mock_oauth_instance = AsyncMock()
    mock_oauth_instance.refresh_token.return_value = {
        "access_token": "new_acc",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("DB Error")
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=MagicMock())
    mock_soc_repo.get_by_id = AsyncMock(return_value=MagicMock())

    with pytest.raises(LinkedInAuthError) as exc_info:
        await provider.publish_content(account, content)

    assert "Failed to persist refreshed tokens: DB Error" in str(exc_info.value)
    mock_session.rollback.assert_awaited_once()

    # In-memory account should be unchanged
    assert account.access_token == old_acc_token
    mock_publisher_class.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.integration_connection_repo")
@patch("app.services.social.linkedin_provider.social_account_repo")
@patch("app.services.social.linkedin_provider.AsyncSessionLocal")
@patch("app.services.social.linkedin_provider.LinkedInOAuthHandler")
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
async def test_publish_failure_after_refresh_keeps_tokens_persisted(
    mock_publisher_class,
    mock_secret_service,
    mock_oauth_class,
    mock_async_session_local,
    mock_soc_repo,
    mock_repo,
    provider,
    account,
    content,
):
    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    account.refresh_token = "old_enc_refresh"

    mock_secret_service.decrypt_token.side_effect = lambda x: f"dec_{x}"
    mock_secret_service.encrypt_token.side_effect = lambda x: f"enc_{x}"
    mock_secret_service.get_provider_credentials.return_value = {}

    mock_oauth_instance = AsyncMock()
    mock_oauth_instance.refresh_token.return_value = {
        "access_token": "new_acc",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_text_post.side_effect = Exception("API Down")
    mock_publisher_class.return_value = mock_publisher_instance

    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=MagicMock())
    mock_soc_repo.get_by_id = AsyncMock(return_value=MagicMock())

    with pytest.raises(Exception) as exc_info:
        await provider.publish_content(account, content)

    assert "API Down" in str(exc_info.value)
    # Commit must have succeeded
    mock_session.commit.assert_awaited_once()
    # In-memory account must have the new access token
    assert account.access_token == "enc_new_acc"


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInSyncEngine")
async def test_get_account_info_success(mock_sync_class, mock_secret_service, provider):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_sync_instance = AsyncMock()
    mock_sync_instance.fetch_profile.return_value = {
        "sub": "123456",
        "localizedFirstName": "John",
        "localizedLastName": "Doe",
    }
    mock_sync_class.return_value = mock_sync_instance

    result = await provider.get_account_info("encrypted_token")

    assert result == {
        "account_id": "urn:li:person:123456",
        "name": "John Doe",
        "username": "John Doe",
        "profile_url": None,
    }
    mock_secret_service.decrypt_token.assert_called_once_with("encrypted_token")
    mock_sync_class.assert_called_once_with("decrypted_token")


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInSyncEngine")
async def test_get_account_info_missing_sub(
    mock_sync_class, mock_secret_service, provider
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_sync_instance = AsyncMock()
    mock_sync_instance.fetch_profile.return_value = {"localizedFirstName": "John"}
    mock_sync_class.return_value = mock_sync_instance

    with pytest.raises(LinkedInAuthError) as exc_info:
        await provider.get_account_info("encrypted_token")

    assert "missing the required 'sub' identifier" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.LinkedInPublisher")
@patch("app.services.social.linkedin_provider.httpx.AsyncClient")
async def test_provider_publish_with_image_success(
    mock_client_class,
    mock_publisher_class,
    mock_secret_service,
    provider,
    account,
    content,
):
    from app.models.asset import Asset
    from app.constants.enums import AssetType

    image_asset = Asset(
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/image.jpg",
        mime_type="image/jpeg",
    )
    content.assets = [image_asset]

    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_image_post.return_value = "urn:li:share:123"
    mock_publisher_class.return_value = mock_publisher_instance

    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    # Mock stream response
    mock_response = AsyncMock()
    mock_response.headers = {"Content-Length": "1000"}
    mock_response.aread = AsyncMock(return_value=b"fakeimage")
    mock_response.raise_for_status = MagicMock()

    # client.stream returns an async context manager
    mock_client.stream = MagicMock()
    mock_client.stream.return_value.__aenter__.return_value = mock_response

    post_id = await provider.publish_content(account, content)

    assert post_id == "urn:li:share:123"
    mock_publisher_instance.publish_image_post.assert_called_once_with(
        author_urn="urn:li:person:12345",
        text="Hello LinkedIn!",
        image_binary=b"fakeimage",
        mime_type="image/jpeg",
    )
    mock_publisher_instance.publish_text_post.assert_not_called()


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
async def test_provider_publish_with_image_missing_url(
    mock_secret_service, provider, account, content
):
    from app.models.asset import Asset
    from app.constants.enums import AssetType

    image_asset = Asset(
        asset_type=AssetType.IMAGE, public_url=None, mime_type="image/jpeg"
    )
    content.assets = [image_asset]

    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)

    assert "missing a public URL" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
async def test_provider_publish_with_unsupported_mime(
    mock_secret_service, provider, account, content
):
    from app.models.asset import Asset
    from app.constants.enums import AssetType

    image_asset = Asset(
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/doc.pdf",
        mime_type="application/pdf",
    )
    content.assets = [image_asset]

    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)

    assert "Unsupported LinkedIn image MIME type" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.linkedin_provider.secret_service")
@patch("app.services.social.linkedin_provider.httpx.AsyncClient")
async def test_provider_publish_with_image_network_error(
    mock_client_class, mock_secret_service, provider, account, content
):
    from app.models.asset import Asset
    from app.constants.enums import AssetType
    import httpx

    image_asset = Asset(
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/image.jpg",
        mime_type="image/jpeg",
    )
    content.assets = [image_asset]

    mock_client = AsyncMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    # client.stream raises an error during execution
    mock_client.stream = MagicMock()
    mock_client.stream.side_effect = httpx.RequestError(
        "Network error", request=MagicMock()
    )

    with pytest.raises(IntegrationError) as exc_info:
        await provider.publish_content(account, content)

    assert "Failed to download image from" in str(exc_info.value)
