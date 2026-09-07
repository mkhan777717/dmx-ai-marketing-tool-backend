import logging
from typing import Any

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)
from app.integrations.secrets.service import secret_service

logger = logging.getLogger(__name__)


class GoogleAdsService:
    """
    Executes reporting queries against Google Ads API v25 searchStream.
    """

    BASE_URL = "https://googleads.googleapis.com/v25/customers"

    def __init__(
        self,
        access_token: str,
        developer_token: str | None = None,
        login_customer_id: str | None = None,
    ):
        if not access_token:
            raise ValueError("Access token required.")
        self.access_token = access_token
        self.developer_token = (
            developer_token
            or secret_service.get_secret("GOOGLE_ADS_DEVELOPER_TOKEN")
            or secret_service.get_provider_credentials("google").get("developer_token")
            or ""
        )
        self.login_customer_id = login_customer_id

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if self.developer_token:
            headers["developer-token"] = self.developer_token
        if self.login_customer_id:
            headers["login-customer-id"] = str(self.login_customer_id).replace("-", "")
        return headers

    async def get_report(
        self,
        customer_id: str,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        login_customer_id: str | None = None,
        query_override: str | None = None,
    ) -> dict[str, Any]:
        """
        Executes a campaign performance report query against Google Ads API v25 searchStream.

        :param customer_id: Clean Google Ads Customer ID (e.g. '6774894805' or 'customers/6774894805').
        :param start_date: Start date (YYYY-MM-DD or '30daysAgo').
        :param end_date: End date (YYYY-MM-DD or 'today').
        :param login_customer_id: Optional Manager (MCC) Account Customer ID for header.
        :param query_override: Optional custom GAQL query string.
        :return: Structured reporting dictionary.
        """
        if not customer_id:
            raise ValueError("Invalid or empty customer_id provided.")

        clean_customer_id = customer_id.split("/")[-1].replace("-", "")
        if not clean_customer_id:
            raise ValueError("Invalid or empty customer_id provided.")

        headers = self._get_headers()
        effective_login_id = login_customer_id or self.login_customer_id
        if effective_login_id:
            headers["login-customer-id"] = str(effective_login_id).replace("-", "")

        url = f"{self.BASE_URL}/{clean_customer_id}/googleAds:searchStream"

        if query_override:
            gaql = query_override
        else:
            if (
                start_date
                and end_date
                and len(start_date) == 10
                and len(end_date) == 10
                and start_date[4] == "-"
                and end_date[4] == "-"
            ):
                date_clause = (
                    f"WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'"
                )
            else:
                date_clause = "WHERE segments.date DURING LAST_30_DAYS"

            gaql = (
                "SELECT campaign.id, campaign.name, campaign.status, "
                "metrics.impressions, metrics.clicks, metrics.cost_micros "
                f"FROM campaign {date_clause}"
            )

        payload = {"query": gaql}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching Google Ads report: {response.text}"
                )
            elif response.status_code == 429:
                raise GoogleQuotaError("Google Ads API rate limit exceeded.")
            elif response.status_code >= 400:
                raise GoogleApiError(
                    f"Google Ads API error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            batches = data if isinstance(data, list) else [data]

            parsed_rows = []
            for batch in batches:
                for row in batch.get("results", []):
                    campaign = row.get("campaign", {})
                    metrics = row.get("metrics", {})

                    cost_micros = int(
                        metrics.get("costMicros", 0)
                        or metrics.get("cost_micros", 0)
                        or 0
                    )
                    cost = cost_micros / 1_000_000.0

                    parsed_rows.append(
                        {
                            "campaign_id": str(campaign.get("id", "")),
                            "campaign_name": campaign.get("name", ""),
                            "status": campaign.get("status", ""),
                            "impressions": int(metrics.get("impressions", 0) or 0),
                            "clicks": int(metrics.get("clicks", 0) or 0),
                            "cost_micros": cost_micros,
                            "cost": cost,
                        }
                    )

            return {
                "customer_id": clean_customer_id,
                "resource_name": f"customers/{clean_customer_id}",
                "query": gaql,
                "rows": parsed_rows,
                "row_count": len(parsed_rows),
            }
