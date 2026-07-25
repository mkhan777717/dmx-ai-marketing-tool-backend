import uuid
from typing import Sequence
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.repositories.base import BaseRepository
from app.models.notification import Notification
from app.constants.enums import NotificationType
from app.models.mixins import get_utc_now

class NotificationRepository(BaseRepository[Notification]):
    async def get_unread_for_user(self, db: AsyncSession, user_id: uuid.UUID, limit: int = 50) -> Sequence[Notification]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.read_at.is_(None)
        ).order_by(self.model.created_at.desc()).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()

    async def mark_as_read(self, db: AsyncSession, notification_id: uuid.UUID) -> Notification | None:
        notification = await self.get_by_id(db, notification_id)
        if notification and not notification.read_at:
            notification.read_at = get_utc_now()
            db.add(notification)
            await db.flush()
            await db.refresh(notification)
        return notification

    async def mark_all_as_read(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        stmt = update(self.model).where(
            self.model.user_id == user_id,
            self.model.read_at.is_(None)
        ).values(read_at=get_utc_now())
        
        result = await db.execute(stmt)
        await db.flush()
        return result.rowcount

notification_repo = NotificationRepository(Notification)
