from typing import Any, Dict

import httpx

from app.integrations.connectors.facebook.exceptions import FacebookPublishError
from app.integrations.constants import META_GRAPH_API_VERSION


class FacebookPublisher:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, access_token: str):
        # Note: To publish to a page, this MUST be the Page Access Token, not the user access token
        self.access_token = access_token

    async def publish_text_post(self, page_id: str, message: str) -> Dict[str, Any]:
        """Publishes a text-only post to a Facebook Page."""

        url = f"{self.BASE_URL}/{page_id}/feed"
        payload = {"message": message, "access_token": self.access_token}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)

            if response.status_code != 200:
                raise FacebookPublishError(
                    f"Failed to publish text post: {response.text}"
                )

            return response.json()

    async def publish_image_post(
        self, page_id: str, message: str, image_url: str
    ) -> Dict[str, Any]:
        """Publishes an image post to a Facebook Page."""
        url = f"{self.BASE_URL}/{page_id}/photos"
        payload = {
            "caption": message,
            "url": image_url,
            "access_token": self.access_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)

            if response.status_code != 200:
                raise FacebookPublishError(
                    f"Failed to publish image post: {response.text}"
                )

            return response.json()

    async def publish_video_post(
        self, page_id: str, title: str, description: str, file_url: str
    ) -> Dict[str, Any]:
        """Publishes a video post to a Facebook Page using a remote public URL."""
        url = f"{self.BASE_URL}/{page_id}/videos"
        payload = {
            "title": title,
            "description": description,
            "file_url": file_url,
            "access_token": self.access_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload)

            if response.status_code != 200:
                raise FacebookPublishError(
                    f"Failed to publish video post: {response.text}"
                )

            return response.json()
