import uuid
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    async def send_notification(self, user_id: uuid.UUID, message: str, context: Dict[str, Any] = None):
        """
        Stub for Notification Service.
        In the future, this will push messages to a queue (e.g. Redis, RabbitMQ) or directly to a provider.
        """
        logger.info(f"Notification sent to user {user_id}: {message}")
        if context:
            logger.debug(f"Notification context: {context}")
        
    async def notify_campaign_published(self, campaign_id: uuid.UUID, user_id: uuid.UUID, success: bool, error: str = None):
        if success:
            msg = f"Campaign {campaign_id} has been published successfully."
        else:
            msg = f"Failed to publish campaign {campaign_id}. Error: {error}"
            
        await self.send_notification(user_id, msg, {"campaign_id": str(campaign_id), "success": success})

notification_service = NotificationService()
