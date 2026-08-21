import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.connectors.twitter.exceptions import (
    TwitterError,
    TwitterAuthError,
)
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.twitter_provider import TwitterProvider


@pytest.fixture
def provider():
    return TwitterProvider()


@pytest.fixture
def account():
    acc = SocialAccount()
    acc.id = uuid.uuid4()
    acc.access_token = "encrypted_token"
    return acc


@pytest.fixture
def content():
    c = CampaignContent()
    c.id = uuid.uuid4()
    c.body = "Hello Twitter!"
    return c


@pytest.mark.asyncio
async def test_provider_missing_token_raises_error(provider, account, content):
    account.access_token = None
    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert "missing access token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_provider_empty_body_raises_error(provider, account, content):
    content.body = "   "
    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert "non-empty body content" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_success(
    mock_publisher_class, mock_secret_service, provider, account, content
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_post.return_value = "12345"
    mock_publisher_class.return_value = mock_publisher_instance

    post_id = await provider.publish_content(account, content)

    assert post_id == "12345"

    mock_secret_service.decrypt_token.assert_called_once_with("encrypted_token")
    mock_publisher_class.assert_called_once_with(access_token="decrypted_token")
    mock_publisher_instance.publish_post.assert_called_once_with(
        text="Hello Twitter!", media_ids=None
    )


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_missing_post_id(
    mock_publisher_class, mock_secret_service, provider, account, content
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_post.return_value = None
    mock_publisher_class.return_value = mock_publisher_instance

    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert "Failed to retrieve valid post ID" in str(exc_info.value)


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.integration_connection_repo")
@patch("app.services.social.twitter_provider.social_account_repo")
@patch("app.services.social.twitter_provider.AsyncSessionLocal")
@patch("app.services.social.twitter_provider.TwitterOAuthHandler")
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_refreshes_token_if_expired(
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
    from datetime import datetime, timedelta, timezone

    # Token expired 10 minutes ago
    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
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
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_post.return_value = "12345"
    mock_publisher_class.return_value = mock_publisher_instance

    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session

    mock_conn = MagicMock()
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=mock_conn)
    mock_soc_account = MagicMock()
    mock_soc_repo.get_by_id = AsyncMock(return_value=mock_soc_account)

    post_id = await provider.publish_content(account, content)

    assert post_id == "12345"
    assert account.access_token == "enc_new_acc"
    assert account.refresh_token == "enc_new_ref"

    mock_oauth_instance.refresh_token.assert_called_once_with("dec_old_enc_refresh")
    mock_session.commit.assert_called_once()
    assert mock_conn.access_token == "enc_new_acc"
    assert mock_soc_account.access_token == "enc_new_acc"

    mock_publisher_class.assert_called_once_with(access_token="dec_enc_new_acc")


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.integration_connection_repo")
@patch("app.services.social.twitter_provider.social_account_repo")
@patch("app.services.social.twitter_provider.AsyncSessionLocal")
@patch("app.services.social.twitter_provider.TwitterOAuthHandler")
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_refresh_preserves_old_refresh_token(
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
    from datetime import datetime, timedelta, timezone

    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
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
        # Twitter does not return a new refresh token
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.publish_post.return_value = "12345"
    mock_publisher_class.return_value = mock_publisher_instance

    mock_session = AsyncMock()
    mock_async_session_local.return_value.__aenter__.return_value = mock_session

    mock_conn = MagicMock()
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=mock_conn)
    mock_soc_account = MagicMock()
    mock_soc_repo.get_by_id = AsyncMock(return_value=mock_soc_account)

    post_id = await provider.publish_content(account, content)

    assert post_id == "12345"
    assert account.access_token == "enc_new_acc"
    assert account.refresh_token == "old_enc_refresh"
    assert mock_conn.refresh_token == "old_enc_refresh"
    assert mock_soc_account.refresh_token == "old_enc_refresh"


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.integration_connection_repo")
@patch("app.services.social.twitter_provider.social_account_repo")
@patch("app.services.social.twitter_provider.AsyncSessionLocal")
@patch("app.services.social.twitter_provider.TwitterOAuthHandler")
@patch("app.services.social.twitter_provider.secret_service")
async def test_provider_refresh_persistence_failure_rolls_back(
    mock_secret_service,
    mock_oauth_class,
    mock_async_session_local,
    mock_soc_repo,
    mock_repo,
    provider,
    account,
    content,
):
    from datetime import datetime, timedelta, timezone

    account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
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
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    mock_oauth_class.return_value = mock_oauth_instance

    mock_session = AsyncMock()
    # Simulate DB failure during commit
    mock_session.commit.side_effect = Exception("DB Connection Error")
    mock_async_session_local.return_value.__aenter__.return_value = mock_session

    mock_conn = MagicMock()
    mock_repo.get_by_workspace_and_provider = AsyncMock(return_value=mock_conn)
    mock_soc_account = MagicMock()
    mock_soc_repo.get_by_id = AsyncMock(return_value=mock_soc_account)

    with pytest.raises(TwitterAuthError) as exc_info:
        await provider.publish_content(account, content)

    assert "Failed to persist refreshed tokens" in str(exc_info.value)

    # Verify rollback was called
    mock_session.rollback.assert_called_once()

    # In-memory account should NOT be updated
    assert account.access_token != "enc_new_acc"
    assert account.refresh_token == "old_enc_refresh"


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.httpx.AsyncClient")
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_publish_with_media(
    mock_publisher_class,
    mock_secret_service,
    mock_async_client,
    provider,
    account,
    content,
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.upload_media.return_value = "111222"
    mock_publisher_instance.publish_post.return_value = "12345"
    mock_publisher_class.return_value = mock_publisher_instance

    # Mock content with assets
    asset1 = MagicMock()
    asset1.file_size = 1000
    asset1.mime_type = "image/png"
    asset1.public_url = "https://example.com/image.png"
    content.assets = [asset1]

    # Mock HTTP download
    mock_get = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = b"fake_bytes"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.get = mock_get

    post_id = await provider.publish_content(account, content)

    assert post_id == "12345"

    mock_get.assert_called_once_with("https://example.com/image.png")
    mock_publisher_instance.upload_media.assert_called_once_with(
        file_bytes=b"fake_bytes",
        mime_type="image/png",
        total_bytes=len(b"fake_bytes"),
        media_category="tweet_image",
    )
    mock_publisher_instance.publish_post.assert_called_once_with(
        text="Hello Twitter!", media_ids=["111222"]
    )


@pytest.mark.asyncio
@patch("app.services.social.twitter_provider.httpx.AsyncClient")
@patch("app.services.social.twitter_provider.secret_service")
@patch("app.services.social.twitter_provider.TwitterPublisher")
async def test_provider_publish_with_streaming_video(
    mock_publisher_class,
    mock_secret_service,
    mock_async_client,
    provider,
    account,
    content,
):
    mock_secret_service.decrypt_token.return_value = "decrypted_token"

    mock_publisher_instance = AsyncMock()
    mock_publisher_instance.upload_media.return_value = "777888"
    mock_publisher_instance.publish_post.return_value = "999000"
    mock_publisher_class.return_value = mock_publisher_instance

    # Mock content with video asset
    asset1 = MagicMock()
    asset1.file_size = 1000000
    asset1.mime_type = "video/mp4"
    asset1.public_url = "https://example.com/video.mp4"
    content.assets = [asset1]

    # Mock HTTP stream
    mock_stream = MagicMock()
    mock_response = AsyncMock()

    async def mock_aiter_bytes(chunk_size):
        yield b"chunk1"
        yield b"chunk2"

    mock_response.aiter_bytes = mock_aiter_bytes
    mock_response.raise_for_status = MagicMock()

    # stream() returns an async context manager
    mock_stream.return_value.__aenter__.return_value = mock_response
    mock_stream.return_value.__aexit__.return_value = None

    mock_client_instance = mock_async_client.return_value.__aenter__.return_value
    mock_client_instance.stream = mock_stream

    post_id = await provider.publish_content(account, content)

    assert post_id == "999000"

    mock_stream.assert_called_once_with("GET", "https://example.com/video.mp4")
    mock_publisher_instance.upload_media.assert_called_once()
    kwargs = mock_publisher_instance.upload_media.call_args.kwargs
    assert kwargs["mime_type"] == "video/mp4"
    assert kwargs["total_bytes"] == 1000000
    assert kwargs["media_category"] == "tweet_video"
    assert hasattr(kwargs["file_bytes"], "__aiter__")

    mock_publisher_instance.publish_post.assert_called_once_with(
        text="Hello Twitter!", media_ids=["777888"]
    )


@pytest.mark.asyncio
async def test_provider_publish_multiple_videos_raises_error(
    provider, account, content
):
    asset1 = MagicMock(mime_type="video/mp4")
    asset2 = MagicMock(mime_type="video/quicktime")
    content.assets = [asset1, asset2]

    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert (
        "Twitter does not support attaching multiple videos or mixing images with video"
        in str(exc_info.value)
    )


@pytest.mark.asyncio
async def test_provider_publish_mixed_media_raises_error(provider, account, content):
    asset1 = MagicMock(mime_type="video/mp4")
    asset2 = MagicMock(mime_type="image/jpeg")
    content.assets = [asset1, asset2]

    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert (
        "Twitter does not support attaching multiple videos or mixing images with video"
        in str(exc_info.value)
    )


@pytest.mark.asyncio
async def test_provider_publish_oversized_video_raises_error(
    provider, account, content
):
    asset1 = MagicMock(
        mime_type="video/mp4", public_url="http://test", file_size=600 * 1024 * 1024
    )
    content.assets = [asset1]

    with pytest.raises(TwitterError) as exc_info:
        await provider.publish_content(account, content)
    assert "exceeds 512MB limit" in str(exc_info.value)
