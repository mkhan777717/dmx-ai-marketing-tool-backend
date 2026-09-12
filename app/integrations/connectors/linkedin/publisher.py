import logging
import os
import re
from typing import Any, Dict, Tuple

import httpx

from app.integrations.connectors.linkedin.exceptions import (
    LinkedInAuthError,
    LinkedInPublishError,
)
from app.integrations.exceptions import IntegrationError

logger = logging.getLogger(__name__)


class LinkedInPublisher:
    POSTS_URL = "https://api.linkedin.com/rest/posts"
    IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
    VIDEOS_URL = "https://api.linkedin.com/rest/videos?action=initializeUpload"

    def __init__(self, access_token: str):
        if not access_token:
            raise LinkedInPublishError(
                "Access token is required for LinkedInPublisher."
            )

        self.access_token = access_token

        api_version = os.getenv("LINKEDIN_API_VERSION")
        if not api_version:
            raise IntegrationError(
                "LINKEDIN_API_VERSION is not configured in the environment."
            )

        if not re.match(r"^\d{6}$", api_version):
            raise IntegrationError(
                f"LINKEDIN_API_VERSION '{api_version}' must be in YYYYMM format."
            )

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
            "LinkedIn-Version": api_version,
        }

    def _validate_author_urn(self, author_urn: str) -> str:
        """Validates that author_urn is a valid LinkedIn person or organization URN."""
        if not author_urn or not isinstance(author_urn, str):
            raise LinkedInPublishError("Author URN is required.")

        author_urn = author_urn.strip()
        if not (
            author_urn.startswith("urn:li:person:")
            or author_urn.startswith("urn:li:organization:")
        ):
            raise LinkedInPublishError(f"Invalid LinkedIn author URN: {author_urn}")
        return author_urn

    def _handle_error_response(
        self, response: httpx.Response, action_name: str
    ) -> None:
        """Parses API error responses safely without exposing raw headers or tokens."""
        if response.status_code == 401:
            raise LinkedInAuthError(
                "LinkedIn access token is invalid, expired, or revoked."
            )

        if response.status_code == 403:
            raise LinkedInPublishError(
                f"Forbidden: Insufficient permissions to perform {action_name} for this LinkedIn account/organization."
            )

        if response.status_code == 429:
            raise LinkedInPublishError(
                f"LinkedIn rate limit exceeded during {action_name}.",
                status_code=429,
            )

        err_text = response.text
        if "Bearer" in err_text:
            err_text = "[REDACTED TOKEN ERROR]"

        raise LinkedInPublishError(
            f"Failed to {action_name}: {err_text}",
            status_code=response.status_code,
        )

    async def publish_text_post(self, author_urn: str, text: str) -> str:
        """Publishes a text post to a LinkedIn personal profile or Company Page."""
        author = self._validate_author_urn(author_urn)

        if not text or not text.strip():
            raise LinkedInPublishError("Post commentary text cannot be empty.")

        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "commentary": text.strip(),
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.POSTS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 201:
                self._handle_error_response(response, "publish text post")

            post_id = response.headers.get("x-restli-id")
            if not post_id:
                raise LinkedInPublishError(
                    "LinkedIn returned success but 'x-restli-id' was missing from headers."
                )

            return str(post_id)

    async def _initialize_image_upload(self, author_urn: str) -> Tuple[str, str]:
        """Initializes image upload, returning (uploadUrl, image_urn)."""
        author = self._validate_author_urn(author_urn)
        payload = {"initializeUploadRequest": {"owner": author}}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.IMAGES_URL, json=payload, headers=self.headers
            )

            if response.status_code != 200:
                self._handle_error_response(response, "initialize image upload")

            data = response.json()
            try:
                upload_url = data["value"]["uploadUrl"]
                image_urn = data["value"]["image"]
                return upload_url, image_urn
            except KeyError as exc:
                raise LinkedInPublishError(
                    f"Invalid response from initializeUpload: {response.text}"
                ) from exc

    async def _upload_binary(
        self, upload_url: str, binary_data: bytes, mime_type: str
    ) -> None:
        """Uploads raw binary data to the designated LinkedIn upload URL."""
        headers = {"Content-Type": mime_type}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    upload_url, content=binary_data, headers=headers
                )
            except Exception as exc:
                raise LinkedInPublishError(
                    f"Network failure uploading media binary: {exc}"
                ) from exc

            if response.status_code not in (200, 201):
                raise LinkedInPublishError(
                    f"Failed to upload image binary: {response.text}",
                    status_code=response.status_code,
                )

    async def publish_image_post(
        self, author_urn: str, text: str, image_binary: bytes, mime_type: str
    ) -> str:
        """Publishes an image post to a LinkedIn personal profile or Company Page."""
        author = self._validate_author_urn(author_urn)

        if not image_binary:
            raise LinkedInPublishError("Image binary data cannot be empty.")

        upload_url, image_urn = await self._initialize_image_upload(author)
        await self._upload_binary(upload_url, image_binary, mime_type)

        payload: Dict[str, Any] = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "commentary": text.strip() if text else "",
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "content": {"media": {"id": image_urn}},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.POSTS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 201:
                self._handle_error_response(response, "publish image post")

            post_id = response.headers.get("x-restli-id")
            if not post_id:
                raise LinkedInPublishError(
                    "LinkedIn returned success for image post but 'x-restli-id' was missing from headers."
                )

            return str(post_id)

    async def _initialize_video_upload(
        self, author_urn: str, file_size: int
    ) -> Tuple[str, str]:
        """Initializes video upload, returning (uploadUrl, video_urn)."""
        author = self._validate_author_urn(author_urn)
        payload = {
            "initializeUploadRequest": {
                "owner": author,
                "fileSizeBytes": file_size,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.VIDEOS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 200:
                self._handle_error_response(response, "initialize video upload")

            data = response.json()
            try:
                val = data["value"]
                video_urn = val["video"]
                upload_instructions = val.get("uploadInstructions", [])
                upload_url = (
                    upload_instructions[0]["uploadUrl"]
                    if upload_instructions
                    else val.get("uploadUrl")
                )
                if not upload_url:
                    raise KeyError("uploadUrl missing")
                return upload_url, video_urn
            except (KeyError, IndexError) as exc:
                raise LinkedInPublishError(
                    f"Invalid response from initializeUpload: {response.text}"
                ) from exc

    async def publish_video_post(
        self,
        author_urn: str,
        text: str,
        video_binary: bytes,
        mime_type: str,
        title: str = "",
    ) -> str:
        """Publishes a video post to a LinkedIn personal profile or Company Page."""
        author = self._validate_author_urn(author_urn)

        if not video_binary:
            raise LinkedInPublishError("Video binary data cannot be empty.")

        upload_url, video_urn = await self._initialize_video_upload(
            author, len(video_binary)
        )
        await self._upload_binary(upload_url, video_binary, mime_type)

        media_obj: Dict[str, Any] = {"id": video_urn}
        if title and title.strip():
            media_obj["title"] = title.strip()

        payload: Dict[str, Any] = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "commentary": text.strip() if text else "",
            "visibility": "PUBLIC",
            "distribution": {"feedDistribution": "MAIN_FEED"},
            "content": {"media": media_obj},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.POSTS_URL, json=payload, headers=self.headers
            )

            if response.status_code != 201:
                self._handle_error_response(response, "publish video post")

            post_id = response.headers.get("x-restli-id")
            if not post_id:
                raise LinkedInPublishError(
                    "LinkedIn returned success for video post but 'x-restli-id' was missing from headers."
                )

            return str(post_id)
