from typing import Any, Dict

import httpx

from app.integrations.connectors.linkedin.exceptions import LinkedInApiError


class LinkedInSyncEngine:
    PROFILE_URL = "https://api.linkedin.com/v2/userinfo"
    # Organization endpoint requires v2 organizationalEntityAcls, but we'll mock basic structure for the architecture

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def fetch_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's profile."""
        async with httpx.AsyncClient() as client:
            response = await client.get(self.PROFILE_URL, headers=self.headers)

            if response.status_code != 200:
                raise LinkedInApiError(
                    f"Failed to fetch profile: {response.text}",
                    status_code=response.status_code,
                )

            return response.json()

    async def fetch_organizations(self) -> list:
        """Fetches organizations the user has access to."""
        # Using a stub URL for architecture purposes since it requires specific permissions
        orgs_url = "https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee"
        async with httpx.AsyncClient() as client:
            response = await client.get(orgs_url, headers=self.headers)

            if response.status_code != 200:
                # Often people don't have this permission, so we return empty instead of failing the whole sync
                return []

            data = response.json()
            return data.get("elements", [])

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            profile = await self.fetch_profile()
            orgs = await self.fetch_organizations()
            return {
                "profile": profile,
                "organizations": orgs,
                "records_synced": 1 + len(orgs),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
