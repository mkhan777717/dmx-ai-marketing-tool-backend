import httpx
import asyncio
from typing import AsyncIterable, Union

from app.integrations.connectors.twitter.exceptions import (
    TwitterAuthError,
    TwitterPublishError,
)


class TwitterPublisher:
    def __init__(self, access_token: str):
        if not access_token:
            raise TwitterAuthError("Missing access token for Twitter publisher.")
        self.access_token = access_token

    async def upload_media(
        self,
        file_bytes: Union[bytes, AsyncIterable[bytes]],
        mime_type: str,
        total_bytes: int,
        media_category: str = "tweet_image",
    ) -> str:
        """
        Uploads a media file to X (Twitter) using the chunked media upload flow (API v2).
        Returns the media_id string.
        """
        base_url = "https://api.twitter.com/2/media/upload"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. INIT
            init_url = f"{base_url}/initialize"
            init_payload = {
                "command": "INIT",
                "total_bytes": str(total_bytes),
                "media_type": mime_type,
                "media_category": media_category,
            }
            init_response = await client.post(
                init_url, data=init_payload, headers=headers
            )
            if init_response.status_code == 401:
                raise TwitterAuthError(
                    "Twitter access token is missing or expired for media upload."
                )
            if init_response.status_code not in (200, 202):
                raise TwitterPublishError(
                    f"INIT media upload failed ({init_response.status_code}): {init_response.text}"
                )

            init_data = init_response.json()
            media_id = init_data.get("data", {}).get("id")
            if not media_id:
                raise TwitterPublishError(
                    f"Failed to parse media_id from INIT response: {init_data}"
                )

            # 2. APPEND
            append_url = f"{base_url}/{media_id}/append"
            if isinstance(file_bytes, bytes):
                files = {"media": ("media", file_bytes, mime_type)}
                append_response = await client.post(
                    append_url, files=files, headers=headers
                )
                if append_response.status_code not in (200, 204):
                    raise TwitterPublishError(
                        f"APPEND media upload failed ({append_response.status_code}): {append_response.text}"
                    )
            else:
                segment_index = 0
                async for chunk in file_bytes:
                    files = {"media": ("media", chunk, mime_type)}
                    data = {
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": str(segment_index),
                    }
                    append_response = await client.post(
                        append_url, data=data, files=files, headers=headers
                    )
                    if append_response.status_code not in (200, 204):
                        raise TwitterPublishError(
                            f"APPEND media upload failed ({append_response.status_code}): {append_response.text}"
                        )
                    segment_index += 1

            # 3. FINALIZE
            finalize_url = f"{base_url}/{media_id}/finalize"
            finalize_payload = {"command": "FINALIZE"}
            finalize_response = await client.post(
                finalize_url, data=finalize_payload, headers=headers
            )
            if finalize_response.status_code not in (200, 201):
                raise TwitterPublishError(
                    f"FINALIZE media upload failed ({finalize_response.status_code}): {finalize_response.text}"
                )

            finalize_data = finalize_response.json()

            # 4. STATUS POLLING
            processing_info = finalize_data.get("data", {}).get("processing_info")
            if processing_info:
                state = processing_info.get("state")
                while state in ("pending", "in_progress"):
                    check_after_secs = processing_info.get("check_after_secs", 5)
                    await asyncio.sleep(check_after_secs)

                    status_url = f"{base_url}/{media_id}/status"
                    status_response = await client.get(status_url, headers=headers)
                    if status_response.status_code != 200:
                        raise TwitterPublishError(
                            f"STATUS media upload failed ({status_response.status_code}): {status_response.text}"
                        )

                    status_data = status_response.json()
                    processing_info = status_data.get("data", {}).get(
                        "processing_info", {}
                    )
                    state = processing_info.get("state")

                    if state == "failed":
                        error_msg = processing_info.get("error", {}).get(
                            "message", "Unknown error"
                        )
                        raise TwitterPublishError(
                            f"Media processing failed: {error_msg}"
                        )
                    elif state == "succeeded":
                        break

            return str(media_id)

    async def publish_post(self, text: str, media_ids: list[str] | None = None) -> str:
        """
        Publishes a tweet to X (Twitter), optionally with media attached.
        Returns the created tweet ID.
        """
        if (not text or not text.strip()) and not media_ids:
            raise TwitterPublishError("Tweet must contain either text or media.")

        url = "https://api.twitter.com/2/tweets"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {}
        if text:
            payload["text"] = text
        if media_ids:
            payload["media"] = {"media_ids": media_ids}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 401:
                raise TwitterAuthError("Twitter access token is missing or expired.")

            if response.status_code not in (200, 201):
                raise TwitterPublishError(
                    f"Twitter API error ({response.status_code}): {response.text}"
                )

            try:
                data = response.json()
            except Exception:
                raise TwitterPublishError(
                    f"Malformed JSON response from Twitter API: {response.text}"
                )

            tweet_id = data.get("data", {}).get("id")
            if not tweet_id:
                raise TwitterPublishError(
                    f"Twitter API response missing tweet ID: {data}"
                )

            return str(tweet_id)
