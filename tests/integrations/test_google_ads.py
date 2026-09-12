from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.connectors.google.ads import GoogleAdsService
from app.integrations.connectors.google.connector import GoogleConnector
from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)


@pytest.fixture
def ads_service():
    return GoogleAdsService(
        access_token="test_access_token",
        developer_token="test_dev_token",
        login_customer_id="9998887777",
    )


@pytest.mark.asyncio
async def test_get_report_success(ads_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "results": [
                {
                    "campaign": {
                        "resourceName": "customers/1234567890/campaigns/101",
                        "id": "101",
                        "name": "Summer Promotion",
                        "status": "ENABLED",
                    },
                    "metrics": {
                        "impressions": "5000",
                        "clicks": "250",
                        "costMicros": "12500000",
                    },
                }
            ],
            "fieldMask": "campaign.id,campaign.name,campaign.status,metrics.impressions,metrics.clicks,metrics.cost_micros",
        }
    ]

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        report = await ads_service.get_report(
            customer_id="1234567890",
            start_date="2026-08-01",
            end_date="2026-09-01",
        )

        assert report["customer_id"] == "1234567890"
        assert report["resource_name"] == "customers/1234567890"
        assert report["row_count"] == 1
        assert len(report["rows"]) == 1

        row = report["rows"][0]
        assert row["campaign_id"] == "101"
        assert row["campaign_name"] == "Summer Promotion"
        assert row["status"] == "ENABLED"
        assert row["impressions"] == 5000
        assert row["clicks"] == 250
        assert row["cost_micros"] == 12500000
        assert row["cost"] == 12.5

        mock_post.assert_called_once()
        url, kwargs = mock_post.call_args
        assert (
            url[0]
            == "https://googleads.googleapis.com/v25/customers/1234567890/googleAds:searchStream"
        )
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"
        assert kwargs["headers"]["developer-token"] == "test_dev_token"
        assert kwargs["headers"]["login-customer-id"] == "9998887777"
        assert (
            "WHERE segments.date BETWEEN '2026-08-01' AND '2026-09-01'"
            in kwargs["json"]["query"]
        )


@pytest.mark.asyncio
async def test_get_report_with_query_override_and_login_id_override(ads_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []

    mock_post = AsyncMock(return_value=mock_response)

    custom_gaql = "SELECT campaign.id, campaign.name FROM campaign LIMIT 5"

    with patch("httpx.AsyncClient.post", new=mock_post):
        report = await ads_service.get_report(
            customer_id="customers/6774894805",
            login_customer_id="1112223333",
            query_override=custom_gaql,
        )

        assert report["customer_id"] == "6774894805"
        assert report["rows"] == []
        assert report["row_count"] == 0

        _, kwargs = mock_post.call_args
        assert kwargs["headers"]["login-customer-id"] == "1112223333"
        assert kwargs["json"]["query"] == custom_gaql


@pytest.mark.asyncio
async def test_get_report_401_auth_error(ads_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Google Ads report"
        ):
            await ads_service.get_report(customer_id="1234567890")


@pytest.mark.asyncio
async def test_get_report_429_quota_error(ads_service):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate Limit Exceeded"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(GoogleQuotaError, match="rate limit exceeded"):
            await ads_service.get_report(customer_id="1234567890")


@pytest.mark.asyncio
async def test_get_report_500_api_error(ads_service):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(GoogleApiError, match="Google Ads API error 500"):
            await ads_service.get_report(customer_id="1234567890")


@pytest.mark.asyncio
async def test_get_report_missing_customer_id_raises_value_error(ads_service):
    with pytest.raises(ValueError, match="Invalid or empty customer_id"):
        await ads_service.get_report(customer_id="")


def test_connector_returns_google_ads_service():
    connector = GoogleConnector(
        credentials={"client_id": "test_id", "client_secret": "test_secret"},
        access_token="test_token",
    )
    service = connector.get_google_ads_service(
        developer_token="dev_tok", login_customer_id="mcc_id"
    )
    assert isinstance(service, GoogleAdsService)
    assert service.access_token == "test_token"
    assert service.developer_token == "dev_tok"
    assert service.login_customer_id == "mcc_id"
