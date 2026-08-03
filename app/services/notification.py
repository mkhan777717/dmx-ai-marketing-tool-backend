import uuid
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.enums import NotificationType
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.repositories.notification import (
    notification_preference_repo,
    notification_repo,
)
from app.schemas.notification import NotificationPreferenceUpdate


class NotificationService:
    @staticmethod
    async def get_unread(
        db: AsyncSession, user_id: uuid.UUID, limit: int = 50
    ) -> Sequence[Notification]:
        return await notification_repo.get_unread_for_user(db, user_id, limit)

    @staticmethod
    async def get_by_id(
        db: AsyncSession, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        return await notification_repo.get_by_id(db, id=notification_id)

    @staticmethod
    async def mark_as_read(
        db: AsyncSession, notification_id: uuid.UUID
    ) -> Optional[Notification]:
        return await notification_repo.mark_as_read(db, notification_id)

    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: uuid.UUID) -> int:
        return await notification_repo.mark_all_as_read(db, user_id)

    @staticmethod
    async def delete(db: AsyncSession, notification_id: uuid.UUID) -> bool:
        obj = await notification_repo.get_by_id(db, id=notification_id)
        if obj:
            await notification_repo.delete(db, id=notification_id)
            return True
        return False

    @staticmethod
    async def get_preferences(
        db: AsyncSession, user_id: uuid.UUID
    ) -> Sequence[NotificationPreference]:
        return await notification_preference_repo.get_all_for_user(db, user_id)

    @staticmethod
    async def update_preference(
        db: AsyncSession,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        notif_type: NotificationType,
        update_data: NotificationPreferenceUpdate,
    ) -> NotificationPreference:
        pref = await notification_preference_repo.get_by_user_and_type(
            db, user_id, notif_type
        )
        if not pref:
            # Create if it doesn't exist
            obj_in = {
                "workspace_id": workspace_id,
                "user_id": user_id,
                "notification_type": notif_type,
                "in_app_enabled": (
                    update_data.in_app_enabled
                    if update_data.in_app_enabled is not None
                    else True
                ),
                "email_enabled": (
                    update_data.email_enabled
                    if update_data.email_enabled is not None
                    else True
                ),
                "push_enabled": (
                    update_data.push_enabled
                    if update_data.push_enabled is not None
                    else False
                ),
            }
            return await notification_preference_repo.create(db, obj_in=obj_in)
        else:
            return await notification_preference_repo.update(
                db, db_obj=pref, obj_in=update_data.model_dump(exclude_unset=True)
            )
