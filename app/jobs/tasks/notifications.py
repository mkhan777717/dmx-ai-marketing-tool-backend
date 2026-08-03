import logging
from typing import Any

from app.jobs.base import JobPayload

logger = logging.getLogger(__name__)


class NotificationTaskPayload(JobPayload):
    notification_id: str
    user_id: str


async def send_in_app(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to dispatch an in-app notification.
    """
    payload = NotificationTaskPayload(**payload_dict)
    logger.info(f"Executing send_in_app for Notification {payload.notification_id}")
    return {"status": "success", "notification_id": payload.notification_id}


async def send_email(payload_dict: dict[str, Any]) -> dict:
    """
    Background job to dispatch an email notification.
    """
    payload = NotificationTaskPayload(**payload_dict)
    logger.info(f"Executing send_email for Notification {payload.notification_id}")
    return {"status": "success", "notification_id": payload.notification_id}
