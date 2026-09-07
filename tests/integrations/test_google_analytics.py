from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.connectors.google.analytics import GoogleAnalyticsService
from app.integrations.connectors.google.connector import GoogleConnector
from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)


@pytest.fixture
def analytics_service():
    return GoogleAnalyticsService("test_access_token")


@pytest.mark.asyncio
async def test_get_report_success(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dimensionHeaders": [{"name": "date"}, {"name": "sessionSource"}],
        "metricHeaders": [
            {"name": "activeUsers", "type": "TYPE_INTEGER"},
            {"name": "sessions", "type": "TYPE_INTEGER"},
        ],
        "rows": [
            {
                "dimensionValues": [{"value": "20260901"}, {"value": "google"}],
                "metricValues": [{"value": "150"}, {"value": "200"}],
            }
        ],
        "rowCount": 1,
    }

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        report = await analytics_service.get_report(
            property_id="987654",
            start_date="2026-08-01",
            end_date="2026-09-01",
            dimensions=["date", "sessionSource"],
            metrics=["activeUsers", "sessions"],
            limit=50,
        )

        assert report["property_id"] == "987654"
        assert report["property_name"] == "properties/987654"
        assert report["dimension_headers"] == ["date", "sessionSource"]
        assert report["metric_headers"] == [
            {"name": "activeUsers", "type": "TYPE_INTEGER"},
            {"name": "sessions", "type": "TYPE_INTEGER"},
        ]
        assert len(report["rows"]) == 1
        assert report["rows"][0]["dimension_values"] == ["20260901", "google"]
        assert report["rows"][0]["metric_values"] == ["150", "200"]
        assert report["row_count"] == 1

        mock_post.assert_called_once()
        url, kwargs = mock_post.call_args
        assert (
            url[0]
            == "https://analyticsdata.googleapis.com/v1beta/properties/987654:runReport"
        )
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"
        assert kwargs["json"] == {
            "dateRanges": [{"startDate": "2026-08-01", "endDate": "2026-09-01"}],
            "dimensions": [{"name": "date"}, {"name": "sessionSource"}],
            "metrics": [{"name": "activeUsers"}, {"name": "sessions"}],
            "limit": 50,
        }


@pytest.mark.asyncio
async def test_get_report_empty_rows(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dimensionHeaders": [{"name": "date"}],
        "metricHeaders": [{"name": "activeUsers", "type": "TYPE_INTEGER"}],
        "rowCount": 0,
    }

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        report = await analytics_service.get_report(property_id="12345")

        assert report["property_id"] == "12345"
        assert report["rows"] == []
        assert report["row_count"] == 0


@pytest.mark.asyncio
async def test_get_report_full_resource_name(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        report = await analytics_service.get_report(property_id="properties/55555")

        assert report["property_id"] == "55555"
        assert report["property_name"] == "properties/55555"
        url, _ = mock_post.call_args
        assert (
            url[0]
            == "https://analyticsdata.googleapis.com/v1beta/properties/55555:runReport"
        )


@pytest.mark.asyncio
async def test_get_report_401_auth_error(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_post = AsyncMock(return_value=mock_response)

    with (
        patch("httpx.AsyncClient.get", new=mock_post),
        patch("httpx.AsyncClient.post", new=mock_post),
    ):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching GA4 report"
        ):
            await analytics_service.get_report(property_id="12345")


@pytest.mark.asyncio
async def test_get_report_429_quota_error(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Too Many Requests"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(GoogleQuotaError, match="rate limit exceeded"):
            await analytics_service.get_report(property_id="12345")


@pytest.mark.asyncio
async def test_get_report_500_api_error(analytics_service):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Error"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleApiError, match="Google Analytics API returned error 500"
        ):
            await analytics_service.get_report(property_id="12345")


def test_connector_returns_analytics_service():
    connector = GoogleConnector(
        credentials={"client_id": "test_id", "client_secret": "test_secret"},
        access_token="test_token",
    )
    service = connector.get_analytics_service()
    assert isinstance(service, GoogleAnalyticsService)
    assert service.access_token == "test_token"
