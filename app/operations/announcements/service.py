from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operations.announcements.models import SystemAnnouncement


class AnnouncementService:
    @staticmethod
    async def get_active_announcements(
        db: AsyncSession,
    ) -> Sequence[SystemAnnouncement]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(SystemAnnouncement)
            .where(
                SystemAnnouncement.is_active,
                or_(
                    SystemAnnouncement.starts_at is None,
                    SystemAnnouncement.starts_at <= now,
                ),
                or_(
                    SystemAnnouncement.expires_at is None,
                    SystemAnnouncement.expires_at >= now,
                ),
            )
            .order_by(
                SystemAnnouncement.priority.desc(), SystemAnnouncement.created_at.desc()
            )
        )

        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_announcement(
        db: AsyncSession,
        title: str,
        message: str,
        type: str = "info",
        priority: int = 0,
    ) -> SystemAnnouncement:
        announcement = SystemAnnouncement(
            title=title, message=message, type=type, priority=priority
        )
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)
        return announcement
