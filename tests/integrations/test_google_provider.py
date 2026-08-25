import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ApiProvider
from app.integrations.connectors.google.exceptions import GoogleAuthError, GoogleError
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.factory import SocialProviderFactory
from app.services.social.google_provider import GoogleProvider


@pytest.fixture
def db_session():
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def mock_account():
    account = MagicMock(spec=SocialAccount)
    account.id = uuid.uuid4()
    account.workspace_id = uuid.uuid4()
    account.account_id = "accounts/111/locations/222"
    account.name = "Test Location"
    account.access_token = "encrypted_access"
    account.refresh_token = "encrypted_refresh"
    account.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return account


@pytest.fixture
def text_content():
    content = MagicMock(spec=CampaignContent)
    content.body = "Hello Google!"
    content.assets = []
    return content


@pytest.fixture
def media_content():
    content = MagicMock(spec=CampaignContent)
    content.body = "Hello Google!"
    content.assets = [MagicMock()]
    return content


def test_factory_returns_google_provider():
    provider = SocialProviderFactory.get_provider(ApiProvider.GOOGLE)
    assert isinstance(provider, GoogleProvider)


@pytest.mark.asyncio
async def test_get_account_info(db_session, mock_account):
    provider = GoogleProvider()
    info = await provider.get_account_info(db_session, mock_account)

    assert info["id"] == "accounts/111/locations/222"
    assert info["name"] == "Test Location"
    assert info["provider"] == "google"


