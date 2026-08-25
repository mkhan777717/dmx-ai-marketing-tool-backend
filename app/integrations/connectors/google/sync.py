import logging
from typing import Any, Dict

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
)
from app.integrations.connectors.google.schemas import GoogleProfileResponse

logger = logging.getLogger(__name__)


class GoogleSyncEngine:
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {self.access_token}"}

    async def fetch_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's profile."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.USERINFO_URL, headers=self.headers)

            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch profile: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            validated_response = GoogleProfileResponse(**data)
            return validated_response.model_dump()

    async def fetch_accounts(self) -> list:
        """Fetches the Google Business Profile accounts."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.ACCOUNTS_URL, headers=self.headers)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching GMB accounts: {response.text}"
                )
            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch GMB accounts: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            return data.get("accounts", [])

    async def fetch_locations(self, account_name: str) -> list:
        """Fetches locations for a specific GMB account."""
        url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations?readMask=name,title"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching GMB locations: {response.text}"
                )
            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch GMB locations: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            return data.get("locations", [])

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            profile = await self.fetch_profile()

            accounts = await self.fetch_accounts()
            business_accounts = []

            for account in accounts:
                account_name_res = account.get("name", "")
                if not account_name_res:
                    continue

                # "accounts/12345" -> "12345"
                account_id = account_name_res.split("/")[-1]

                locations = await self.fetch_locations(account_name_res)
                parsed_locations = []

                for loc in locations:
                    loc_name_res = loc.get("name", "")
                    if not loc_name_res:
                        continue

                    # "accounts/123/locations/456" -> "456"
                    loc_id = loc_name_res.split("/")[-1]
                    parsed_locations.append(
                        {"location_id": loc_id, "location_name": loc.get("title", "")}
                    )

                business_accounts.append(
                    {
                        "account_id": account_id,
                        "account_name": account.get("accountName", ""),
                        "locations": parsed_locations,
                    }
                )

            return {
                "profile": profile,
                "business_accounts": business_accounts,
                "records_synced": 1 + len(business_accounts),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
