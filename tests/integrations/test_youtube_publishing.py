import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import ApiProvider, AssetType, PublishStatus
from app.integrations.connectors.google.exceptions import GoogleError
from app.models.asset import Asset
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.publishing import PublishingService
from app.services.social.factory import SocialProviderFactory
from app.services.social.google_provider import GoogleProvider


@pytest.fixture
def db_session():
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def workspace_id():
    return uuid.uuid4()


@pytest.fixture
def youtube_account(workspace_id):
    account = MagicMock(spec=SocialAccount)
    account.id = uuid.uuid4()
    account.workspace_id = workspace_id
    account.account_id = "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    account.name = "Test YouTube Channel"
    account.provider = ApiProvider.YOUTUBE
    account.access_token = "enc_access_token"
    account.refresh_token = "enc_refresh_token"
    account.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    return account


@pytest.fixture
def video_asset():
    asset = MagicMock(spec=Asset)
    asset.id = uuid.uuid4()
    asset.public_url = "https://example.com/video.mp4"
    asset.mime_type = "video/mp4"
    asset.asset_type = AssetType.VIDEO
    asset.file_size = 1024 * 1024 * 5
    return asset


@pytest.fixture
def image_asset():
    asset = MagicMock(spec=Asset)
    asset.id = uuid.uuid4()
    asset.public_url = "https://example.com/image.jpg"
    asset.mime_type = "image/jpeg"
    asset.asset_type = AssetType.IMAGE
    asset.file_size = 1024 * 500
    return asset


@pytest.fixture
def video_content(workspace_id, video_asset):
    content = MagicMock(spec=CampaignContent)
    content.id = uuid.uuid4()
    content.campaign_id = uuid.uuid4()
    content.workspace_id = workspace_id
    content.title = "Awesome YouTube Video"
    content.body = "This is a detailed video description."
    content.assets = [video_asset]
    content.metadata_ = {
        "privacy_status": "unlisted",
        "tags": ["marketing", "tech"],
        "category_id": "28",
    }
    return content


def test_factory_resolves_youtube_provider():
    provider = SocialProviderFactory.get_provider(ApiProvider.YOUTUBE)
    assert isinstance(provider, GoogleProvider)


@pytest.mark.asyncio
async def test_youtube_account_routes_to_youtube_publisher(
    db_session, youtube_account, video_content
):
    provider = GoogleProvider()

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="raw_access_token",
        ),
        patch(
            "app.integrations.connectors.google.youtube.YouTubePublisher.upload_video",
            new_callable=AsyncMock,
        ) as mock_upload,
    ):
        mock_upload.return_value = "yt_vid_999"

        result = await provider.publish_content(
            db_session, youtube_account, video_content
        )

        assert result == "yt_vid_999"
        mock_upload.assert_called_once_with(
            asset_url="https://example.com/video.mp4",
            title="Awesome YouTube Video",
            description="This is a detailed video description.",
            file_size=1024 * 1024 * 5,
            mime_type="video/mp4",
            privacy_status="unlisted",
            tags=["marketing", "tech"],
            category_id="28",
        )


@pytest.mark.asyncio
async def test_youtube_publishing_rejects_missing_video_asset(
    db_session, youtube_account, video_content
):
    provider = GoogleProvider()
    video_content.assets = []

    with pytest.raises(GoogleError, match="YouTube publishing requires a VIDEO asset."):
        await provider.publish_content(db_session, youtube_account, video_content)


@pytest.mark.asyncio
async def test_youtube_publishing_rejects_image_asset(
    db_session, youtube_account, video_content, image_asset
):
    provider = GoogleProvider()
    video_content.assets = [image_asset]

    with pytest.raises(GoogleError, match="YouTube publishing requires a VIDEO asset."):
        await provider.publish_content(db_session, youtube_account, video_content)


@pytest.mark.asyncio
async def test_youtube_publishing_content_title_fallback(
    db_session, youtube_account, video_content
):
    provider = GoogleProvider()
    video_content.title = None
    video_content.body = "Body description used as title"
    video_content.metadata_ = None

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="raw_access_token",
        ),
        patch(
            "app.integrations.connectors.google.youtube.YouTubePublisher.upload_video",
            new_callable=AsyncMock,
        ) as mock_upload,
    ):
        mock_upload.return_value = "yt_vid_888"

        result = await provider.publish_content(
            db_session, youtube_account, video_content
        )

        assert result == "yt_vid_888"
        mock_upload.assert_called_once_with(
            asset_url="https://example.com/video.mp4",
            title="Body description used as title",
            description="Body description used as title",
            file_size=1024 * 1024 * 5,
            mime_type="video/mp4",
            privacy_status="private",
            tags=None,
            category_id=None,
        )


