import logging
import uuid
from typing import Any

from app.services.notifications.providers.base import BaseNotificationProvider

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):
    @property
    def provider_name(self) -> str:
        return "EMAIL"

    async def send(
        self, user_id: uuid.UUID, title: str, body: str, data: dict[str, Any] = None
    ) -> bool:
        """
        Simulates sending an email via SMTP or an external API like SendGrid/AWS SES.
        """
        logger.info(
            f"[EmailProvider] Sending email to User={user_id} | Subject={title}"
        )
        # Implementation for real email sending goes here.
        return True
