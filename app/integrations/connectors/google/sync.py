from typing import Any, Dict

import httpx

from app.integrations.connectors.google.exceptions import GoogleApiError
from app.integrations.connectors.google.schemas import GoogleProfileResponse


class GoogleSyncEngine:
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

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

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            profile = await self.fetch_profile()

            return {"profile": profile, "records_synced": 1}

        return {"status": "skipped", "reason": "unsupported sync type"}
