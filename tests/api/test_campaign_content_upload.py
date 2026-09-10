import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.api.dependencies.auth import get_current_user, get_current_workspace
from app.constants.enums import AssetStatus, AssetType, ContentStatus, ContentType
from app.main import app
from app.models.asset import Asset
from app.models.campaign_content import CampaignContent
from app.models.user import User
from app.models.workspace import Workspace
from app.services.ai_content import AIContentService
from app.services.storage import StorageService


@pytest.fixture
def mock_workspace_id():
    return uuid.uuid4()


@pytest.fixture
def mock_user_id():
    return uuid.uuid4()


@pytest.fixture
def mock_campaign_id():
    return uuid.uuid4()


@pytest.fixture
def mock_content_id():
    return uuid.uuid4()


@pytest.fixture
def override_auth_deps(mock_user_id, mock_workspace_id):
    def override_get_current_user():
        return User(id=mock_user_id, email="test@example.com")

    def override_get_current_workspace():
        return Workspace(id=mock_workspace_id, name="Test Workspace")

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_current_workspace] = override_get_current_workspace

    with (
        patch(
            "app.api.dependencies.auth.workspace_member_repo.get_member",
            return_value=None,
        ),
        patch(
            "app.api.dependencies.auth.workspace_repo.get_by_id",
            return_value=Workspace(id=mock_workspace_id, owner_id=mock_user_id),
        ),
    ):
        yield

    app.dependency_overrides.clear()


# Binary helpers
VALID_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c63000100000500010d0a2d0b0000000049454e44ae426082"
)
VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9"
)
INVALID_TEXT_BYTES = b"This is a text file pretending to be an image"


