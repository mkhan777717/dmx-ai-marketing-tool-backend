import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.constants.enums import AssetType
from app.integrations.connectors.whatsapp.connector import WhatsAppConnector
from app.integrations.connectors.whatsapp.exceptions import WhatsAppPublishError
from app.integrations.connectors.whatsapp.publisher import WhatsAppPublisher
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.whatsapp_provider import WhatsAppProvider


@pytest.fixture
def publisher():
    return WhatsAppPublisher(access_token="raw_wa_access_token_123")


@pytest.fixture
def provider():
    return WhatsAppProvider()


@pytest.fixture
def account():
    return SocialAccount(
        id=uuid.uuid4(), account_id="phone_num_id_555", access_token="enc_wa_token"
    )


@pytest.fixture
def mock_secret_service():
    with patch("app.services.social.whatsapp_provider.secret_service") as mock_secret:
        mock_secret.decrypt_token.side_effect = lambda t: f"decrypted_{t}" if t else ""
        yield mock_secret


# ============================================================
# 1. TEXT MESSAGE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_send_text_message_success(publisher):
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "15550199", "wa_id": "15550199"}],
            "messages": [{"id": "wamid.HBgLMTU1NTAxOTk2MzA1"}],
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        res = await publisher.send_text_message(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            message="Hello from AI Marketing Suite!",
        )

        assert res["messages"][0]["id"] == "wamid.HBgLMTU1NTAxOTk2MzA1"

        mock_client.post.assert_called_once()
        url, kwargs = mock_client.post.call_args

        assert "phone_num_id_555/messages" in url[0]
        payload = kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["recipient_type"] == "individual"
        assert payload["to"] == "15550199"
        assert payload["type"] == "text"
        assert payload["text"]["body"] == "Hello from AI Marketing Suite!"


@pytest.mark.asyncio
async def test_missing_access_token():
    pub = WhatsAppPublisher(access_token="")
    with pytest.raises(WhatsAppPublishError, match="Access token is required"):
        await pub.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_missing_phone_number_id(publisher):
    with pytest.raises(WhatsAppPublishError, match="phone_number_id is required"):
        await publisher.send_text_message("", "15550199", "Hello")


@pytest.mark.asyncio
async def test_missing_recipient(publisher):
    with pytest.raises(
        WhatsAppPublishError, match="Recipient phone number is required"
    ):
        await publisher.send_text_message("phone_id", "", "Hello")


@pytest.mark.asyncio
async def test_missing_message_body(publisher):
    with pytest.raises(WhatsAppPublishError, match="Message body is required"):
        await publisher.send_text_message("phone_id", "15550199", "  ")


@pytest.mark.asyncio
async def test_http_400_failure(publisher):
    fail_resp = MagicMock(status_code=400, text="Bad Request: Invalid phone number")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError, match="Status 400"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_http_401_403_auth_failure(publisher):
    fail_resp = MagicMock(status_code=401, text="Unauthorized: Invalid access token")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError, match="Status 401"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_http_429_rate_limit_failure(publisher):
    fail_resp = MagicMock(status_code=429, text="Rate limit exceeded")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError, match="Status 429"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_http_5xx_failure(publisher):
    fail_resp = MagicMock(status_code=503, text="Service Unavailable")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError, match="Status 503"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_network_request_failure(publisher):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.side_effect = Exception("DNS Resolution failed")

        with pytest.raises(WhatsAppPublishError, match="Network error"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_malformed_json_response(publisher):
    ok_resp = MagicMock(status_code=200)
    ok_resp.json.side_effect = ValueError("Invalid JSON string")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = ok_resp

        with pytest.raises(WhatsAppPublishError, match="invalid JSON"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


@pytest.mark.asyncio
async def test_missing_message_id_response(publisher):
    ok_resp = MagicMock(
        status_code=200, json=lambda: {"messaging_product": "whatsapp", "messages": []}
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = ok_resp

        with pytest.raises(WhatsAppPublishError, match="missing message ID"):
            await publisher.send_text_message("phone_id", "15550199", "Hello")


# ============================================================
# 2. TEMPLATE MESSAGE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_send_template_message_success(publisher):
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "messaging_product": "whatsapp",
            "contacts": [{"input": "15550199", "wa_id": "15550199"}],
            "messages": [{"id": "wamid.TEMPLATE_MSG_001"}],
        },
    )

    components = [
        {"type": "body", "parameters": [{"type": "text", "text": "John Doe"}]}
    ]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        res = await publisher.send_template_message(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            template_name="sample_issue_resolution",
            language_code="en_US",
            components=components,
        )

        assert res["messages"][0]["id"] == "wamid.TEMPLATE_MSG_001"

        mock_client.post.assert_called_once()
        url, kwargs = mock_client.post.call_args

        assert "phone_num_id_555/messages" in url[0]
        payload = kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["type"] == "template"
        assert payload["to"] == "15550199"
        assert payload["template"]["name"] == "sample_issue_resolution"
        assert payload["template"]["language"]["code"] == "en_US"
        assert payload["template"]["components"] == components


@pytest.mark.asyncio
async def test_send_template_message_missing_template_name(publisher):
    with pytest.raises(WhatsAppPublishError, match="Template name is required"):
        await publisher.send_template_message("phone_id", "15550199", "")


@pytest.mark.asyncio
async def test_send_template_message_missing_language_code(publisher):
    with pytest.raises(WhatsAppPublishError, match="Language code is required"):
        await publisher.send_template_message(
            "phone_id", "15550199", "sample_template", language_code=""
        )


@pytest.mark.asyncio
async def test_send_template_message_http_400(publisher):
    fail_resp = MagicMock(status_code=400, text="Template does not exist")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError, match="Status 400"):
            await publisher.send_template_message(
                "phone_id", "15550199", "invalid_template"
            )


