import logging

import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)

logger = logging.getLogger(__name__)


class YouTubePublisher:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    async def upload_video(
        self,
        asset_url: str,
        title: str,
        description: str,
        file_size: int,
        mime_type: str,
    ) -> str:
        """
        Uploads a video to YouTube using the Resumable Upload protocol.
        Does not load the entire video into memory.
        """
        init_url = f"{self.base_url}?uploadType=resumable&part=snippet,status"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Length": str(file_size),
            "X-Upload-Content-Type": mime_type,
        }

        payload = {
            "snippet": {
                "title": title[:100] if title else "Untitled Video",
                "description": description[:5000] if description else "",
            },
            "status": {"privacyStatus": "private"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Initialize upload session
            response = await client.post(init_url, headers=headers, json=payload)
            self._handle_errors(response)

            location_url = response.headers.get("Location")
            if not location_url:
                raise GoogleApiError(
                    "YouTube upload initialization failed: missing Location header."
                )

            # 2. Upload binary data
            uploaded_bytes = 0
            retries = 3

            while uploaded_bytes < file_size and retries > 0:
                try:
                    # Stream from asset_url, offset by uploaded_bytes
                    req_headers = {}
                    if uploaded_bytes > 0:
                        req_headers["Range"] = f"bytes={uploaded_bytes}-"

                    async with client.stream(
                        "GET", asset_url, headers=req_headers
                    ) as stream_resp:
                        if stream_resp.status_code not in (200, 206):
                            raise GoogleApiError(
                                f"Failed to fetch asset from URL: {stream_resp.status_code}"
                            )

                        async def chunk_generator():
                            async for chunk in stream_resp.aiter_bytes(
                                chunk_size=1024 * 1024 * 4
                            ):
                                yield chunk

                        put_headers = {
                            "Content-Length": str(file_size - uploaded_bytes),
                            "Content-Range": f"bytes {uploaded_bytes}-{file_size - 1}/{file_size}",
                        }

                        upload_resp = await client.put(
                            location_url,
                            content=chunk_generator(),
                            headers=put_headers,
                            timeout=300.0,
                        )

                        if upload_resp.status_code in (200, 201):
                            data = upload_resp.json()
                            video_id = data.get("id")
                            if not video_id:
                                raise GoogleApiError(
                                    "YouTube response missing video 'id'."
                                )
                            return video_id

                        if upload_resp.status_code == 308:
                            # 308 Resume Incomplete
                            range_header = upload_resp.headers.get("Range")
                            if range_header:
                                # Example: Range: bytes=0-999999
                                last_byte = int(range_header.split("-")[1])
                                uploaded_bytes = last_byte + 1
                                continue
                            else:
                                raise GoogleApiError(
                                    "308 response missing Range header."
                                )

                        self._handle_errors(upload_resp)

                except (httpx.RequestError, GoogleApiError) as e:
                    retries -= 1
                    if retries == 0:
                        raise GoogleApiError(
                            f"YouTube video upload failed after retries: {str(e)}"
                        )

                    # Recover state from YouTube
                    status_resp = await client.put(
                        location_url, headers={"Content-Range": f"bytes */{file_size}"}
                    )

                    if status_resp.status_code == 308:
                        range_header = status_resp.headers.get("Range")
                        if range_header:
                            last_byte = int(range_header.split("-")[1])
                            uploaded_bytes = last_byte + 1
                        else:
                            uploaded_bytes = 0
                    elif status_resp.status_code in (200, 201):
                        return status_resp.json().get("id")
                    else:
                        self._handle_errors(status_resp)

        raise GoogleApiError("YouTube upload did not complete.")

    def _handle_errors(self, response: httpx.Response):
        if response.status_code == 401:
            raise GoogleAuthError("Google access token is invalid or expired.")
        elif response.status_code == 403:
            raise GoogleAuthError(
                "Forbidden. Ensure the account has permission and 'youtube.upload' scope."
            )
        elif response.status_code == 429:
            raise GoogleQuotaError("YouTube rate limit exceeded.")
        elif response.status_code >= 400:
            raise GoogleApiError(
                f"YouTube API returned error {response.status_code}: {response.text}",
                status_code=response.status_code,
            )
