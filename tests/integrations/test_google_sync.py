from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
)
from app.integrations.connectors.google.sync import GoogleSyncEngine


@pytest.fixture
def google_sync_engine():
    return GoogleSyncEngine("test_access_token")


@pytest.mark.asyncio
async def test_fetch_profile_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "12345",
        "email": "test@example.com",
        "verified_email": True,
        "name": "Test User",
        "given_name": "Test",
        "family_name": "User",
        "picture": "https://example.com/pic.jpg",
        "locale": "en",
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        profile = await google_sync_engine.fetch_profile()
        assert profile["id"] == "12345"
        assert profile["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_fetch_profile_with_missing_optional_fields(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "109876543210987654321",
        "email": "creator@example.com",
        "verified_email": True,
        # missing given_name, family_name, picture, locale, name
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        profile = await google_sync_engine.fetch_profile()
        assert profile["id"] == "109876543210987654321"
        assert profile["email"] == "creator@example.com"
        assert profile["given_name"] is None
        assert profile["family_name"] is None
        assert profile["picture"] is None
        assert profile["locale"] is None


@pytest.mark.asyncio
async def test_fetch_accounts_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "accounts": [
            {"name": "accounts/111", "accountName": "Test Account 1"},
            {"name": "accounts/222", "accountName": "Test Account 2"},
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        accounts = await google_sync_engine.fetch_accounts()
        assert len(accounts) == 2
        assert accounts[0]["name"] == "accounts/111"


@pytest.mark.asyncio
async def test_fetch_locations_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "locations": [
            {"name": "accounts/111/locations/333", "title": "Test Location 1"},
            {"name": "accounts/111/locations/444", "title": "Test Location 2"},
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        locations = await google_sync_engine.fetch_locations("accounts/111")
        assert len(locations) == 2
        assert locations[0]["title"] == "Test Location 1"


@pytest.mark.asyncio
async def test_perform_sync_full_success(google_sync_engine):
    with (
        patch.object(google_sync_engine, "fetch_profile") as mock_profile,
        patch.object(google_sync_engine, "fetch_accounts") as mock_accounts,
        patch.object(google_sync_engine, "fetch_locations") as mock_locations,
        patch.object(google_sync_engine, "fetch_youtube_channels") as mock_yt,
        patch.object(google_sync_engine, "fetch_ga4_properties") as mock_ga4,
    ):
        mock_profile.return_value = {"id": "123"}
        mock_accounts.return_value = [
            {"name": "accounts/111", "accountName": "Test Account 1"}
        ]
        mock_locations.return_value = [
            {"name": "accounts/111/locations/333", "title": "Test Location 1"}
        ]
        mock_yt.return_value = []
        mock_ga4.return_value = [
            {
                "property_id": "987654",
                "property_name": "properties/987654",
                "display_name": "Main GA4 Property",
                "account_id": "12345",
                "account_name": "Test Company",
            }
        ]

        result = await google_sync_engine.perform_sync()

        assert result["profile"]["id"] == "123"
        assert len(result["business_accounts"]) == 1
        assert result["business_accounts"][0]["account_id"] == "111"
        assert result["business_accounts"][0]["account_name"] == "Test Account 1"
        assert len(result["business_accounts"][0]["locations"]) == 1
        assert result["business_accounts"][0]["locations"][0]["location_id"] == "333"
        assert (
            result["business_accounts"][0]["locations"][0]["location_name"]
            == "Test Location 1"
        )
        assert len(result["ga4_properties"]) == 1
        assert result["ga4_properties"][0]["property_id"] == "987654"
        assert result["records_synced"] == 3


@pytest.mark.asyncio
async def test_perform_sync_empty_accounts_and_locations(google_sync_engine):
    with (
        patch.object(google_sync_engine, "fetch_profile") as mock_profile,
        patch.object(google_sync_engine, "fetch_accounts") as mock_accounts,
        patch.object(google_sync_engine, "fetch_youtube_channels") as mock_yt,
        patch.object(google_sync_engine, "fetch_ga4_properties") as mock_ga4,
    ):
        mock_profile.return_value = {"id": "123"}
        mock_accounts.return_value = []
        mock_yt.return_value = []
        mock_ga4.return_value = []

        result = await google_sync_engine.perform_sync()

        assert len(result["business_accounts"]) == 0
        assert result["records_synced"] == 1


@pytest.mark.asyncio
async def test_fetch_accounts_auth_error(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(GoogleAuthError):
            await google_sync_engine.fetch_accounts()


@pytest.mark.asyncio
async def test_fetch_locations_api_error(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Error"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(GoogleApiError):
            await google_sync_engine.fetch_locations("accounts/111")


@pytest.mark.asyncio
async def test_perform_sync_malformed_ids(google_sync_engine):
    with (
        patch.object(google_sync_engine, "fetch_profile") as mock_profile,
        patch.object(google_sync_engine, "fetch_accounts") as mock_accounts,
        patch.object(google_sync_engine, "fetch_locations") as mock_locations,
        patch.object(google_sync_engine, "fetch_youtube_channels") as mock_yt,
        patch.object(google_sync_engine, "fetch_ga4_properties") as mock_ga4,
    ):
        mock_profile.return_value = {"id": "123"}
        mock_yt.return_value = []
        mock_ga4.return_value = []
        # missing "name" key
        mock_accounts.return_value = [{"accountName": "Test Account 1"}]

        result = await google_sync_engine.perform_sync()
        assert len(result["business_accounts"]) == 0

        # Now test locations missing name
        mock_accounts.return_value = [
            {"name": "accounts/111", "accountName": "Test Account 1"}
        ]
        mock_locations.return_value = [{"title": "Test Location 1"}]

        result2 = await google_sync_engine.perform_sync()
        assert len(result2["business_accounts"]) == 1
        assert len(result2["business_accounts"][0]["locations"]) == 0


@pytest.mark.asyncio
async def test_fetch_youtube_channels_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": "UC_channel_123",
                "snippet": {
                    "title": "My YouTube Channel",
                    "customUrl": "@mychannel",
                    "description": "Welcome to my channel!",
                    "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
                },
            }
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        channels = await google_sync_engine.fetch_youtube_channels()

        assert len(channels) == 1
        assert channels[0]["channel_id"] == "UC_channel_123"
        assert channels[0]["title"] == "My YouTube Channel"
        assert channels[0]["custom_url"] == "@mychannel"
        assert channels[0]["thumbnail_url"] == "https://example.com/thumb.jpg"

        mock_get.assert_called_once()
        url, kwargs = mock_get.call_args
        assert url[0] == "https://www.googleapis.com/youtube/v3/channels"
        assert kwargs["params"] == {"part": "snippet,contentDetails", "mine": "true"}
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"


@pytest.mark.asyncio
async def test_fetch_youtube_channels_empty(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": []}

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        channels = await google_sync_engine.fetch_youtube_channels()
        assert channels == []


@pytest.mark.asyncio
async def test_fetch_youtube_channels_auth_error_401(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching YouTube channels"
        ):
            await google_sync_engine.fetch_youtube_channels()


@pytest.mark.asyncio
async def test_fetch_youtube_channels_auth_error_403(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Quota or permission denied"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching YouTube channels"
        ):
            await google_sync_engine.fetch_youtube_channels()


@pytest.mark.asyncio
async def test_perform_sync_youtube_provider_only_fetches_channels(google_sync_engine):
    with (
        patch.object(google_sync_engine, "fetch_profile") as mock_profile,
        patch.object(google_sync_engine, "fetch_accounts") as mock_accounts,
        patch.object(google_sync_engine, "fetch_youtube_channels") as mock_yt,
    ):
        mock_profile.return_value = {"id": "123"}
        mock_yt.return_value = [{"channel_id": "UC123", "title": "YT Channel"}]

        result = await google_sync_engine.perform_sync(
            sync_type="full", provider="youtube"
        )

        assert result["profile"]["id"] == "123"
        assert result["business_accounts"] == []
        assert result["youtube_channels"] == [
            {"channel_id": "UC123", "title": "YT Channel"}
        ]
        mock_accounts.assert_not_called()
        mock_yt.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_ga4_properties_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "accountSummaries": [
            {
                "account": "accounts/12345",
                "displayName": "Test Company",
                "propertySummaries": [
                    {
                        "property": "properties/987654",
                        "displayName": "Main GA4 Property",
                        "propertyType": "PROPERTY_TYPE_ORDINARY",
                    }
                ],
            }
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        props = await google_sync_engine.fetch_ga4_properties()

        assert len(props) == 1
        assert props[0]["property_id"] == "987654"
        assert props[0]["property_name"] == "properties/987654"
        assert props[0]["display_name"] == "Main GA4 Property"
        assert props[0]["account_id"] == "12345"
        assert props[0]["account_name"] == "Test Company"

        mock_get.assert_called_once()
        url, kwargs = mock_get.call_args
        assert url[0] == "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
        assert kwargs["headers"]["Authorization"] == "Bearer test_access_token"


@pytest.mark.asyncio
async def test_fetch_ga4_properties_empty(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"accountSummaries": []}

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        props = await google_sync_engine.fetch_ga4_properties()
        assert props == []


@pytest.mark.asyncio
async def test_fetch_ga4_properties_auth_error_401(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching GA4 properties"
        ):
            await google_sync_engine.fetch_ga4_properties()


@pytest.mark.asyncio
async def test_fetch_ga4_properties_api_error_500(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(GoogleApiError, match="Failed to fetch GA4 properties"):
            await google_sync_engine.fetch_ga4_properties()


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_success(google_sync_engine):
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "resourceNames": [
            "customers/1234567890",
            "customers/6774894805",
        ]
    }

    mock_post_response = MagicMock()
    mock_post_response.status_code = 403
    mock_post_response.text = "Forbidden"

    mock_get = AsyncMock(return_value=mock_get_response)
    mock_post = AsyncMock(return_value=mock_post_response)

    with (
        patch("httpx.AsyncClient.get", new=mock_get),
        patch("httpx.AsyncClient.post", new=mock_post),
        patch(
            "app.integrations.secrets.service.secret_service.get_secret",
            return_value="test_dev_token",
        ),
    ):
        customers = await google_sync_engine.fetch_google_ads_customers()
        assert len(customers) == 2
        assert customers[0]["customer_id"] == "1234567890"
        assert customers[0]["resource_name"] == "customers/1234567890"
        assert customers[0]["descriptive_name"] == "Customer 1234567890"
        assert customers[1]["customer_id"] == "6774894805"

        # Verify developer-token header passed
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["developer-token"] == "test_dev_token"


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_hierarchy_discovery(google_sync_engine):
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"resourceNames": ["customers/6774894805"]}

    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = [
        {
            "results": [
                {
                    "customerClient": {
                        "resourceName": "customers/6774894805/customerClients/6774894805",
                        "clientCustomer": "customers/6774894805",
                        "id": "6774894805",
                        "descriptiveName": "DMX Manager Account",
                        "manager": True,
                        "level": "0",
                        "status": "ENABLED",
                    }
                },
                {
                    "customerClient": {
                        "resourceName": "customers/6774894805/customerClients/8109628125",
                        "clientCustomer": "customers/8109628125",
                        "id": "8109628125",
                        "descriptiveName": "NEW DMX Test Client",
                        "manager": False,
                        "level": "1",
                        "status": "ENABLED",
                    }
                },
            ]
        }
    ]

    mock_get = AsyncMock(return_value=mock_get_response)
    mock_post = AsyncMock(return_value=mock_post_response)

    with (
        patch("httpx.AsyncClient.get", new=mock_get),
        patch("httpx.AsyncClient.post", new=mock_post),
        patch(
            "app.integrations.secrets.service.secret_service.get_secret",
            return_value="test_dev_token",
        ),
    ):
        customers = await google_sync_engine.fetch_google_ads_customers()
        assert len(customers) == 2

        manager_acc = next(c for c in customers if c["customer_id"] == "6774894805")
        client_acc = next(c for c in customers if c["customer_id"] == "8109628125")

        assert manager_acc["descriptive_name"] == "DMX Manager Account"
        assert manager_acc["is_manager"] is True
        assert manager_acc["level"] == 0
        assert "login_customer_id" not in manager_acc

        assert client_acc["descriptive_name"] == "NEW DMX Test Client"
        assert client_acc["is_manager"] is False
        assert client_acc["level"] == 1
        assert client_acc["login_customer_id"] == "6774894805"

        # Verify headers passed in post request include login-customer-id
        assert (
            mock_post.call_args.kwargs["headers"]["login-customer-id"] == "6774894805"
        )
        assert (
            mock_post.call_args.kwargs["headers"]["developer-token"] == "test_dev_token"
        )


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_deduplication(google_sync_engine):
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {
        "resourceNames": ["customers/6774894805", "customers/8109628125"]
    }

    mock_post_response = MagicMock()
    mock_post_response.status_code = 200
    mock_post_response.json.return_value = [
        {
            "results": [
                {
                    "customerClient": {
                        "id": "8109628125",
                        "descriptiveName": "NEW DMX Test Client",
                        "manager": False,
                        "level": "1",
                    }
                }
            ]
        }
    ]

    mock_get = AsyncMock(return_value=mock_get_response)
    mock_post = AsyncMock(return_value=mock_post_response)

    with (
        patch("httpx.AsyncClient.get", new=mock_get),
        patch("httpx.AsyncClient.post", new=mock_post),
    ):
        customers = await google_sync_engine.fetch_google_ads_customers()
        # Should deduplicate 8109628125 and update its metadata
        customer_ids = [c["customer_id"] for c in customers]
        assert len(customer_ids) == len(set(customer_ids))
        assert "8109628125" in customer_ids
        assert "6774894805" in customer_ids


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_empty(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"resourceNames": []}

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        customers = await google_sync_engine.fetch_google_ads_customers()
        assert customers == []


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_auth_error_401(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleAuthError, match="Permission denied fetching Google Ads customers"
        ):
            await google_sync_engine.fetch_google_ads_customers()


@pytest.mark.asyncio
async def test_fetch_google_ads_customers_api_error_500(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Error"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(
            GoogleApiError, match="Failed to fetch Google Ads customers"
        ):
            await google_sync_engine.fetch_google_ads_customers()


@pytest.mark.asyncio
async def test_google_sync_includes_google_ads_customers_and_handles_failure_gracefully(
    google_sync_engine,
):
    profile_response = MagicMock()
    profile_response.status_code = 200
    profile_response.json.return_value = {
        "id": "user123",
        "email": "user@example.com",
        "verified_email": True,
    }

    accounts_response = MagicMock()
    accounts_response.status_code = 200
    accounts_response.json.return_value = {"accounts": []}

    yt_response = MagicMock()
    yt_response.status_code = 200
    yt_response.json.return_value = {"items": []}

    ga4_response = MagicMock()
    ga4_response.status_code = 200
    ga4_response.json.return_value = {"accountSummaries": []}

    ads_response = MagicMock()
    ads_response.status_code = 500  # Failure in Ads should not break sync
    ads_response.text = "Ads API Unavailable"

    sc_response = MagicMock()
    sc_response.status_code = 200
    sc_response.json.return_value = {"siteEntry": []}

    mock_get = AsyncMock(
        side_effect=[
            profile_response,
            accounts_response,
            yt_response,
            ga4_response,
            ads_response,
            sc_response,
        ]
    )

    with patch("httpx.AsyncClient.get", new=mock_get):
        sync_result = await google_sync_engine.perform_sync(
            sync_type="full", provider="google"
        )
        assert sync_result["profile"]["email"] == "user@example.com"
        assert sync_result["google_ads_customers"] == []
        assert sync_result["search_console_sites"] == []
        assert sync_result["records_synced"] == 1


@pytest.mark.asyncio
async def test_fetch_search_console_sites_success(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "siteEntry": [
            {"siteUrl": "https://example.com/", "permissionLevel": "siteOwner"}
        ]
    }

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        sites = await google_sync_engine.fetch_search_console_sites()
        assert len(sites) == 1
        assert sites[0]["site_url"] == "https://example.com/"
        assert sites[0]["permission_level"] == "siteOwner"


@pytest.mark.asyncio
async def test_fetch_search_console_sites_empty(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"siteEntry": []}

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        sites = await google_sync_engine.fetch_search_console_sites()
        assert sites == []


@pytest.mark.asyncio
async def test_fetch_search_console_sites_auth_error(google_sync_engine):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"

    mock_get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient.get", new=mock_get):
        with pytest.raises(GoogleAuthError):
            await google_sync_engine.fetch_search_console_sites()


@pytest.mark.asyncio
async def test_google_sync_handles_search_console_failure_gracefully(
    google_sync_engine,
):
    profile_response = MagicMock()
    profile_response.status_code = 200
    profile_response.json.return_value = {
        "id": "user123",
        "email": "user@example.com",
        "verified_email": True,
    }

    accounts_response = MagicMock()
    accounts_response.status_code = 200
    accounts_response.json.return_value = {"accounts": []}

    yt_response = MagicMock()
    yt_response.status_code = 200
    yt_response.json.return_value = {"items": []}

    ga4_response = MagicMock()
    ga4_response.status_code = 200
    ga4_response.json.return_value = {"accountSummaries": []}

    ads_response = MagicMock()
    ads_response.status_code = 200
    ads_response.json.return_value = {"resourceNames": []}

    sc_response = MagicMock()
    sc_response.status_code = 500  # Failure in Search Console should not break sync
    sc_response.text = "Search Console API Unavailable"

    mock_get = AsyncMock(
        side_effect=[
            profile_response,
            accounts_response,
            yt_response,
            ga4_response,
            ads_response,
            sc_response,
        ]
    )

    with patch("httpx.AsyncClient.get", new=mock_get):
        sync_result = await google_sync_engine.perform_sync(
            sync_type="full", provider="google"
        )
        assert sync_result["profile"]["email"] == "user@example.com"
        assert sync_result["search_console_sites"] == []
        assert sync_result["records_synced"] == 1
