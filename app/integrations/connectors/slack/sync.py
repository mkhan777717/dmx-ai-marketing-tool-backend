from typing import Any, Dict

import httpx

from app.integrations.connectors.slack.exceptions import SlackApiError
from app.integrations.connectors.slack.schemas import (
    SlackAuthTestResponse,
    SlackConversationsListResponse,
)


class SlackSyncEngine:
    API_BASE_URL = "https://slack.com/api"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def verify_auth(self) -> Dict[str, Any]:
        """Calls auth.test to verify the token and get identity."""
        url = f"{self.API_BASE_URL}/auth.test"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers)

            if response.status_code != 200:
                raise SlackApiError(f"HTTP error on auth.test: {response.status_code}")

            data = response.json()
            if not data.get("ok"):
                raise SlackApiError("Slack API error", error_code=data.get("error"))

            validated = SlackAuthTestResponse(**data)
            return validated.model_dump()

    async def list_channels(
        self, types: str = "public_channel,private_channel"
    ) -> list:
        """Calls conversations.list to get channels the bot can access."""
        url = f"{self.API_BASE_URL}/conversations.list"
        params = {"exclude_archived": "true", "types": types, "limit": 1000}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                raise SlackApiError(
                    f"HTTP error on conversations.list: {response.status_code}"
                )

            data = response.json()
            if not data.get("ok"):
                raise SlackApiError("Slack API error", error_code=data.get("error"))

            validated = SlackConversationsListResponse(**data)

            # Format nicely for internal syncing
            return [
                {
                    "id": channel.id,
                    "name": channel.name,
                    "is_private": channel.is_group or channel.is_im,
                }
                for channel in validated.channels
            ]

    async def perform_sync(self, sync_type: str = "full") -> dict:
        """Orchestrates the synchronization process."""
        if sync_type == "full":
            auth_info = await self.verify_auth()
            channels = await self.list_channels()

            return {
                "identity": auth_info,
                "channels": channels,
                "records_synced": len(channels) + 1,
            }

        return {"status": "skipped", "reason": "unsupported sync type"}
