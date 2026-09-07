from typing import Any

from app.constants.enums import ApiProvider
from app.integrations.connectors.slack.exceptions import SlackPublishError
from app.integrations.connectors.slack.publisher import SlackPublisher
from app.integrations.exceptions import IntegrationError
from app.integrations.secrets.service import secret_service
from app.models.campaign_content import CampaignContent
from app.models.social_account import SocialAccount
from app.services.social.base import BaseSocialProvider


class SlackProvider(BaseSocialProvider):
    @property
    def provider_name(self) -> str:
        return ApiProvider.SLACK.value

    async def publish_content(
        self, account: SocialAccount, content: CampaignContent
    ) -> str:
        if not account or not account.access_token:
            raise IntegrationError(
                f"No access token available for social account {getattr(account, 'id', 'unknown')}"
            )

        if not account.account_id:
            raise IntegrationError("Slack SocialAccount missing channel account_id.")

        decrypted_token = secret_service.decrypt_token(account.access_token)
        publisher = SlackPublisher(access_token=decrypted_token)

        channel_id = account.account_id
        text_body = content.body or ""
        assets = content.assets if content.assets else []

        if assets:
            asset_urls = [
                a.public_url for a in assets if getattr(a, "public_url", None)
            ]
            if asset_urls:
                joined_urls = "\n".join(asset_urls)
                message_text = (
                    f"{text_body}\n{joined_urls}".strip() if text_body else joined_urls
                )
            else:
                message_text = text_body
        else:
            message_text = text_body

        if not message_text.strip():
            raise IntegrationError(
                f"Campaign content {content.id} body is empty and no valid asset URLs provided."
            )

        try:
            response = await publisher.publish_message(
                channel_id=channel_id,
                text=message_text,
            )
        except SlackPublishError as e:
            raise IntegrationError(f"Slack publishing failed: {str(e)}") from e

        ts = response.get("ts")
        if not ts:
            raise SlackPublishError("Slack API did not return a valid timestamp (ts).")

        return str(ts)

    async def get_account_info(self, account: SocialAccount | str) -> dict[str, Any]:
        """Returns account channel information."""
        if isinstance(account, str):
            return {
                "account_id": "slack_channel",
                "name": "Slack Channel",
                "provider": ApiProvider.SLACK.value,
            }

        return {
            "account_id": account.account_id,
            "name": account.name or "Slack Channel",
            "provider": ApiProvider.SLACK.value,
        }
