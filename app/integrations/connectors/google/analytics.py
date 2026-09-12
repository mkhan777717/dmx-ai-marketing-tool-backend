import logging
from typing import Any

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)

logger = logging.getLogger(__name__)


class GoogleAnalyticsService:
    BASE_URL = "https://analyticsdata.googleapis.com/v1beta"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get_report(
        self,
        property_id: str,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Executes a GA4 runReport request using the Google Analytics Data API v1beta.

        :param property_id: Clean GA4 Property ID (e.g. '123456') or resource name ('properties/123456').
        :param start_date: Start date for reporting (YYYY-MM-DD or relative like '30daysAgo').
        :param end_date: End date for reporting (YYYY-MM-DD or relative like 'today').
        :param dimensions: Optional list of dimension names (e.g. ['date', 'sessionSource']).
        :param metrics: Optional list of metric names (e.g. ['activeUsers', 'sessions']).
        :param limit: Optional row limit.
        :return: Structured report dictionary containing headers, rows, and row_count.
        """
        clean_prop = (
            property_id
            if property_id.startswith("properties/")
            else f"properties/{property_id}"
        )
        url = f"{self.BASE_URL}/{clean_prop}:runReport"

        dim_list = dimensions or ["date"]
        met_list = metrics or ["activeUsers", "sessions", "screenPageViews"]

        payload: dict[str, Any] = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": d} for d in dim_list],
            "metrics": [{"name": m} for m in met_list],
        }

        if limit is not None:
            payload["limit"] = limit

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=self.headers, json=payload)

            if response.status_code in (401, 403):
                raise GoogleAuthError(
                    f"Permission denied fetching GA4 report: {response.text}"
                )
            elif response.status_code == 429:
                raise GoogleQuotaError("Google Analytics rate limit exceeded.")
            elif response.status_code >= 400:
                raise GoogleApiError(
                    f"Google Analytics API returned error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()

            dim_headers = [h.get("name", "") for h in data.get("dimensionHeaders", [])]
            met_headers = [
                {
                    "name": h.get("name", ""),
                    "type": h.get("type", "TYPE_UNSPECIFIED"),
                }
                for h in data.get("metricHeaders", [])
            ]

            parsed_rows = []
            for row in data.get("rows", []):
                d_vals = [v.get("value", "") for v in row.get("dimensionValues", [])]
                m_vals = [v.get("value", "") for v in row.get("metricValues", [])]
                parsed_rows.append(
                    {
                        "dimension_values": d_vals,
                        "metric_values": m_vals,
                    }
                )

            row_count = data.get("rowCount", len(parsed_rows))

            return {
                "property_id": property_id.split("/")[-1],
                "property_name": clean_prop,
                "dimension_headers": dim_headers,
                "metric_headers": met_headers,
                "rows": parsed_rows,
                "row_count": row_count,
            }
