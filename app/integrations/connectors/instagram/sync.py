from typing import Any, Dict

import httpx

from app.integrations.connectors.instagram.exceptions import InstagramApiError
from app.integrations.connectors.instagram.schemas import FacebookPagesResponse
from app.integrations.constants import META_GRAPH_API_VERSION
from app.integrations.exceptions import OAuthTokenError


class InstagramSyncEngine:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.params = {"access_token": self.access_token}

    async def fetch_pages_with_instagram(self) -> list:
        """Fetches Facebook Pages that have an Instagram Business Account linked."""
        url = f"{self.BASE_URL}/me/accounts"
        params = {
            **self.params,
            "fields": "id,name,access_token,instagram_business_account",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                try:
                    err_data = response.json()
                    err_type = err_data.get("error", {}).get("type")
                    if (
                        response.status_code in (400, 401)
                        and err_type == "OAuthException"
                    ):
                        raise OAuthTokenError(
                            "Instagram/Facebook access token is invalid or expired."
                        )
                except ValueError:
                    pass

                raise InstagramApiError(
                    f"Failed to fetch pages (Status: {response.status_code})",
                    status_code=response.status_code,
                )

            data = response.json()
            validated_response = FacebookPagesResponse(**data)

            # Filter only pages that have a linked instagram_business_account
            return [
                page.model_dump()
                for page in validated_response.data
                if page.instagram_business_account is not None
            ]

    async def fetch_profile(self, ig_account_id: str) -> Dict[str, Any]:
        """Fetches the Instagram Business Account profile."""
        url = f"{self.BASE_URL}/{ig_account_id}"
        params = {**self.params, "fields": "id,username,name,profile_picture_url"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            if response.status_code != 200:
                try:
                    err_data = response.json()
                    err_type = err_data.get("error", {}).get("type")
                    if (
                        response.status_code in (400, 401)
                        and err_type == "OAuthException"
                    ):
                        raise OAuthTokenError(
                            "Instagram/Facebook access token is invalid or expired."
                        )
                except ValueError:
                    pass

                raise InstagramApiError(
                    f"Failed to fetch IG profile (Status: {response.status_code})",
                    status_code=response.status_code,
                )

            return response.json()

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            linked_pages = await self.fetch_pages_with_instagram()

            profiles = []
            for page in linked_pages:
                ig_id = page["instagram_business_account"]["id"]
                profile = await self.fetch_profile(ig_id)
                # Attach the page access token so we can use it to publish later
                profile["linked_page_id"] = page["id"]
                profile["page_access_token"] = page["access_token"]
                profiles.append(profile)

            return {"instagram_accounts": profiles, "records_synced": len(profiles)}

        return {"status": "skipped", "reason": "unsupported sync type"}
