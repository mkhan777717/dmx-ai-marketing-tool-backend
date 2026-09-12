import logging
import urllib.parse
from typing import Any

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)

logger = logging.getLogger(__name__)


class GoogleSearchConsoleService:
    """
    Service for interacting with Google Search Console REST API v1.
    """

    BASE_URL = "https://www.googleapis.com/webmasters/v3"

    def __init__(self, access_token: str):
        if not access_token:
            raise ValueError("Access token required.")
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get_sites(self) -> list[dict[str, Any]]:
        """
        Fetches the verified sites/properties for the authenticated user via Search Console sites.list.

        :return: List of normalized site dictionaries containing site_url and permission_level.
        """
        url = f"{self.BASE_URL}/sites"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self.headers)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching Search Console sites: {response.text}"
                )
            elif response.status_code == 429:
                raise GoogleQuotaError("Google Search Console rate limit exceeded.")
            elif response.status_code >= 400:
                raise GoogleApiError(
                    f"Google Search Console API returned error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            site_entries = data.get("siteEntry", [])
            parsed_sites = []

            for entry in site_entries:
                site_url = entry.get("siteUrl", "")
                if not site_url:
                    continue
                permission_level = entry.get("permissionLevel", "")
                parsed_sites.append(
                    {
                        "site_url": site_url,
                        "permission_level": permission_level,
                    }
                )

            return parsed_sites

    async def get_search_analytics(
        self,
        site_url: str,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        dimensions: list[str] | None = None,
        row_limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Executes a Search Analytics query request against Google Search Console API v1 /sites/{siteUrl}/searchAnalytics/query.

        :param site_url: Verified property URL (e.g. 'https://example.com/' or 'sc-domain:example.com').
        :param start_date: Start date (YYYY-MM-DD or relative string).
        :param end_date: End date (YYYY-MM-DD or relative string).
        :param dimensions: Optional list of dimensions (e.g. ['query', 'page', 'country', 'device', 'date']).
        :param row_limit: Optional row limit.
        :return: Structured report dictionary containing keys, clicks, impressions, ctr, and position.
        """
        if not site_url:
            raise ValueError("Invalid or empty site_url provided.")

        encoded_site_url = urllib.parse.quote(site_url, safe="")
        url = f"{self.BASE_URL}/sites/{encoded_site_url}/searchAnalytics/query"

        dim_list = dimensions or ["query"]
        payload: dict[str, Any] = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dim_list,
        }
        if row_limit is not None:
            payload["rowLimit"] = row_limit

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching Search Console analytics: {response.text}"
                )
            elif response.status_code == 429:
                raise GoogleQuotaError("Google Search Console rate limit exceeded.")
            elif response.status_code >= 400:
                raise GoogleApiError(
                    f"Google Search Console API returned error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            rows_data = data.get("rows", [])
            parsed_rows = []

            for r in rows_data:
                keys = r.get("keys", [])
                clicks = int(r.get("clicks", 0) or 0)
                impressions = int(r.get("impressions", 0) or 0)
                ctr = float(r.get("ctr", 0.0) or 0.0)
                position = float(r.get("position", 0.0) or 0.0)

                parsed_rows.append(
                    {
                        "keys": keys,
                        "clicks": clicks,
                        "impressions": impressions,
                        "ctr": ctr,
                        "position": position,
                    }
                )

            return {
                "site_url": site_url,
                "start_date": start_date,
                "end_date": end_date,
                "dimensions": dim_list,
                "rows": parsed_rows,
                "row_count": len(parsed_rows),
            }