@pytest.mark.asyncio
async def test_publish_content_success(db_session, mock_account, text_content):
    provider = GoogleProvider()

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted_access",
        ),
        patch(
            "app.integrations.connectors.google.business_profile.GoogleBusinessProfilePublisher.publish_post",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.return_value = "accounts/111/locations/222/localPosts/789"

        result = await provider.publish_content(db_session, mock_account, text_content)

        mock_publish.assert_called_once_with(
            account_id="accounts/111/locations/222",
            text="Hello Google!",
            image_url=None,
        )
        assert result == "accounts/111/locations/222/localPosts/789"


@pytest.mark.asyncio
async def test_publish_content_rejects_empty_body(
    db_session, mock_account, text_content
):
    provider = GoogleProvider()
    text_content.body = "   "

    with pytest.raises(GoogleError, match="requires non-empty body"):
        await provider.publish_content(db_session, mock_account, text_content)


@pytest.mark.asyncio
async def test_publish_content_rejects_multiple_media(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets.append(MagicMock())

    with pytest.raises(
        GoogleError,
        match="Google Provider only supports a single image or video for publishing.",
    ):
        await provider.publish_content(db_session, mock_account, media_content)


@pytest.mark.asyncio
async def test_publish_content_rejects_missing_url(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = None

    with pytest.raises(
        GoogleError, match="Asset public_url must be a valid HTTP/HTTPS URL."
    ):
        await provider.publish_content(db_session, mock_account, media_content)


@pytest.mark.asyncio
async def test_publish_content_rejects_invalid_url_protocol(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = "ftp://example.com/image.jpg"

    with pytest.raises(
        GoogleError, match="Asset public_url must be a valid HTTP/HTTPS URL."
    ):
        await provider.publish_content(db_session, mock_account, media_content)


@pytest.mark.asyncio
async def test_publish_content_rejects_unsupported_mime(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = "https://example.com/audio.mp3"
    media_content.assets[0].mime_type = "audio/mp3"

    with pytest.raises(
        GoogleError,
        match="Unsupported MIME type audio/mp3. Only images and videos are supported.",
    ):
        await provider.publish_content(db_session, mock_account, media_content)


@pytest.mark.asyncio
async def test_publish_content_rejects_unsupported_image_mime(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = "https://example.com/image.gif"
    media_content.assets[0].mime_type = "image/gif"

    with pytest.raises(
        GoogleError,
        match="Image format image/gif is not supported by Google Business Profile.",
    ):
        await provider.publish_content(db_session, mock_account, media_content)


@pytest.mark.asyncio
async def test_publish_content_with_image_success(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = "https://example.com/image.jpg"
    media_content.assets[0].mime_type = "image/jpeg"

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted_access",
        ),
        patch(
            "app.integrations.connectors.google.business_profile.GoogleBusinessProfilePublisher.publish_post",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_publish.return_value = "accounts/111/locations/222/localPosts/789"

        result = await provider.publish_content(db_session, mock_account, media_content)

        mock_publish.assert_called_once_with(
            account_id="accounts/111/locations/222",
            text="Hello Google!",
            image_url="https://example.com/image.jpg",
        )
        assert result == "accounts/111/locations/222/localPosts/789"


@pytest.mark.asyncio
async def test_publish_content_with_video_success(
    db_session, mock_account, media_content
):
    provider = GoogleProvider()
    media_content.assets[0].public_url = "https://example.com/video.mp4"
    media_content.assets[0].mime_type = "video/mp4"
    media_content.assets[0].file_size = 1024 * 1024 * 10

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted_access",
        ),
        patch(
            "app.integrations.connectors.google.youtube.YouTubePublisher.upload_video",
            new_callable=AsyncMock,
        ) as mock_upload,
    ):
        mock_upload.return_value = "youtube_video_123"

        result = await provider.publish_content(db_session, mock_account, media_content)

        mock_upload.assert_called_once_with(
            asset_url="https://example.com/video.mp4",
            title="Hello Google!",
            description="Hello Google!",
            file_size=1024 * 1024 * 10,
            mime_type="video/mp4",
        )
        assert result == "youtube_video_123"


@pytest.mark.asyncio
async def test_publish_content_refreshes_token_if_expired(
    db_session, mock_account, text_content
):
    provider = GoogleProvider()
    mock_account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)

    mock_new_tokens = {
        "access_token": "new_access",
        "refresh_token": "new_refresh",
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    mock_conn = MagicMock()
    mock_soc_account = MagicMock()

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted",
        ),
        patch(
            "app.integrations.secrets.service.secret_service.get_provider_credentials",
            return_value={"client_id": "c", "client_secret": "s"},
        ),
        patch(
            "app.integrations.connectors.google.oauth.GoogleOAuthHandler.refresh_access_token",
            new_callable=AsyncMock,
        ) as mock_refresh,
        patch(
            "app.integrations.secrets.service.secret_service.encrypt_token",
            side_effect=["enc_new_access", "enc_new_refresh"],
        ),
        patch("app.services.social.google_provider.AsyncSessionLocal"),
        patch(
            "app.integrations.oauth.repository.integration_connection_repo.get_by_workspace_and_provider",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch(
            "app.repositories.social_account.social_account_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=mock_soc_account,
        ),
        patch(
            "app.integrations.connectors.google.business_profile.GoogleBusinessProfilePublisher.publish_post",
            new_callable=AsyncMock,
        ) as mock_publish,
    ):
        mock_refresh.return_value = mock_new_tokens
        mock_publish.return_value = "accounts/111/locations/222/localPosts/789"

        result = await provider.publish_content(db_session, mock_account, text_content)

        assert mock_refresh.call_count == 1
        assert mock_account.access_token == "enc_new_access"
        assert mock_account.refresh_token == "enc_new_refresh"
        mock_publish.assert_called_once_with(
            account_id="accounts/111/locations/222",
            text="Hello Google!",
            image_url=None,
        )
        assert result == "accounts/111/locations/222/localPosts/789"


@pytest.mark.asyncio
async def test_publish_content_missing_refresh_token_fails(
    db_session, mock_account, text_content
):
    provider = GoogleProvider()
    mock_account.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    mock_account.refresh_token = None

    with pytest.raises(
        GoogleAuthError, match="token expired and no refresh token available"
    ):
        await provider.publish_content(db_session, mock_account, text_content)
