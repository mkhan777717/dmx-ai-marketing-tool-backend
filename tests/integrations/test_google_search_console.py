from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.connectors.google.connector import GoogleConnector
from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)
from app.integrations.connectors.google.search_console import (
    GoogleSearchConsoleService,
)


@pytest.fixture
def sc_service():
    return GoogleSearchConsoleService(access_token="test_access_token")


@pytest.mark.asyncio
async def test_get_sites_success(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "siteEntry": [
            {
                "siteUrl": "https://example.com/",
                "permissionLevel": "siteOwner",
            },
            {
                "siteUrl": "sc-domain:example.com",
                "permissionLevel": "siteFullUser",
            },
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        sites = await sc_service.get_sites()

        assert len(sites) == 2
        assert sites[0]["site_url"] == "https://example.com/"
        assert sites[0]["permission_level"] == "siteOwner"
        assert sites[1]["site_url"] == "sc-domain:example.com"
        assert sites[1]["permission_level"] == "siteFullUser"

        mock_get.assert_called_once()
        url, kwargs = mock_get.call_args
        assert url[0] == "https://www.googleapis.com/webmasters/v3/sites"
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"


@pytest.mark.asyncio
async def test_get_sites_empty(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"siteEntry": []}

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        sites = await sc_service.get_sites()
        assert sites == []


@pytest.mark.asyncio
async def test_get_sites_auth_error_401(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Search Console sites"
        ):
            await sc_service.get_sites()


@pytest.mark.asyncio
async def test_get_sites_auth_error_403(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Search Console sites"
        ):
            await sc_service.get_sites()


@pytest.mark.asyncio
async def test_get_sites_quota_error_429(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate Limit Exceeded"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleQuotaError, match="Google Search Console rate limit exceeded"
        ):
            await sc_service.get_sites()


@pytest.mark.asyncio
async def test_get_sites_api_error_500(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleApiError, match="Google Search Console API returned error 500"
        ):
            await sc_service.get_sites()


def test_missing_access_token_raises_value_error():
    with pytest.raises(ValueError, match="Access token required"):
        GoogleSearchConsoleService(access_token="")


def test_connector_returns_search_console_service():
    connector = GoogleConnector(
        credentials={"client_id": "cid", "client_secret": "cs"},
        access_token="test_token",
    )
    sc_service = connector.get_search_console_service()
    assert isinstance(sc_service, GoogleSearchConsoleService)
    assert sc_service.access_token == "test_token"


@pytest.mark.asyncio
async def test_get_search_analytics_success(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "rows": [
            {
                "keys": ["dmx ai marketing"],
                "clicks": 120,
                "impressions": 3500,
                "ctr": 0.034,
                "position": 2.1,
            }
        ]
    }

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        res = await sc_service.get_search_analytics(
            site_url="https://example.com/",
            start_date="2026-08-01",
            end_date="2026-09-01",
            dimensions=["query"],
            row_limit=50,
        )

        assert res["site_url"] == "https://example.com/"
        assert res["start_date"] == "2026-08-01"
        assert res["end_date"] == "2026-09-01"
        assert res["dimensions"] == ["query"]
        assert res["row_count"] == 1
        assert res["rows"][0]["keys"] == ["dmx ai marketing"]
        assert res["rows"][0]["clicks"] == 120
        assert res["rows"][0]["impressions"] == 3500
        assert res["rows"][0]["ctr"] == 0.034
        assert res["rows"][0]["position"] == 2.1

        mock_post.assert_called_once()
        url, kwargs = mock_post.call_args
        assert (
            url[0]
            == "https://www.googleapis.com/webmasters/v3/sites/https%3A%2F%2Fexample.com%2F/searchAnalytics/query"
        )
        assert kwargs["json"]["startDate"] == "2026-08-01"
        assert kwargs["json"]["endDate"] == "2026-09-01"
        assert kwargs["json"]["dimensions"] == ["query"]
        assert kwargs["json"]["rowLimit"] == 50


@pytest.mark.asyncio
async def test_get_search_analytics_sc_domain_url_encoding(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"rows": []}

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        res = await sc_service.get_search_analytics(site_url="sc-domain:example.com")

        assert res["site_url"] == "sc-domain:example.com"
        assert res["row_count"] == 0
        assert res["rows"] == []

        url, _ = mock_post.call_args
        assert (
            url[0]
            == "https://www.googleapis.com/webmasters/v3/sites/sc-domain%3Aexample.com/searchAnalytics/query"
        )


@pytest.mark.asyncio
async def test_get_search_analytics_auth_error_401(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Search Console analytics"
        ):
            await sc_service.get_search_analytics(site_url="https://example.com/")


@pytest.mark.asyncio
async def test_get_search_analytics_auth_error_403(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Search Console analytics"
        ):
            await sc_service.get_search_analytics(site_url="https://example.com/")


@pytest.mark.asyncio
async def test_get_search_analytics_quota_error_429(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Quota exceeded"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleQuotaError, match="Google Search Console rate limit exceeded"
        ):
            await sc_service.get_search_analytics(site_url="https://example.com/")


@pytest.mark.asyncio
async def test_get_search_analytics_api_error_500(sc_service):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.post", new=mock_post):
        with pytest.raises(
            GoogleApiError, match="Google Search Console API returned error 500"
        ):
            await sc_service.get_search_analytics(site_url="https://example.com/")


@pytest.mark.asyncio
async def test_get_search_analytics_missing_site_url_raises_value_error(sc_service):
    with pytest.raises(ValueError, match="Invalid or empty site_url provided"):
        await sc_service.get_search_analytics(site_url="")