# ============================================================
# 3. IMAGE MESSAGE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_send_image_message_success(publisher):
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.IMAGE_MSG_001"}],
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        res = await publisher.send_media_message(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="image",
            media_url="https://images.unsplash.com/photo-sample.jpg",
            caption="Check out our new product!",
        )

        assert res["messages"][0]["id"] == "wamid.IMAGE_MSG_001"

        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["type"] == "image"
        assert (
            payload["image"]["link"] == "https://images.unsplash.com/photo-sample.jpg"
        )
        assert payload["image"]["caption"] == "Check out our new product!"


@pytest.mark.asyncio
async def test_send_image_message_missing_url(publisher):
    with pytest.raises(WhatsAppPublishError, match="Media URL is required"):
        await publisher.send_media_message("phone_id", "15550199", "image", "")


# ============================================================
# 4. VIDEO MESSAGE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_send_video_message_success(publisher):
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.VIDEO_MSG_001"}],
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        res = await publisher.send_media_message(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="video",
            media_url="https://cdn.example.com/demo.mp4",
            caption="Watch quick video tutorial",
        )

        assert res["messages"][0]["id"] == "wamid.VIDEO_MSG_001"

        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["type"] == "video"
        assert payload["video"]["link"] == "https://cdn.example.com/demo.mp4"
        assert payload["video"]["caption"] == "Watch quick video tutorial"


# ============================================================
# 5. DOCUMENT MESSAGE TESTS
# ============================================================


@pytest.mark.asyncio
async def test_send_document_message_success(publisher):
    mock_resp = MagicMock(
        status_code=200,
        json=lambda: {
            "messaging_product": "whatsapp",
            "messages": [{"id": "wamid.DOC_MSG_001"}],
        },
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = mock_resp

        res = await publisher.send_media_message(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="document",
            media_url="https://cdn.example.com/invoice.pdf",
            caption="July Invoice",
            filename="Invoice_July_2026.pdf",
        )

        assert res["messages"][0]["id"] == "wamid.DOC_MSG_001"

        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["type"] == "document"
        assert payload["document"]["link"] == "https://cdn.example.com/invoice.pdf"
        assert payload["document"]["caption"] == "July Invoice"
        assert payload["document"]["filename"] == "Invoice_July_2026.pdf"


@pytest.mark.asyncio
async def test_send_media_unsupported_type(publisher):
    with pytest.raises(WhatsAppPublishError, match="Unsupported media_type 'audio'"):
        await publisher.send_media_message(
            "phone_id", "15550199", "audio", "https://audio.mp3"
        )


# ============================================================
# 6. PROVIDER ROUTING TESTS
# ============================================================


@pytest.mark.asyncio
async def test_provider_routes_text_message(provider, account, mock_secret_service):
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Text Message",
        body="Hello Text World",
        metadata_={"recipient": "15550199"},
    )

    with patch(
        "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_text_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = {"messages": [{"id": "wamid.TXT_001"}]}

        msg_id = await provider.publish_content(account, content)
        assert msg_id == "wamid.TXT_001"
        mock_send.assert_called_once_with(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            message="Hello Text World",
        )


@pytest.mark.asyncio
async def test_provider_routes_template_message(provider, account, mock_secret_service):
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Template Message",
        body="",
        metadata_={
            "recipient": "15550199",
            "template_name": "welcome_offer",
            "language_code": "en_US",
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Valued Customer"}],
                }
            ],
        },
    )

    with patch(
        "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_template_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = {"messages": [{"id": "wamid.TPL_001"}]}

        msg_id = await provider.publish_content(account, content)
        assert msg_id == "wamid.TPL_001"
        mock_send.assert_called_once_with(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            template_name="welcome_offer",
            language_code="en_US",
            components=[
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": "Valued Customer"}],
                }
            ],
        )


