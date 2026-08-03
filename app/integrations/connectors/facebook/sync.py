from typing import Any, Dict

import httpx

from app.integrations.connectors.facebook.exceptions import FacebookApiError
from app.integrations.connectors.facebook.schemas import FacebookPagesResponse


class FacebookSyncEngine:
    GRAPH_API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.params = {"access_token": self.access_token}

    async def fetch_profile(self) -> Dict[str, Any]:
        """Fetches the authenticated user's profile."""
        url = f"{self.BASE_URL}/me"
        params = {**self.params, "fields": "id,name"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise FacebookApiError(
                    f"Failed to fetch profile: {response.text}",
                    status_code=response.status_code,
                )

            return response.json()

    async def fetch_pages(self) -> list:
        """Fetches the Facebook Pages the user administers, including Page Access Tokens."""
        url = f"{self.BASE_URL}/me/accounts"
        params = {**self.params, "fields": "id,name,access_token,category,tasks"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                raise FacebookApiError(
                    f"Failed to fetch pages: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            validated_response = FacebookPagesResponse(**data)
            return [page.model_dump() for page in validated_response.data]

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            profile = await self.fetch_profile()
            pages = await self.fetch_pages()
            return {
                "profile": profile,
                "pages": pages,
                "records_synced": 1 + len(pages),
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
