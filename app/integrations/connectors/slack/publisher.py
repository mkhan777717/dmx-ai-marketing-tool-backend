from typing import Any, Dict, List, Optional

import httpx

from app.integrations.connectors.slack.exceptions import SlackPublishError
from app.integrations.connectors.slack.schemas import SlackPostMessageResponse


class SlackPublisher:
    API_BASE_URL = "https://slack.com/api"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def publish_message(
        self,
        channel_id: str,
        text: str,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publishes a message to a Slack channel using chat.postMessage."""

        url = f"{self.API_BASE_URL}/chat.postMessage"

        payload = {
            "channel": channel_id,
            "text": text,  # Fallback text if blocks are provided
        }

        if blocks:
            payload["blocks"] = blocks

        if thread_ts:
            payload["thread_ts"] = thread_ts

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)

            if response.status_code != 200:
                raise SlackPublishError(
                    f"HTTP error on chat.postMessage: {response.status_code}"
                )

            data = response.json()
            if not data.get("ok"):
                error_msg = data.get("error", "Unknown Slack API error")
                raise SlackPublishError(f"Slack API error: {error_msg}")

            validated = SlackPostMessageResponse(**data)
            return validated.model_dump()
