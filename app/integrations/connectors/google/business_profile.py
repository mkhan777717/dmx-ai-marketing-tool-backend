import httpx

from app.integrations.connectors.google.exceptions import (
    GoogleApiError,
    GoogleAuthError,
    GoogleQuotaError,
)


class GoogleBusinessProfilePublisher:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://mybusiness.googleapis.com/v4"

    async def publish_post(
        self, account_id: str, text: str, image_url: str | None = None
    ) -> str:
        """
        Publishes a LocalPost to the given account/location resource name.
        `account_id` is the full resource name, e.g., 'accounts/X/locations/Y'.
        """
        url = f"{self.base_url}/{account_id}/localPosts"

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "languageCode": "en-US",
            "summary": text,
            "topicType": "STANDARD",
        }

        if image_url:
            payload["media"] = [
                {
                    "mediaFormat": "PHOTO",
                    "sourceUrl": image_url,
                }
            ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 401:
                raise GoogleAuthError(
                    "Google Business Profile access token is invalid or expired."
                )
            elif response.status_code == 403:
                raise GoogleAuthError(
                    "Forbidden. Ensure the account has permission and 'business.manage' scope."
                )
            elif response.status_code == 429:
                raise GoogleQuotaError("Google Business Profile rate limit exceeded.")
            elif response.status_code >= 400:
                # 400 Bad Request or 5xx Server errors
                raise GoogleApiError(
                    f"Google API returned error {response.status_code}: {response.text}",
                    status_code=response.status_code,
                )

            data = response.json()
            post_name = data.get("name")
            if not post_name:
                raise GoogleApiError(
                    "Google Business Profile response missing 'name' identifier."
                )

            return str(post_name)