@pytest.mark.asyncio
async def test_publishing_history_receives_youtube_video_id(
    db_session, youtube_account, video_content
):
    workspace_id = video_content.workspace_id

    mock_history = MagicMock()
    mock_history.id = uuid.uuid4()

    with (
        patch(
            "app.repositories.campaign_content.campaign_content_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=video_content,
        ),
        patch(
            "app.repositories.social_account.social_account_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=youtube_account,
        ),
        patch(
            "app.repositories.publish_history.publish_history_repo.create",
            new_callable=AsyncMock,
            return_value=mock_history,
        ),
        patch(
            "app.repositories.publish_history.publish_history_repo.update",
            new_callable=AsyncMock,
        ) as mock_update,
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="raw_access_token",
        ),
        patch(
            "app.integrations.connectors.google.youtube.YouTubePublisher.upload_video",
            new_callable=AsyncMock,
            return_value="yt_vid_777",
        ),
    ):
        request = MagicMock()
        request.content_id = video_content.id
        request.social_account_id = youtube_account.id

        await PublishingService.publish_content(db_session, workspace_id, request)

        mock_update.assert_called_once()
        _, kwargs = mock_update.call_args
        obj_in = kwargs.get("obj_in") or mock_update.call_args[0][2]
        assert obj_in["status"] == PublishStatus.PUBLISHED
        assert obj_in["external_post_id"] == "yt_vid_777"


@pytest.mark.asyncio
async def test_publishing_history_records_failed_youtube_publish(
    db_session, youtube_account, video_content
):
    workspace_id = video_content.workspace_id

    mock_history = MagicMock()
    mock_history.id = uuid.uuid4()

    with (
        patch(
            "app.repositories.campaign_content.campaign_content_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=video_content,
        ),
        patch(
            "app.repositories.social_account.social_account_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=youtube_account,
        ),
        patch(
            "app.repositories.publish_history.publish_history_repo.create",
            new_callable=AsyncMock,
            return_value=mock_history,
        ),
        patch(
            "app.repositories.publish_history.publish_history_repo.update",
            new_callable=AsyncMock,
        ) as mock_update,
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="raw_access_token",
        ),
        patch(
            "app.integrations.connectors.google.youtube.YouTubePublisher.upload_video",
            new_callable=AsyncMock,
            side_effect=GoogleError("YouTube API quota exceeded"),
        ),
    ):
        request = MagicMock()
        request.content_id = video_content.id
        request.social_account_id = youtube_account.id

        await PublishingService.publish_content(db_session, workspace_id, request)

        mock_update.assert_called_once()
        _, kwargs = mock_update.call_args
        obj_in = kwargs.get("obj_in") or mock_update.call_args[0][2]
        assert obj_in["status"] == PublishStatus.FAILED
        assert "YouTube API quota exceeded" in obj_in["error_message"]


@pytest.mark.asyncio
async def test_existing_google_business_profile_publishing_intact(db_session):
    google_account = MagicMock(spec=SocialAccount)
    google_account.id = uuid.uuid4()
    google_account.workspace_id = uuid.uuid4()
    google_account.account_id = "accounts/111/locations/222"
    google_account.provider = ApiProvider.GOOGLE
    google_account.access_token = "enc_access_token"
    google_account.refresh_token = "enc_refresh_token"
    google_account.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    text_content = MagicMock(spec=CampaignContent)
    text_content.body = "Business update post"
    text_content.assets = []

    provider = GoogleProvider()

    with (
        patch(
            "app.integrations.secrets.service.secret_service.decrypt_token",
            return_value="decrypted_access",
        ),
        patch(
            "app.integrations.connectors.google.business_profile.GoogleBusinessProfilePublisher.publish_post",
            new_callable=AsyncMock,
            return_value="accounts/111/locations/222/localPosts/123",
        ) as mock_publish,
    ):
        result = await provider.publish_content(
            db_session, google_account, text_content
        )

        assert result == "accounts/111/locations/222/localPosts/123"
        mock_publish.assert_called_once_with(
            account_id="accounts/111/locations/222",
            text="Business update post",
            image_url=None,
        )
