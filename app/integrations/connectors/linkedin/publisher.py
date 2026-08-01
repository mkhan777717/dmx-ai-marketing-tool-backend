from typing import Any, Dict

import httpx

from app.integrations.connectors.linkedin.exceptions import LinkedInPublishError


class LinkedInPublisher:
    # Use UGC post API for general publishing
    UGC_POST_URL = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

    async def publish_text_post(self, author_urn: str, text: str) -> Dict[str, Any]:
        """Publishes a text-only post to LinkedIn."""

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.UGC_POST_URL, json=payload, headers=self.headers
            )

            if response.status_code not in (201, 200):
                raise LinkedInPublishError(
                    f"Failed to publish text post: {response.text}"
                )

            return response.json()

    async def publish_image_post(
        self, author_urn: str, text: str, image_url: str
    ) -> Dict[str, Any]:
        """
        Architecture stub for publishing an image post.
        LinkedIn requires a 3-step process for images:
        1. Register Upload
        2. Upload Image
        3. Create UGC Post
        """
        raise NotImplementedError("Image publishing is planned for a future iteration.")
