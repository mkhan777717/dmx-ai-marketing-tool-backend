from typing import Any, Dict

import httpx

from app.integrations.connectors.instagram.exceptions import InstagramPublishError
from app.integrations.constants import META_GRAPH_API_VERSION


class InstagramPublisher:
    GRAPH_API_VERSION = META_GRAPH_API_VERSION
    BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

    def __init__(
        self,
        page_access_token: str,
        max_attempts: int = 10,
        poll_interval: float = 1.0,
    ):
        # We need the page access token of the Facebook Page linked to the Instagram account
        self.page_access_token = page_access_token
        self.max_attempts = max_attempts
        self.poll_interval = poll_interval

    async def wait_for_container_ready(
        self,
        creation_id: str,
        client: httpx.AsyncClient | None = None,
        max_attempts: int | None = None,
        poll_interval: float | None = None,
    ) -> bool:
        """
        Polls GET /{creation_id}?fields=status_code until status_code reaches FINISHED.
        Raises InstagramPublishError on ERROR, EXPIRED, timeout, or HTTP failures.
        """
        if not creation_id:
            raise InstagramPublishError(
                "Media container creation ID is required for status polling."
            )

        if not self.page_access_token:
            raise InstagramPublishError(
                "Page access token is required for container status polling."
            )

        attempts_limit = max_attempts if max_attempts is not None else self.max_attempts
        interval = poll_interval if poll_interval is not None else self.poll_interval

        status_url = f"{self.BASE_URL}/{creation_id}"
        params = {
            "fields": "status_code",
            "access_token": self.page_access_token,
        }

        should_close_client = False
        if client is None:
            client = httpx.AsyncClient()
            should_close_client = True

        try:
            for attempt in range(1, attempts_limit + 1):
                try:
                    response = await client.get(status_url, params=params)
                except httpx.RequestError as e:
                    raise InstagramPublishError(
                        f"Failed to check container status (Network error): {str(e)}"
                    )

                if response.status_code != 200:
                    raise InstagramPublishError(
                        f"Failed to check container status (Status Code {response.status_code}): {response.text}"
                    )

                try:
                    data = response.json()
                except Exception:
                    raise InstagramPublishError(
                        "Container status response returned invalid JSON."
                    )

                status_code = data.get("status_code")

                if not status_code:
                    raise InstagramPublishError(
                        "Container status response missing 'status_code' field."
                    )

                if status_code == "FINISHED":
                    return True
                elif status_code in ("ERROR", "EXPIRED"):
                    err_msg = (
                        data.get("status")
                        or f"Container status code returned {status_code}."
                    )
                    raise InstagramPublishError(
                        f"Media container processing failed with status '{status_code}': {err_msg}"
                    )
                elif status_code == "IN_PROGRESS":
                    if attempt < attempts_limit:
                        import asyncio

                        await asyncio.sleep(interval)
                else:
                    raise InstagramPublishError(
                        f"Media container returned unexpected status_code '{status_code}'."
                    )

            raise InstagramPublishError(
                f"Media container {creation_id} processing timed out after {attempts_limit} attempts."
            )
        finally:
            if should_close_client:
                await client.aclose()

    async def publish_image_post(
        self,
        ig_user_id: str,
        image_url: str,
        caption: str = "",
        max_attempts: int | None = None,
        poll_interval: float | None = None,
    ) -> Dict[str, Any]:
        """Publishes an image post to an Instagram Business Account via a two-step process."""
        if not self.page_access_token:
            raise InstagramPublishError(
                "Page access token is required to publish image post."
            )

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

            # Step 1.5: Poll status until FINISHED
            await self.wait_for_container_ready(
                creation_id=creation_id,
                client=client,
                max_attempts=max_attempts,
                poll_interval=poll_interval,
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

    async def publish_video_post(
        self,
        ig_user_id: str,
        video_url: str,
        caption: str = "",
        max_attempts: int | None = None,
        poll_interval: float | None = None,
    ) -> Dict[str, Any]:
        """Publishes a video post to an Instagram Business Account via a two-step process."""
        if not self.page_access_token:
            raise InstagramPublishError(
                "Page access token is required to publish video post."
            )

        # Step 1: Create Video Media Container
        container_url = f"{self.BASE_URL}/{ig_user_id}/media"
        container_payload = {
            "media_type": "VIDEO",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.page_access_token,
        }

        async with httpx.AsyncClient() as client:
            container_response = await client.post(
                container_url, data=container_payload
            )

            if container_response.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to create video media container: {container_response.text}"
                )

            container_data = container_response.json()
            creation_id = container_data.get("id")

            if not creation_id:
                raise InstagramPublishError(
                    "Video media container creation did not return an ID."
                )

            # Step 1.5: Poll status until FINISHED
            await self.wait_for_container_ready(
                creation_id=creation_id,
                client=client,
                max_attempts=max_attempts,
                poll_interval=poll_interval,
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
                    f"Failed to publish video media container: {publish_response.text}"
                )

            return publish_response.json()

    async def publish_carousel_post(
        self,
        ig_user_id: str,
        items: list[Any],
        caption: str = "",
        max_attempts: int | None = None,
        poll_interval: float | None = None,
    ) -> Dict[str, Any]:
        """
        Publishes a Carousel post (containing 2 to 10 image or video items) to an Instagram Business Account.
        Follows the Meta Graph API multi-step container creation process:
        1. Create child media container for each item (with is_carousel_item=true).
        2. Wait for each child container to reach FINISHED state.
        3. Create parent carousel container (media_type=CAROUSEL, children=[child_ids]).
        4. Wait for parent carousel container to reach FINISHED state.
        5. Publish parent carousel container via media_publish.
        """
        if not self.page_access_token:
            raise InstagramPublishError(
                "Page access token is required to publish Carousel post."
            )

        if not ig_user_id:
            raise InstagramPublishError(
                "Instagram user ID is required to publish Carousel post."
            )

        if not items or not isinstance(items, list):
            raise InstagramPublishError(
                "Carousel items list is required and cannot be empty."
            )

        if len(items) < 2 or len(items) > 10:
            raise InstagramPublishError(
                f"Instagram Carousel requires between 2 and 10 items, but received {len(items)}."
            )

        # Parse and validate items
        parsed_items: list[dict[str, str]] = []
        for idx, item in enumerate(items, start=1):
            if isinstance(item, str):
                url = item.strip()
                if not url:
                    raise InstagramPublishError(
                        f"Carousel item {idx} has an empty image URL."
                    )
                parsed_items.append({"media_type": "IMAGE", "url": url})
            elif isinstance(item, dict):
                media_type = (
                    item.get("media_type")
                    or item.get("type")
                    or item.get("asset_type")
                    or "IMAGE"
                )
                media_type_str = str(media_type).upper()
                if media_type_str not in ("IMAGE", "VIDEO"):
                    raise InstagramPublishError(
                        f"Carousel item {idx} has unsupported media_type '{media_type}'."
                    )
                url = (
                    item.get("url")
                    or item.get("public_url")
                    or item.get("image_url")
                    or item.get("video_url")
                    or ""
                )
                url = str(url).strip()
                if not url:
                    raise InstagramPublishError(
                        f"Carousel item {idx} is missing a media URL."
                    )
                parsed_items.append({"media_type": media_type_str, "url": url})
            else:
                raise InstagramPublishError(
                    f"Carousel item {idx} must be a URL string or item dictionary."
                )

        child_container_ids: list[str] = []

        async with httpx.AsyncClient() as client:
            # Step 1: Create child media containers
            for idx, item in enumerate(parsed_items, start=1):
                container_url = f"{self.BASE_URL}/{ig_user_id}/media"
                payload = {
                    "is_carousel_item": "true",
                    "access_token": self.page_access_token,
                }
                if item["media_type"] == "IMAGE":
                    payload["image_url"] = item["url"]
                else:
                    payload["media_type"] = "VIDEO"
                    payload["video_url"] = item["url"]

                container_resp = await client.post(container_url, data=payload)
                if container_resp.status_code != 200:
                    raise InstagramPublishError(
                        f"Failed to create child media container for item {idx}: {container_resp.text}"
                    )

                try:
                    data = container_resp.json()
                except Exception:
                    raise InstagramPublishError(
                        f"Child media container creation for item {idx} returned invalid JSON."
                    )

                child_id = data.get("id")
                if not child_id:
                    raise InstagramPublishError(
                        f"Child media container creation for item {idx} did not return an ID."
                    )

                # Wait for child container status to reach FINISHED
                await self.wait_for_container_ready(
                    creation_id=child_id,
                    client=client,
                    max_attempts=max_attempts,
                    poll_interval=poll_interval,
                )

                child_container_ids.append(child_id)

            # Step 2: Create parent CAROUSEL container
            parent_container_url = f"{self.BASE_URL}/{ig_user_id}/media"
            children_str = ",".join(child_container_ids)
            parent_payload = {
                "media_type": "CAROUSEL",
                "children": children_str,
                "caption": caption,
                "access_token": self.page_access_token,
            }

            parent_resp = await client.post(parent_container_url, data=parent_payload)
            if parent_resp.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to create parent Carousel media container: {parent_resp.text}"
                )

            try:
                parent_data = parent_resp.json()
            except Exception:
                raise InstagramPublishError(
                    "Parent Carousel media container creation returned invalid JSON."
                )

            parent_id = parent_data.get("id")
            if not parent_id:
                raise InstagramPublishError(
                    "Parent Carousel media container creation did not return an ID."
                )

            # Wait for parent container status to reach FINISHED
            await self.wait_for_container_ready(
                creation_id=parent_id,
                client=client,
                max_attempts=max_attempts,
                poll_interval=poll_interval,
            )

            # Step 3: Publish parent Carousel container
            publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
            publish_payload = {
                "creation_id": parent_id,
                "access_token": self.page_access_token,
            }

            publish_resp = await client.post(publish_url, data=publish_payload)
            if publish_resp.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to publish Carousel media container: {publish_resp.text}"
                )

            try:
                return publish_resp.json()
            except Exception:
                raise InstagramPublishError(
                    "Carousel media publish response returned invalid JSON."
                )

    async def publish_reels_post(
        self,
        ig_user_id: str,
        video_url: str,
        caption: str = "",
        max_attempts: int | None = None,
        poll_interval: float | None = None,
    ) -> Dict[str, Any]:
        """Publishes a Reels post to an Instagram Business Account via a two-step process."""
        if not self.page_access_token:
            raise InstagramPublishError(
                "Page access token is required to publish Reels post."
            )

        if not ig_user_id:
            raise InstagramPublishError(
                "Instagram user ID is required to publish Reels post."
            )

        if not video_url:
            raise InstagramPublishError("Video URL is required to publish Reels post.")

        # Step 1: Create REELS Media Container
        container_url = f"{self.BASE_URL}/{ig_user_id}/media"
        container_payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.page_access_token,
        }

        async with httpx.AsyncClient() as client:
            container_response = await client.post(
                container_url, data=container_payload
            )

            if container_response.status_code != 200:
                raise InstagramPublishError(
                    f"Failed to create Reels media container: {container_response.text}"
                )

            try:
                container_data = container_response.json()
            except Exception:
                raise InstagramPublishError(
                    "Reels media container creation response returned invalid JSON."
                )

            creation_id = container_data.get("id")

            if not creation_id:
                raise InstagramPublishError(
                    "Reels media container creation did not return an ID."
                )

            # Step 1.5: Poll status until FINISHED
            await self.wait_for_container_ready(
                creation_id=creation_id,
                client=client,
                max_attempts=max_attempts,
                poll_interval=poll_interval,
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
                    f"Failed to publish Reels media container: {publish_response.text}"
                )

            try:
                return publish_response.json()
            except Exception:
                raise InstagramPublishError(
                    "Reels media publish response returned invalid JSON."
                )
