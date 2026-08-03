from typing import Any, Dict

import httpx

from app.integrations.connectors.facebook.exceptions import FacebookPublishError


class FacebookPublisher:
    GRAPH_API_VERSION = "v18.0"
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
        """
        Architecture stub for publishing an image post.
        Facebook requires POSTing to /{page_id}/photos with the image URL.
        """
        raise NotImplementedError("Image publishing is planned for a future iteration.")