def make_mock_content(mock_content_id, mock_campaign_id, mock_workspace_id):
    return CampaignContent(
        id=mock_content_id,
        campaign_id=mock_campaign_id,
        workspace_id=mock_workspace_id,
        title="Sample Content Item",
        content_type=ContentType.SOCIAL_POST,
        status=ContentStatus.DRAFT,
        version=1,
        is_current=True,
        assets=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_upload_valid_png_image(
    async_client: AsyncClient,
    override_auth_deps,
    mock_workspace_id,
    mock_campaign_id,
    mock_content_id,
):
    mock_asset = Asset(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        file_name="test.png",
        original_file_name="test.png",
        display_name="test.png",
        asset_type=AssetType.IMAGE,
        mime_type="image/png",
        file_size=len(VALID_PNG_BYTES),
        storage_provider="supabase",
        storage_key="assets/test.png",
        public_url="https://whvrwwuxejaofqwhhxgc.supabase.co/storage/v1/object/public/campaign-assets/assets/test.png",
        checksum="hash123",
        status=AssetStatus.READY,
    )
    mock_content = make_mock_content(
        mock_content_id, mock_campaign_id, mock_workspace_id
    )
    mock_content.assets = [mock_asset]

    with (
        patch(
            "app.api.v1.endpoints.campaign_content.AIContentService.upload_content_image",
            new_callable=AsyncMock,
            return_value=mock_content,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.commit",
            new_callable=AsyncMock,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.refresh",
            new_callable=AsyncMock,
        ),
    ):
        files = {"file": ("test.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
        response = await async_client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/campaigns/{mock_campaign_id}/contents/{mock_content_id}/upload-image",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Sample Content Item"
        assert len(data["assets"]) == 1
        asset = data["assets"][0]
        assert asset["asset_type"] == "IMAGE"
        assert asset["mime_type"] == "image/png"
        assert (
            "storage/v1/object/public/campaign-assets/assets/test.png"
            in asset["public_url"]
        )


@pytest.mark.asyncio
async def test_upload_valid_jpeg_image(
    async_client: AsyncClient,
    override_auth_deps,
    mock_workspace_id,
    mock_campaign_id,
    mock_content_id,
):
    mock_asset = Asset(
        id=uuid.uuid4(),
        workspace_id=mock_workspace_id,
        file_name="test.jpg",
        original_file_name="test.jpg",
        display_name="test.jpg",
        asset_type=AssetType.IMAGE,
        mime_type="image/jpeg",
        file_size=len(VALID_JPEG_BYTES),
        storage_provider="supabase",
        storage_key="assets/test.jpg",
        public_url="https://whvrwwuxejaofqwhhxgc.supabase.co/storage/v1/object/public/campaign-assets/assets/test.jpg",
        checksum="jpeg123hash",
        status=AssetStatus.READY,
    )
    mock_content = make_mock_content(
        mock_content_id, mock_campaign_id, mock_workspace_id
    )
    mock_content.assets = [mock_asset]

    with (
        patch(
            "app.api.v1.endpoints.campaign_content.AIContentService.upload_content_image",
            new_callable=AsyncMock,
            return_value=mock_content,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.commit",
            new_callable=AsyncMock,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.refresh",
            new_callable=AsyncMock,
        ),
    ):
        files = {"file": ("test.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")}
        response = await async_client.post(
            f"/api/v1/workspaces/{mock_workspace_id}/campaigns/{mock_campaign_id}/contents/{mock_content_id}/upload-image",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["assets"]) == 1
        asset = data["assets"][0]
        assert asset["mime_type"] == "image/jpeg"
        assert (
            "storage/v1/object/public/campaign-assets/assets/test.jpg"
            in asset["public_url"]
        )


@pytest.mark.asyncio
async def test_upload_content_image_replaces_old_assets(
    mock_workspace_id,
    mock_campaign_id,
    mock_content_id,
):
    # Setup mock content with 3 old dummy assets
    old_asset1 = Asset(
        id=uuid.uuid4(),
        file_name="old1.jpg",
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/old1.jpg",
    )
    old_asset2 = Asset(
        id=uuid.uuid4(),
        file_name="old2.jpg",
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/old2.jpg",
    )
    old_asset3 = Asset(
        id=uuid.uuid4(),
        file_name="old3.html",
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/old3.html",
    )

    mock_content = make_mock_content(
        mock_content_id, mock_campaign_id, mock_workspace_id
    )
    mock_content.assets = [old_asset1, old_asset2, old_asset3]
    assert len(mock_content.assets) == 3

    mock_db = AsyncMock()
    mock_upload_result = {
        "storage_provider": "supabase",
        "storage_key": "assets/new_uploaded.jpg",
        "public_url": "https://whvrwwuxejaofqwhhxgc.supabase.co/storage/v1/object/public/campaign-assets/assets/new_uploaded.jpg",
        "file_size": len(VALID_JPEG_BYTES),
        "checksum": "newhash123",
        "mime_type": "image/jpeg",
    }

    with (
        patch(
            "app.services.ai_content.AIContentService.get_content",
            new_callable=AsyncMock,
            return_value=mock_content,
        ),
        patch(
            "app.services.storage.StorageService.upload_image",
            new_callable=AsyncMock,
            return_value=mock_upload_result,
        ),
    ):
        updated_content = await AIContentService.upload_content_image(
            db=mock_db,
            workspace_id=mock_workspace_id,
            campaign_id=mock_campaign_id,
            content_id=mock_content_id,
            file_bytes=VALID_JPEG_BYTES,
            filename="new_uploaded.jpg",
            content_type="image/jpeg",
        )

        assert len(updated_content.assets) == 1
        new_asset = updated_content.assets[0]
        assert new_asset.file_name == "new_uploaded.jpg"
        assert "new_uploaded.jpg" in new_asset.public_url


@pytest.mark.asyncio
async def test_upload_invalid_mime_type_rejected():
    with pytest.raises(Exception) as excinfo:
        StorageService.validate_image(b"%PDF-1.4...", "application/pdf")
    assert "Unsupported file MIME type" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_upload_invalid_header_magic_bytes_rejected():
    with pytest.raises(Exception) as excinfo:
        StorageService.validate_image(INVALID_TEXT_BYTES, "image/png")
    assert "Invalid file header" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_upload_oversized_file_rejected():
    oversized_bytes = VALID_PNG_BYTES + (b"\x00" * (11 * 1024 * 1024))
    with pytest.raises(Exception) as excinfo:
        StorageService.validate_image(oversized_bytes, "image/png")
    assert "exceeds maximum limit" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_upload_workspace_unauthorized(
    async_client: AsyncClient,
    mock_user_id,
    mock_workspace_id,
    mock_campaign_id,
    mock_content_id,
):
    def override_get_current_user():
        return User(id=mock_user_id, email="unauthorized@example.com")

    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with (
            patch(
                "app.api.dependencies.auth.workspace_member_repo.get_member",
                return_value=None,
            ),
            patch(
                "app.api.dependencies.auth.workspace_repo.get_by_id",
                return_value=Workspace(id=mock_workspace_id, owner_id=uuid.uuid4()),
            ),
        ):
            files = {"file": ("test.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
            response = await async_client.post(
                f"/api/v1/workspaces/{mock_workspace_id}/campaigns/{mock_campaign_id}/contents/{mock_content_id}/upload-image",
                files=files,
                headers={"X-Workspace-ID": str(mock_workspace_id)},
            )
            assert response.status_code == 403
            assert response.json()["detail"] == "Not authorized"
    finally:
        app.dependency_overrides.clear()
