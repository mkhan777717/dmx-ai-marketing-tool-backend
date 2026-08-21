import os

import httpx

from app.integrations.connectors.linkedin.exceptions import LinkedInPublishError


class LinkedInPublisher:
    # Use REST Posts API for general publishing
    POSTS_URL = "https://api.linkedin.com/rest/posts"

    def __init__(self, access_token: str):
        self.access_token = access_token

        # Load the API version from env, failing safely if missing
        api_version = os.getenv("LINKEDIN_API_VERSION")
        if not api_version:
            from app.integrations.exceptions import IntegrationError

            raise IntegrationError(
                "LINKEDIN_API_VERSION is not configured in the environment."
            )

        import re

        if not re.match(r"^\d{6}$", api_version):
            from app.integrations.exceptions import IntegrationError

            raise IntegrationError(
                f"LINKEDIN_API_VERSION '{api_version}' must be in YYYYMM format."
            )

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "LinkedIn-Version": api_version,
        }

    async def publish_text_post(self, author_urn: str, text: str) -> str:
        """Publishes a text-only post to LinkedIn."""

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "commentary": text,
            "visibility": "PUBLIC",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.POSTS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 201:
                raise LinkedInPublishError(
                    f"Failed to publish text post: {response.text}"
                )

            post_id = response.headers.get("x-restli-id")
            if not post_id:
                raise LinkedInPublishError(
                    "LinkedIn returned success but 'x-restli-id' was missing from headers."
                )

            return str(post_id)

    async def _initialize_upload(self, author_urn: str) -> tuple[str, str]:
        """Initializes image upload, returning (uploadUrl, image_urn)."""
        url = "https://api.linkedin.com/rest/images?action=initializeUpload"
        payload = {"initializeUploadRequest": {"owner": author_urn}}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers)

            if response.status_code != 200:
                raise LinkedInPublishError(
                    f"Failed to initialize image upload: {response.text}"
                )

            data = response.json()
            try:
                upload_url = data["value"]["uploadUrl"]
                image_urn = data["value"]["image"]
                return upload_url, image_urn
            except KeyError:
                raise LinkedInPublishError(
                    f"Invalid response from initializeUpload: {response.text}"
                )

    async def _upload_binary(
        self, upload_url: str, image_binary: bytes, mime_type: str
    ) -> None:
        """Uploads the raw binary image data to the provided uploadUrl."""
        # Use a fresh set of headers, the uploadUrl handles its own auth via query params/URL structure
        headers = {"Content-Type": mime_type}

        async with httpx.AsyncClient() as client:
            response = await client.put(
                upload_url, content=image_binary, headers=headers
            )

            if response.status_code not in (200, 201):
                raise LinkedInPublishError(
                    f"Failed to upload image binary: {response.text}"
                )

    async def publish_image_post(
        self, author_urn: str, text: str, image_binary: bytes, mime_type: str
    ) -> str:
        """
        Publishes an image post to LinkedIn.
        1. Register Upload
        2. Upload Image Binary
        3. Create Post
        """
        # Step 1
        upload_url, image_urn = await self._initialize_upload(author_urn)

        # Step 2
        await self._upload_binary(upload_url, image_binary, mime_type)

        # Step 3
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "commentary": text,
            "visibility": "PUBLIC",
            "content": {"media": {"id": image_urn}},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.POSTS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 201:
                raise LinkedInPublishError(
                    f"Failed to publish image post: {response.text}"
                )

            post_id = response.headers.get("x-restli-id")
            if not post_id:
                raise LinkedInPublishError(
                    "LinkedIn returned success for image post but 'x-restli-id' was missing from headers."
                )

            return str(post_id)