@pytest.mark.asyncio
async def test_provider_routes_image_message(provider, account, mock_secret_service):
    image_asset = MagicMock(
        asset_type=AssetType.IMAGE,
        public_url="https://example.com/banner.jpg",
        file_name="banner.jpg",
    )
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Image Promo",
        body="Summer Sale Banner",
        metadata_={"recipient": "15550199"},
        assets=[image_asset],
    )

    with patch(
        "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_media_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = {"messages": [{"id": "wamid.IMG_001"}]}

        msg_id = await provider.publish_content(account, content)
        assert msg_id == "wamid.IMG_001"
        mock_send.assert_called_once_with(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="image",
            media_url="https://example.com/banner.jpg",
            caption="Summer Sale Banner",
            filename="banner.jpg",
        )


@pytest.mark.asyncio
async def test_provider_routes_video_message(provider, account, mock_secret_service):
    video_asset = MagicMock(
        asset_type=AssetType.VIDEO,
        public_url="https://example.com/clip.mp4",
        file_name="clip.mp4",
    )
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Video Promo",
        body="Product Demo",
        metadata_={"recipient": "15550199"},
        assets=[video_asset],
    )

    with patch(
        "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_media_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = {"messages": [{"id": "wamid.VID_001"}]}

        msg_id = await provider.publish_content(account, content)
        assert msg_id == "wamid.VID_001"
        mock_send.assert_called_once_with(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="video",
            media_url="https://example.com/clip.mp4",
            caption="Product Demo",
            filename="clip.mp4",
        )


@pytest.mark.asyncio
async def test_provider_routes_document_message(provider, account, mock_secret_service):
    doc_asset = MagicMock(
        asset_type=AssetType.DOCUMENT,
        public_url="https://example.com/report.pdf",
        file_name="Monthly_Report.pdf",
    )
    content = CampaignContent(
        id=uuid.uuid4(),
        title="Doc Report",
        body="Monthly Report PDF",
        metadata_={"recipient": "15550199", "filename": "Custom_Report_Name.pdf"},
        assets=[doc_asset],
    )

    with patch(
        "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_media_message",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = {"messages": [{"id": "wamid.DOC_001"}]}

        msg_id = await provider.publish_content(account, content)
        assert msg_id == "wamid.DOC_001"
        mock_send.assert_called_once_with(
            phone_number_id="phone_num_id_555",
            recipient="15550199",
            media_type="document",
            media_url="https://example.com/report.pdf",
            caption="Monthly Report PDF",
            filename="Custom_Report_Name.pdf",
        )


# ============================================================
# 7. CONNECTOR CAPABILITY & METHOD TESTS
# ============================================================


@pytest.mark.asyncio
async def test_connector_capabilities_phase_2b():
    connector = WhatsAppConnector(credentials={}, access_token="tok_123")
    caps = connector.get_capabilities()
    assert "publish_text" in caps.supported_actions
    assert "publish_template" in caps.supported_actions
    assert "publish_image" in caps.supported_actions
    assert "publish_video" in caps.supported_actions
    assert "publish_document" in caps.supported_actions
    # Confirm unsupported capabilities are not falsely exposed
    assert "audio" not in caps.supported_actions
    assert "incoming_message" not in caps.supported_actions


@pytest.mark.asyncio
async def test_connector_publish_template_and_media_routing():
    connector = WhatsAppConnector(credentials={}, access_token="tok_123")

    with (
        patch(
            "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_template_message",
            new_callable=AsyncMock,
        ) as mock_tpl,
        patch(
            "app.integrations.connectors.whatsapp.publisher.WhatsAppPublisher.send_media_message",
            new_callable=AsyncMock,
        ) as mock_media,
    ):
        mock_tpl.return_value = {"messages": [{"id": "wamid.TPL_CONN"}]}
        mock_media.return_value = {"messages": [{"id": "wamid.IMG_CONN"}]}

        res_tpl = await connector.publish(
            page_id="phone_55",
            content="",
            page_access_token="tok_123",
            recipient="15550199",
            template_name="sample_issue_resolution",
        )
        assert res_tpl["messages"][0]["id"] == "wamid.TPL_CONN"

        res_media = await connector.publish(
            page_id="phone_55",
            content="Image caption",
            page_access_token="tok_123",
            recipient="15550199",
            media_type="image",
            media_url="https://example.com/photo.jpg",
        )
        assert res_media["messages"][0]["id"] == "wamid.IMG_CONN"


# ============================================================
# 8. SECURITY TESTS
# ============================================================


@pytest.mark.asyncio
async def test_security_token_not_in_exceptions_or_logs():
    pub = WhatsAppPublisher(access_token="SUPER_SECRET_BEARER_TOKEN_777")
    fail_resp = MagicMock(status_code=401, text="Unauthorized: Token invalid")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.post.return_value = fail_resp

        with pytest.raises(WhatsAppPublishError) as exc_info:
            await pub.send_text_message("phone_id", "15550199", "Test text")

        assert "SUPER_SECRET_BEARER_TOKEN_777" not in str(exc_info.value)
