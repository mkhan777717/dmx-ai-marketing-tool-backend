import logging
from typing import Any, Dict

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
)
from app.integrations.connectors.google.schemas import GoogleProfileResponse
from app.integrations.connectors.google.search_console import (
    GoogleSearchConsoleService,
)
from app.integrations.secrets.service import secret_service

logger = logging.getLogger(__name__)


class GoogleSyncEngine:
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
    ACCOUNTS_URL = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    GA4_ACCOUNT_SUMMARIES_URL = (
        "https://analyticsadmin.googleapis.com/v1beta/accountSummaries"
    )
    GOOGLE_ADS_ACCESSIBLE_CUSTOMERS_URL = (
        "https://googleads.googleapis.com/v25/customers:listAccessibleCustomers"
    )

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

    YOUTUBE_CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

    async def fetch_youtube_channels(self) -> list[dict[str, Any]]:
        """Fetches the authenticated user's YouTube channels via YouTube Data API v3."""
        params = {
            "part": "snippet,contentDetails",
            "mine": "true",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.YOUTUBE_CHANNELS_URL, headers=self.headers, params=params
            )

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching YouTube channels: {response.text}"
                )
            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch YouTube channels: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            items = data.get("items", [])
            parsed_channels = []
            for item in items:
                channel_id = item.get("id")
                snippet = item.get("snippet", {})
                if not channel_id:
                    continue

                thumbnails = snippet.get("thumbnails", {})
                thumbnail_url = (
                    thumbnails.get("default", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("high", {}).get("url")
                    or ""
                )

                parsed_channels.append(
                    {
                        "channel_id": channel_id,
                        "title": snippet.get("title", ""),
                        "custom_url": snippet.get("customUrl", ""),
                        "thumbnail_url": thumbnail_url,
                        "description": snippet.get("description", ""),
                    }
                )

            return parsed_channels

    async def fetch_ga4_properties(self) -> list[dict[str, Any]]:
        """Fetches the accessible Google Analytics 4 (GA4) properties via GA4 Admin API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.GA4_ACCOUNT_SUMMARIES_URL, headers=self.headers
            )

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching GA4 properties: {response.text}"
                )
            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch GA4 properties: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            account_summaries = data.get("accountSummaries", [])
            parsed_properties = []

            for acc in account_summaries:
                acc_resource = acc.get("account", "")
                acc_id = acc_resource.split("/")[-1] if acc_resource else ""
                acc_display_name = acc.get("displayName", "")

                for prop_sum in acc.get("propertySummaries", []):
                    prop_resource = prop_sum.get("property", "")
                    if not prop_resource:
                        continue

                    prop_id = prop_resource.split("/")[-1]
                    prop_display_name = prop_sum.get("displayName", "") or prop_id

                    parsed_properties.append(
                        {
                            "property_id": prop_id,
                            "property_name": prop_resource,
                            "display_name": prop_display_name,
                            "account_id": acc_id,
                            "account_name": acc_display_name,
                        }
                    )

            return parsed_properties

    async def fetch_google_ads_customers(
        self, developer_token: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetches accessible Google Ads customer accounts and their CustomerClient manager hierarchy children via Google Ads API v25."""
        headers = dict(self.headers)
        dev_token = (
            developer_token
            or secret_service.get_secret("GOOGLE_ADS_DEVELOPER_TOKEN")
            or secret_service.get_provider_credentials("google").get("developer_token")
            or ""
        )
        if dev_token:
            headers["developer-token"] = dev_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.GOOGLE_ADS_ACCESSIBLE_CUSTOMERS_URL, headers=headers
            )

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching Google Ads customers: {response.text}"
                )
            if response.status_code != 200:
                raise GoogleApiError(
                    f"Failed to fetch Google Ads customers: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            resource_names = data.get("resourceNames", [])
            discovered_customers: dict[str, dict[str, Any]] = {}

            # 1. Populate accessible accounts from listAccessibleCustomers
            for resource_name in resource_names:
                if not resource_name:
                    continue
                customer_id = resource_name.split("/")[-1].replace("-", "")
                if not customer_id:
                    continue
                discovered_customers[customer_id] = {
                    "customer_id": customer_id,
                    "resource_name": f"customers/{customer_id}",
                    "descriptive_name": f"Customer {customer_id}",
                }

            # 2. Discover CustomerClient hierarchy for each accessible account
            gaql = (
                "SELECT customer_client.id, customer_client.descriptive_name, "
                "customer_client.manager, customer_client.level, "
                "customer_client.client_customer, customer_client.status "
                "FROM customer_client"
            )

            for manager_id in list(discovered_customers.keys()):
                mcc_headers = dict(headers)
                mcc_headers["login-customer-id"] = manager_id
                mcc_headers["Content-Type"] = "application/json"

                url = f"https://googleads.googleapis.com/v25/customers/{manager_id}/googleAds:searchStream"
                try:
                    stream_resp = await client.post(
                        url, headers=mcc_headers, json={"query": gaql}
                    )
                    if stream_resp.status_code != 200:
                        logger.debug(
                            f"CustomerClient hierarchy query for manager {manager_id} returned status {stream_resp.status_code}: {stream_resp.text}"
                        )
                        continue

                    stream_data = stream_resp.json()
                    batches = (
                        stream_data if isinstance(stream_data, list) else [stream_data]
                    )

                    for batch in batches:
                        for row in batch.get("results", []):
                            cc = (
                                row.get("customerClient")
                                or row.get("customer_client")
                                or {}
                            )
                            client_id = str(cc.get("id") or "").replace("-", "")
                            if not client_id:
                                continue

                            desc_name = (
                                cc.get("descriptiveName")
                                or cc.get("descriptive_name")
                                or f"Customer {client_id}"
                            )
                            is_manager = bool(cc.get("manager"))
                            level_val = cc.get("level")
                            level = int(level_val) if level_val is not None else None
                            client_customer = (
                                cc.get("clientCustomer")
                                or cc.get("client_customer")
                                or f"customers/{client_id}"
                            )

                            if client_id in discovered_customers:
                                existing = discovered_customers[client_id]
                                if desc_name and desc_name != f"Customer {client_id}":
                                    existing["descriptive_name"] = desc_name
                                existing["is_manager"] = is_manager
                                if level is not None:
                                    existing["level"] = level
                                existing["client_customer"] = client_customer
                                if (
                                    client_id != manager_id
                                    and "login_customer_id" not in existing
                                ):
                                    existing["login_customer_id"] = manager_id
                            else:
                                client_entry: dict[str, Any] = {
                                    "customer_id": client_id,
                                    "resource_name": f"customers/{client_id}",
                                    "descriptive_name": desc_name,
                                    "is_manager": is_manager,
                                    "level": level,
                                    "client_customer": client_customer,
                                }
                                if client_id != manager_id:
                                    client_entry["login_customer_id"] = manager_id
                                discovered_customers[client_id] = client_entry

                except Exception as e:
                    logger.warning(
                        f"Error querying CustomerClient hierarchy for manager {manager_id}: {e}"
                    )

            return list(discovered_customers.values())

    async def fetch_search_console_sites(self) -> list[dict[str, Any]]:
        """Fetches the accessible Google Search Console verified sites."""
        search_console_service = GoogleSearchConsoleService(self.access_token)
        return await search_console_service.get_sites()

    async def perform_sync(
        self, sync_type: str = "full", provider: str = "google"
    ) -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            profile = await self.fetch_profile()
            provider_lower = (provider or "google").lower()

            business_accounts = []
            youtube_channels = []
            ga4_properties = []
            google_ads_customers = []
            search_console_sites = []

            if provider_lower in ("youtube", "youtube_channel"):
                # For YouTube provider sync, ONLY fetch YouTube channels.
                # Do NOT call GMB fetch_accounts() or fetch_locations().
                try:
                    youtube_channels = await self.fetch_youtube_channels()
                except Exception as e:
                    logger.warning(f"Fetching YouTube channels during sync failed: {e}")
            else:
                # For Google Business Profile sync, fetch GMB accounts, locations, YouTube channels, GA4 properties, Google Ads customers, and Search Console sites
                try:
                    accounts = await self.fetch_accounts()
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
                                {
                                    "location_id": loc_id,
                                    "location_name": loc.get("title", ""),
                                }
                            )

                        business_accounts.append(
                            {
                                "account_id": account_id,
                                "account_name": account.get("accountName", ""),
                                "locations": parsed_locations,
                            }
                        )
                except Exception as e:
                    logger.warning(f"Fetching GMB accounts during sync failed: {e}")

                try:
                    youtube_channels = await self.fetch_youtube_channels()
                except Exception as e:
                    logger.warning(f"Fetching YouTube channels during sync failed: {e}")

                try:
                    ga4_properties = await self.fetch_ga4_properties()
                except Exception as e:
                    logger.warning(f"Fetching GA4 properties during sync failed: {e}")

                try:
                    google_ads_customers = await self.fetch_google_ads_customers()
                except Exception as e:
                    logger.warning(
                        f"Fetching Google Ads customers during sync failed: {e}"
                    )

                try:
                    search_console_sites = await self.fetch_search_console_sites()
                except Exception as e:
                    logger.warning(
                        f"Fetching Search Console sites during sync failed: {e}"
                    )

            return {
                "profile": profile,
                "business_accounts": business_accounts,
                "youtube_channels": youtube_channels,
                "ga4_properties": ga4_properties,
                "google_ads_customers": google_ads_customers,
                "search_console_sites": search_console_sites,
                "records_synced": (
                    1
                    + len(business_accounts)
                    + len(youtube_channels)
                    + len(ga4_properties)
                    + len(google_ads_customers)
                    + len(search_console_sites)
                ),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
