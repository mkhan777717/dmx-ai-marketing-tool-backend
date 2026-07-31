from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session as get_db
from app.operations.announcements.service import AnnouncementService

router = APIRouter(prefix="/announcements", tags=["Operations - System Announcements"])


@router.get("/active")
async def get_active_announcements(db: AsyncSession = Depends(get_db)):
    """Get all active announcements for users."""
    announcements = await AnnouncementService.get_active_announcements(db)
    return announcements
