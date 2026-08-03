import logging
import uuid
from typing import Any

from app.constants.enums import NotificationPriority, NotificationType
from app.db.session import AsyncSessionLocal
from app.repositories.notification import notification_repo
from app.services.notifications.providers.base import BaseNotificationProvider

logger = logging.getLogger(__name__)


class InAppProvider(BaseNotificationProvider):
    @property
    def provider_name(self) -> str:
        return "IN_APP"

    async def send(
        self, user_id: uuid.UUID, title: str, body: str, data: dict[str, Any] = None
    ) -> bool:
        """
        'Sending' an in-app notification simply means writing it to the `notifications` table.
        """
        try:
            # We use a fresh session to ensure the notification is saved even if
            # the surrounding transaction fails or hasn't committed.
            async with AsyncSessionLocal() as db:
                obj_in = {
                    "workspace_id": (
                        data.get("workspace_id") if data else None
                    ),  # Required, but might need to fetch user's default if not provided
                    "user_id": user_id,
                    "title": title,
                    "body": body,
                    "type": (
                        data.get("type", NotificationType.SYSTEM)
                        if data
                        else NotificationType.SYSTEM
                    ),
                    "priority": (
                        data.get("priority", NotificationPriority.NORMAL)
                        if data
                        else NotificationPriority.NORMAL
                    ),
                    "data": data,
                }
                # Handle cases where workspace_id is missing (system alerts) by fetching a workspace for the user
                if not obj_in["workspace_id"]:
                    from app.repositories.workspace_member import workspace_member_repo

                    memberships = await workspace_member_repo.get_by_user_id(
                        db, user_id
                    )
                    if memberships:
                        obj_in["workspace_id"] = memberships[0].workspace_id

                if obj_in["workspace_id"]:
                    await notification_repo.create(db, obj_in=obj_in)
                    return True
                else:
                    logger.warning(
                        f"Could not determine workspace_id for user {user_id}. Notification not saved."
                    )
                    return False
        except Exception as e:
            logger.error(f"Failed to save InApp notification: {str(e)}", exc_info=True)
            return False
