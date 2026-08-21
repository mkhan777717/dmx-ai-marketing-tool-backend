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
    ):

        mock_profile.return_value = {"id": "123"}
        mock_accounts.return_value = [
            {"name": "accounts/111", "accountName": "Test Account 1"}
        ]
        mock_locations.return_value = [
            {"name": "accounts/111/locations/333", "title": "Test Location 1"}
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
        assert result["records_synced"] == 2


@pytest.mark.asyncio
async def test_perform_sync_empty_accounts_and_locations(google_sync_engine):
    with (
        patch.object(google_sync_engine, "fetch_profile") as mock_profile,
        patch.object(google_sync_engine, "fetch_accounts") as mock_accounts,
    ):

        mock_profile.return_value = {"id": "123"}
        mock_accounts.return_value = []

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
    ):

        mock_profile.return_value = {"id": "123"}
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
