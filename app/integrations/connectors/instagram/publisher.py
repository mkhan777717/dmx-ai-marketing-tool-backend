from typing import Any, Dict

import httpx

from app.integrations.connectors.instagram.exceptions import InstagramPublishError


class InstagramPublisher:
    GRAPH_API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(self, page_access_token: str):
        # We need the page access token of the Facebook Page linked to the Instagram account
        self.page_access_token = page_access_token

    async def publish_image_post(
        self, ig_user_id: str, image_url: str, caption: str = ""
    ) -> Dict[str, Any]:
        """Publishes an image post to an Instagram Business Account via a two-step process."""

        # Step 1: Create Media Container
        container_url = f"{self.BASE_URL}/{ig_user_id}/media"
        container_payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.page_access_token,
        }

        async with httpx.AsyncClient() as client:
            container_response = await client.post(
                container_url, data=container_payload
            )

            if container_response.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to create media container: {container_response.text}"
                )

            container_data = container_response.json()
            creation_id = container_data.get("id")

            if not creation_id:
                raise InstagramPublishError(
                    "Media container creation did not return an ID."
                )

            # Step 2: Publish the Container
            publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.page_access_token,
            }

            publish_response = await client.post(publish_url, data=publish_payload)

            if publish_response.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to publish media container: {publish_response.text}"
                )

            return publish_response.json()

    async def publish_carousel_post(
        self, ig_user_id: str, image_urls: list, caption: str = ""
    ) -> Dict[str, Any]:
        """
        Architecture stub for publishing a carousel post.
        Requires creating multiple media containers and a carousel container.
        """
        raise NotImplementedError(
            "Carousel publishing is planned for a future iteration."
        )

    async def publish_reels_post(
        self, ig_user_id: str, video_url: str, caption: str = ""
    ) -> Dict[str, Any]:
        """
        Architecture stub for publishing a reels post.
        """
        raise NotImplementedError("Reels publishing is planned for a future iteration.")
